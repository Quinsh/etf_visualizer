from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ETF Visualizer API",
    description="API for creating and visualizing equal-weighted stock portfolios",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class PortfolioRequest(BaseModel):
    tickers: List[str]
    period: str = "1y"  # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

class StockData(BaseModel):
    ticker: str
    data: Dict[str, Any]
    error: str = None

class PortfolioResponse(BaseModel):
    tickers: List[str]
    portfolio_data: Dict[str, Any]
    individual_stocks: List[StockData]
    period: str
    created_at: str

# Thread pool for concurrent API calls
executor = ThreadPoolExecutor(max_workers=10)

def fetch_stock_data(ticker: str, period: str) -> Dict[str, Any]:
    """Fetch data for a single stock ticker"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if hist.empty:
            return {"ticker": ticker, "error": f"No data found for {ticker}"}
        
        # Convert to dictionary for JSON serialization
        data = {
            "dates": hist.index.strftime('%Y-%m-%d').tolist(),
            "prices": hist['Close'].tolist(),
            "volumes": hist['Volume'].tolist(),
            "highs": hist['High'].tolist(),
            "lows": hist['Low'].tolist(),
            "opens": hist['Open'].tolist()
        }
        
        return {"ticker": ticker, "data": data, "error": None}
    
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {str(e)}")
        return {"ticker": ticker, "error": str(e)}

async def fetch_multiple_stocks(tickers: List[str], period: str) -> List[Dict[str, Any]]:
    """Fetch data for multiple stocks concurrently"""
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(executor, fetch_stock_data, ticker, period)
        for ticker in tickers
    ]
    return await asyncio.gather(*tasks)

def calculate_equal_weighted_portfolio(stocks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate equal-weighted portfolio performance"""
    valid_stocks = [stock for stock in stocks_data if stock.get("error") is None]
    
    if not valid_stocks:
        raise HTTPException(status_code=400, detail="No valid stock data found")
    
    # Get the common date range
    all_dates = []
    for stock in valid_stocks:
        all_dates.extend(stock["data"]["dates"])
    
    unique_dates = sorted(list(set(all_dates)))
    
    # Create portfolio dataframe
    portfolio_data = {}
    
    for date in unique_dates:
        daily_prices = []
        for stock in valid_stocks:
            stock_dates = stock["data"]["dates"]
            if date in stock_dates:
                date_index = stock_dates.index(date)
                daily_prices.append(stock["data"]["prices"][date_index])
        
        # Only include dates where we have data for all stocks
        if len(daily_prices) == len(valid_stocks):
            # Equal weighted average
            portfolio_data[date] = sum(daily_prices) / len(daily_prices)
    
    if not portfolio_data:
        raise HTTPException(status_code=400, detail="No common dates found across all stocks")
    
    # Calculate portfolio statistics
    dates = list(portfolio_data.keys())
    prices = list(portfolio_data.values())
    
    # Calculate daily returns
    returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
    
    # Calculate statistics
    total_return = (prices[-1] - prices[0]) / prices[0] * 100 if len(prices) > 1 else 0
    volatility = np.std(returns) * np.sqrt(252) * 100 if len(returns) > 1 else 0  # Annualized
    
    return {
        "dates": dates,
        "prices": prices,
        "returns": returns,
        "total_return_percent": round(total_return, 2),
        "annualized_volatility_percent": round(volatility, 2),
        "num_data_points": len(prices)
    }

@app.get("/")
async def root():
    return {"message": "ETF Visualizer API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/portfolio", response_model=PortfolioResponse)
async def create_portfolio(request: PortfolioRequest):
    """Create equal-weighted portfolio from list of tickers"""
    
    if not request.tickers:
        raise HTTPException(status_code=400, detail="At least one ticker is required")
    
    if len(request.tickers) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 tickers allowed")
    
    # Validate period
    valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
    if request.period not in valid_periods:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
        )
    
    try:
        logger.info(f"Fetching data for tickers: {request.tickers}")
        
        # Fetch stock data concurrently
        stocks_data = await fetch_multiple_stocks(request.tickers, request.period)
        
        # Calculate portfolio performance
        portfolio_data = calculate_equal_weighted_portfolio(stocks_data)
        
        # Format response
        individual_stocks = [
            StockData(
                ticker=stock["ticker"],
                data=stock.get("data", {}),
                error=stock.get("error")
            )
            for stock in stocks_data
        ]
        
        return PortfolioResponse(
            tickers=request.tickers,
            portfolio_data=portfolio_data,
            individual_stocks=individual_stocks,
            period=request.period,
            created_at=datetime.now().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/ticker/{ticker}")
async def get_ticker_info(ticker: str):
    """Get basic information about a ticker"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            "ticker": ticker,
            "name": info.get("longName", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", "N/A"),
            "currency": info.get("currency", "USD")
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found: {str(e)}")

@app.get("/portfolio/example")
async def get_example_portfolio():
    """Get an example portfolio for testing"""
    example_request = PortfolioRequest(
        tickers=["AAPL", "GOOGL", "MSFT", "TSLA"],
        period="6mo"
    )
    return await create_portfolio(example_request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)