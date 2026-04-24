"use client";

import useSWR from "swr";
import { Activity, Gauge, TrendingDown, Target, Zap, ServerCrash } from "lucide-react";

const fetcher = (url: string) => fetch(url).then(res => res.json());

export default function Dashboard() {
  const { data, error, isLoading } = useSWR("http://127.0.0.1:8000/api/market/dashboard", fetcher, { refreshInterval: 60000 });

  const getStatusLight = (val: number, type: string) => {
    if (type === "fear") {
      if (val <= 25) return <span className="text-red-500 font-bold">Extreme Fear</span>;
      if (val <= 45) return <span className="text-orange-400 font-bold">Fear</span>;
      if (val <= 55) return <span className="text-yellow-400 font-bold">Neutral</span>;
      if (val <= 75) return <span className="text-green-400 font-bold">Greed</span>;
      return <span className="text-emerald-500 font-bold">Extreme Greed</span>;
    }
    if (type === "naaim") {
      if (val <= 40) return <span className="text-red-500 font-bold">Bearish</span>;
      if (val <= 80) return <span className="text-yellow-400 font-bold">Neutral</span>;
      return <span className="text-emerald-500 font-bold">Bullish</span>;
    }
    if (type === "vix") {
      if (val <= 15) return <span className="text-emerald-500 font-bold">Complacency</span>;
      if (val <= 20) return <span className="text-yellow-400 font-bold">Normal</span>;
      return <span className="text-red-500 font-bold">High Volatility (Fear)</span>;
    }
    return <span className="text-gray-400">Unknown</span>;
  };

  return (
    <div className="p-8 font-sans w-full">
      <div className="flex flex-col gap-2 mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Gauge className="h-8 w-8 text-blue-500" />
          Daily Market Intelligence
        </h1>
        <p className="text-gray-400">Real-time macro data, volatility indicators, and institutional positioning metrics.</p>
      </div>

      {isLoading && (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-500 flex items-center gap-2">
          <ServerCrash className="h-5 w-5" />
          Cannot connect to Python Backend. Make sure FastAPI server is running on Port 8000.
        </div>
      )}

      {data && (
        <div className="space-y-8 animate-in fade-in duration-500">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <MetricCard
              title="CNN Fear & Greed"
              value={data.playwright_data?.CNNFearGreed || "N/A"}
              status={getStatusLight(Number(data.playwright_data?.CNNFearGreed), "fear")}
              icon={<Target className="text-pink-400" />}
            />
            <MetricCard
              title="Crypto Fear & Greed"
              value={data.crypto_fng || "N/A"}
              status={getStatusLight(Number(data.crypto_fng), "fear")}
              icon={<Zap className="text-blue-400" />}
            />
            <MetricCard
              title="NAAIM Exposure Index"
              value={data.naaim?.value || "N/A"}
              status={getStatusLight(Number(data.naaim?.value), "naaim")}
              icon={<Activity className="text-orange-400" />}
              sub={data.naaim?.date}
            />
            <MetricCard
              title="VIX"
              value={data.vix_data?.VIX || "N/A"}
              status={getStatusLight(Number(data.vix_data?.VIX), "vix")}
              icon={<TrendingDown className="text-purple-400" />}
            />
            <MetricCard
              title="Trading Logic Breadth"
              value={data.playwright_data?.TradingLogic || "N/A"}
              status={<span className="text-gray-400">Score / 1100</span>}
              icon={<Activity className="text-emerald-400" />}
            />
            <MetricCard
              title="Truflation US CPI"
              value={data.playwright_data?.Truflation || "N/A"}
              status={<span className="text-gray-400">Live Inflation</span>}
              icon={<Gauge className="text-red-400" />}
            />
          </div>

          <div className="bg-[#1A1F2B] rounded-xl p-6 border border-gray-800 shadow-xl">
            <h2 className="text-lg font-semibold text-white mb-4">Volatility Index Matrix</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <div className="text-sm text-gray-500">S&P 500 VIX</div>
                <div className="text-2xl font-bold text-white">{data.vix_data?.VIX || "N/A"}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500">VVIX (Vol of VIX)</div>
                <div className="text-2xl font-bold text-white">{data.vix_data?.VVIX || "N/A"}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500">VIX / VVIX Ratio</div>
                <div className="text-2xl font-bold text-blue-400">{data.vix_data?.["VIX/VVIX"] || "N/A"}</div>
              </div>
            </div>
          </div>

          <div className="bg-[#1A1F2B] rounded-xl p-6 border border-gray-800 shadow-xl">
            <h2 className="text-lg font-semibold text-white mb-4">AAII Sentiment Survey (Retail)</h2>
            <div className="flex justify-between items-center bg-[#0E1117] p-4 rounded-lg">
              <div className="text-center">
                <div className="text-sm text-gray-500 mb-1">Bullish 🟢</div>
                <div className="text-xl font-bold text-emerald-500">{data.playwright_data?.AAII?.Bullish || "N/A"}</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-500 mb-1">Neutral ⚪</div>
                <div className="text-xl font-bold text-gray-300">{data.playwright_data?.AAII?.Neutral || "N/A"}</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-500 mb-1">Bearish 🔴</div>
                <div className="text-xl font-bold text-red-500">{data.playwright_data?.AAII?.Bearish || "N/A"}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ title, value, icon, status, sub }: { title: string, value: string | number, icon: React.ReactNode, status: React.ReactNode, sub?: string }) {
  return (
    <div className="bg-[#1A1F2B] p-5 rounded-xl border border-gray-800/80 hover:border-gray-600 transition-colors flex flex-col justify-between">
      <div className="flex justify-between items-start mb-4">
        <div>
          <div className="text-gray-400 font-medium text-sm mb-1">{title}</div>
          <div className="text-3xl font-bold text-white">{value}</div>
          {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
        </div>
        <div className="opacity-70 p-2 bg-[#0E1117] rounded-lg">{icon}</div>
      </div>
      <div className="mt-auto border-t border-gray-800 pt-3">{status}</div>
    </div>
  );
}
