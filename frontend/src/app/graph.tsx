import React, { useEffect } from "react";
import { init, dispose } from "klinecharts";

// Define the data structure for KLineChart bars
interface BarData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// Define the callback function type for getBars
type GetBarsCallback = (data: BarData[]) => void;

// Define the getBars function parameters
interface GetBarsParams {
  callback: GetBarsCallback;
}

// Define the data loader interface
interface DataLoader {
  getBars: (params: GetBarsParams) => void;
}

const GraphComponent = (): React.JSX.Element => {
  useEffect(() => {
    // Initialize the chart with proper null checking
    const chart = init("chart");

    // Check if chart initialization was successful
    if (!chart) {
      console.error("Failed to initialize KLineChart");
      return;
    }

    // Set the symbol for the chart
    // Use type assertion to access chart methods since TypeScript definitions might be incomplete
    try {
      // Sample OHLCV data for the chart
      const sampleData: BarData[] = [
        {
          timestamp: 1517846400000,
          open: 7424.6,
          high: 7511.3,
          low: 6032.3,
          close: 7310.1,
          volume: 224461,
        },
        {
          timestamp: 1517932800000,
          open: 7310.1,
          high: 8499.9,
          low: 6810,
          close: 8165.4,
          volume: 148807,
        },
        {
          timestamp: 1518019200000,
          open: 8166.7,
          high: 8700.8,
          low: 7400,
          close: 8245.1,
          volume: 24467,
        },
        {
          timestamp: 1518105600000,
          open: 8244,
          high: 8494,
          low: 7760,
          close: 8364,
          volume: 29834,
        },
        {
          timestamp: 1518192000000,
          open: 8363.6,
          high: 9036.7,
          low: 8269.8,
          close: 8311.9,
          volume: 28203,
        },
        {
          timestamp: 1518278400000,
          open: 8301,
          high: 8569.4,
          low: 7820.2,
          close: 8426,
          volume: 59854,
        },
        {
          timestamp: 1518364800000,
          open: 8426,
          high: 8838,
          low: 8024,
          close: 8640,
          volume: 54457,
        },
        {
          timestamp: 1518451200000,
          open: 8640,
          high: 8976.8,
          low: 8360,
          close: 8500,
          volume: 51156,
        },
        {
          timestamp: 1518537600000,
          open: 8504.9,
          high: 9307.3,
          low: 8474.3,
          close: 9307.3,
          volume: 49118,
        },
        {
          timestamp: 1518624000000,
          open: 9307.3,
          high: 9897,
          low: 9182.2,
          close: 9774,
          volume: 48092,
        },
      ];

      console.log("Chart initialized:", chart);
      console.log("Sample data:", sampleData);

      // Try different approaches to load data in KLineChart v10
      // Method 1: Try setDataLoader (original approach)
      try {
        const dataLoader: DataLoader = {
          getBars: ({ callback }: GetBarsParams) => {
            console.log("getBars called, providing data...");
            callback(sampleData);
          },
        };
        (chart as any).setDataLoader(dataLoader);
        console.log("setDataLoader called successfully");
      } catch (loaderError) {
        console.log(
          "setDataLoader failed, trying alternative methods:",
          loaderError
        );

        // Method 2: Try applyNewData (v9 method that might still work)
        try {
          (chart as any).applyNewData(sampleData);
          console.log("applyNewData called successfully");
        } catch (applyError) {
          console.log("applyNewData failed:", applyError);

          // Method 3: Try setData (direct data setting)
          try {
            (chart as any).setData(sampleData);
            console.log("setData called successfully");
          } catch (setDataError) {
            console.log("setData failed:", setDataError);

            // Method 4: Try loadData
            try {
              (chart as any).loadData(sampleData);
              console.log("loadData called successfully");
            } catch (loadError) {
              console.log("loadData failed:", loadError);
              console.error("All data loading methods failed");
            }
          }
        }
      }

      // Set symbol and period after data loading
      (chart as any).setSymbol({ ticker: "TestSymbol" });
      (chart as any).setPeriod({ span: 1, type: "day" });
    } catch (error) {
      console.error("Error setting up chart:", error);
    }

    // Cleanup function to dispose of the chart when component unmounts
    return () => {
      dispose("chart");
    };
  }, []);

  // Return the chart container div with proper styling
  return (
    <div
      id="chart"
      style={{
        width: "600px",
        height: "600px",
        border: "1px solid #ccc",
        borderRadius: "4px",
      }}
    />
  );
};

export default GraphComponent;
