"use client";

import useSWR from "swr";
import { BarChart3, Loader2, ServerCrash } from "lucide-react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const fetcher = (url: string) => fetch(url).then(res => res.json());

export default function BreadthPage() {
  const { data, error, isLoading } = useSWR(
    "http://127.0.0.1:8000/api/market/breadth",
    fetcher,
    { revalidateOnFocus: false }
  );

  const chartData = data?.history?.map((row: any) => ({
    date: row.Date?.slice(0, 10),
    Buy: row.Buy_Count,
    Sell: row.Sell_Count,
    SPY: row.SPY_Close,
  })) ?? [];

  return (
    <div className="p-8 font-sans w-full">
      <div className="flex flex-col gap-2 mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-cyan-500" />
          Market Breadth Analysis
        </h1>
        <p className="text-gray-400">
          Daily count of Buy vs. Sell signals across the S&P 500 and NASDAQ universe, compared against SPY price action.
        </p>
      </div>

      {isLoading && (
        <div className="flex justify-center items-center py-20">
          <Loader2 className="h-12 w-12 text-cyan-500 animate-spin" />
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-500 flex items-center gap-2">
          <ServerCrash className="h-5 w-5" />
          Cannot connect to backend. Make sure FastAPI is running on Port 8000.
        </div>
      )}

      {chartData.length > 0 && (
        <div className="bg-[#1A1F2B] rounded-xl p-6 border border-gray-800 shadow-xl animate-in fade-in">
          <h2 className="text-lg font-semibold text-white mb-6">Signal Breadth vs. SPY Price History</h2>
          <ResponsiveContainer width="100%" height={450}>
            <ComposedChart data={chartData} margin={{ top: 5, right: 30, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 11 }} tickFormatter={(v) => v?.slice(0, 7)} interval={30} />
              <YAxis yAxisId="left" tick={{ fill: "#6b7280", fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: "#6b7280", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1A1F2B", border: "1px solid #374151", borderRadius: "8px" }}
                labelStyle={{ color: "#9ca3af", fontSize: 12 }}
              />
              <Legend wrapperStyle={{ color: "#9ca3af" }} />
              <Bar yAxisId="left" dataKey="Buy" name="Buy Signals" fill="#10b981" opacity={0.75} />
              <Bar yAxisId="left" dataKey="Sell" name="Sell Signals" fill="#ef4444" opacity={0.75} />
              <Line yAxisId="right" type="monotone" dataKey="SPY" name="SPY Price" stroke="#60a5fa" strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {data && chartData.length === 0 && (
        <div className="bg-[#1A1F2B] rounded-xl p-12 border border-gray-800 text-center text-gray-500">
          No historical breadth data available yet. Run the Market Screener first to generate signal history.
        </div>
      )}
    </div>
  );
}
