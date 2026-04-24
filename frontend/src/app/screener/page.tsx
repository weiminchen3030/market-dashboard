"use client";

import { useState } from "react";
import useSWR from "swr";
import { Search, Loader2, Activity, Zap } from "lucide-react";
import { CandlestickChart } from "@/components/CandlestickChart";

const fetcher = (url: string) => fetch(url).then(res => res.json());

export default function MarketScreenerPage() {
  const [universe, setUniverse] = useState("SP500");
  const [targetDate, setTargetDate] = useState("");
  const [results, setResults] = useState<any[] | null>(null);
  const [isCached, setIsCached] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scanTime, setScanTime] = useState<number | null>(null);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const { data: histData, isLoading: isHistLoading } = useSWR(
    selectedTicker ? `http://127.0.0.1:8000/api/market/stock/${selectedTicker}/history` : null,
    fetcher
  );

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResults(null);
    setSelectedTicker(null);
    const start = Date.now();

    try {
      const url = targetDate
        ? `http://127.0.0.1:8000/api/market/screener/index/${universe}?date=${targetDate}`
        : `http://127.0.0.1:8000/api/market/screener/index/${universe}`;

      const res = await fetch(url);
      if (!res.ok) throw new Error("API responded with an error.");
      const data = await res.json();
      setResults(data.signals || []);
      setIsCached(data.cached || false);
      setScanTime((Date.now() - start) / 1000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const buyCount = results ? results.filter((r) => r.Signal === "Buy").length : 0;
  const sellCount = results ? results.filter((r) => r.Signal === "Sell").length : 0;

  return (
    <div className="p-8">
      <div className="mb-8 flex flex-col gap-2">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Search className="h-8 w-8 text-indigo-500" />
          Advanced Market Screener
        </h1>
        <p className="text-gray-400 max-w-3xl">
          Scan entire stock universes (S&P 500, NASDAQ 100) to identify Buy / Sell signals based on EMA Crossovers, MACD, and RSI.
        </p>
      </div>

      {/* Controls */}
      <div className="bg-[#1A1F2B] p-6 rounded-xl border border-gray-800 shadow-xl mb-8">
        <form onSubmit={handleScan} className="flex flex-col md:flex-row gap-4 items-end">
          <div className="flex-1 flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-400">Universe</label>
            <select
              value={universe}
              onChange={(e) => setUniverse(e.target.value)}
              className="bg-[#0E1117] border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-indigo-500 transition-colors"
            >
              <option value="SP500">S&P 500</option>
              <option value="NASDAQ100">NASDAQ 100</option>
              <option value="WATCHLIST">Watchlist</option>
            </select>
          </div>

          <div className="flex-1 flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-400">Target Date (Optional – for backtesting)</label>
            <input
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="bg-[#0E1117] border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-indigo-500 transition-colors"
              max={new Date().toISOString().split("T")[0]}
            />
          </div>

          <button
            disabled={isLoading}
            type="submit"
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-lg font-medium transition-colors shadow-lg shadow-indigo-500/20 disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
          >
            {isLoading && <Loader2 className="animate-spin h-5 w-5" />}
            {isLoading ? "Scanning…" : "Run Live Screener"}
          </button>
        </form>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 mb-8">{error}</div>
      )}

      {results !== null && (
        <div className="animate-in fade-in duration-500">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-[#1A1F2B] p-4 rounded-xl border border-gray-800 text-center">
              <div className="text-xs text-gray-400 mb-1 uppercase tracking-wide">Total Signals</div>
              <div className="text-2xl font-bold text-white">{results.length}</div>
              {isCached && (
                <div className="flex items-center justify-center gap-1 text-xs text-yellow-400 mt-1">
                  <Zap className="h-3 w-3" /> Cached result
                </div>
              )}
            </div>
            <div className="bg-emerald-500/5 p-4 rounded-xl border border-emerald-500/20 text-center">
              <div className="text-xs text-emerald-400 mb-1 uppercase tracking-wide">Buy Signals</div>
              <div className="text-2xl font-bold text-emerald-400">{buyCount}</div>
            </div>
            <div className="bg-red-500/5 p-4 rounded-xl border border-red-500/20 text-center">
              <div className="text-xs text-red-400 mb-1 uppercase tracking-wide">Sell Signals</div>
              <div className="text-2xl font-bold text-red-400">{sellCount}</div>
            </div>
          </div>

          {/* Two-column layout: table + chart */}
          <div className="flex gap-6">
            {/* Signal Table */}
            <div className="bg-[#1A1F2B] rounded-xl border border-gray-800 overflow-hidden flex-shrink-0 w-64">
              <div className="px-4 py-3 border-b border-gray-800 flex justify-between items-center">
                <h2 className="text-sm font-semibold text-white">Signals</h2>
                <span className="text-xs text-gray-500">{scanTime?.toFixed(1)}s</span>
              </div>

              {results.length === 0 ? (
                <div className="p-8 text-center text-gray-500 text-sm">No signals found.</div>
              ) : (
                <div className="overflow-y-auto max-h-[520px]">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-[#1A1F2B] z-10">
                      <tr className="text-gray-500 text-xs uppercase border-b border-gray-800">
                        <th className="px-3 py-2 text-left">Symbol</th>
                        <th className="px-3 py-2 text-left">Sig</th>
                        <th className="px-3 py-2 text-right">Price</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800/50">
                      {results.map((row, idx) => (
                        <tr
                          key={idx}
                          className={`cursor-pointer transition-colors text-sm ${
                            selectedTicker === row.Symbol
                              ? "bg-indigo-500/10"
                              : "hover:bg-white/[0.04]"
                          }`}
                          onClick={() => setSelectedTicker(row.Symbol)}
                        >
                          <td className="px-3 py-1.5 font-bold text-blue-400">{row.Symbol}</td>
                          <td className="px-3 py-1.5">
                            <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${
                              row.Signal === "Buy"
                                ? "bg-emerald-500/10 text-emerald-400"
                                : "bg-red-500/10 text-red-400"
                            }`}>
                              {row.Signal}
                            </span>
                          </td>
                          <td className="px-3 py-1.5 text-right text-gray-300 font-mono text-xs">
                            ${row["Current Price"]?.toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Chart Panel */}
            <div className="flex-1 bg-[#1A1F2B] rounded-xl border border-gray-800 overflow-hidden">
              {!selectedTicker ? (
                <div className="h-full flex flex-col items-center justify-center text-gray-600 p-8">
                  <Activity className="h-12 w-12 mb-3 opacity-30" />
                  <p className="text-sm">Click any ticker on the left to view its chart</p>
                </div>
              ) : (
                <div className="h-full flex flex-col">
                  <div className="px-5 py-4 border-b border-gray-800 flex justify-between items-center">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Activity className="h-5 w-5 text-blue-500" />
                      {selectedTicker}
                    </h3>
                    <a
                      href={`/explorer?ticker=${selectedTicker}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      Full Profile ↗
                    </a>
                  </div>
                  <div className="flex-1 p-2">
                    {isHistLoading ? (
                      <div className="h-full flex items-center justify-center">
                        <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
                      </div>
                    ) : histData?.data ? (
                      <CandlestickChart data={histData.data} />
                    ) : (
                      <div className="h-full flex items-center justify-center text-red-400 text-sm">
                        Failed to load chart data.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
