"use client";

import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from "recharts";
import { TrendingUp, Loader2, ArrowUpRight, ArrowDownRight, DollarSign } from "lucide-react";

export default function StrategyPage() {
  const [ticker, setTicker] = useState("SPY");
  const [levTicker, setLevTicker] = useState("UPRO");
  const [investment, setInvestment] = useState(1000);
  const [result, setResult] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/api/market/strategy/${ticker}?lev_ticker=${levTicker}&monthly_investment=${investment}`
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to run strategy");
      }
      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (v: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v);

  const formatPct = (v: number) => `${(v * 100).toFixed(1)}%`;

  return (
    <div className="p-8 font-sans w-full">
      <div className="flex flex-col gap-2 mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <TrendingUp className="h-8 w-8 text-purple-500" />
          Dual-Asset Strategy Backtester
        </h1>
        <p className="text-gray-400">
          10-year compounding engine: automatically switches between a base ETF and a leveraged ETF based on VIX / DeMark signals.
        </p>
      </div>

      {/* Config Panel */}
      <div className="bg-[#1A1F2B] p-6 rounded-xl border border-gray-800 shadow-xl mb-8">
        <form onSubmit={handleRun} className="flex flex-col md:flex-row gap-4 items-end">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-400">Base ETF</label>
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="bg-[#0E1117] border border-gray-700 rounded-lg px-4 py-3 text-white w-32 focus:outline-none focus:border-purple-500"
              placeholder="SPY"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-400">Leveraged ETF</label>
            <input
              value={levTicker}
              onChange={(e) => setLevTicker(e.target.value.toUpperCase())}
              className="bg-[#0E1117] border border-gray-700 rounded-lg px-4 py-3 text-white w-32 focus:outline-none focus:border-purple-500"
              placeholder="UPRO"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-400">Monthly Investment ($)</label>
            <input
              type="number"
              value={investment}
              onChange={(e) => setInvestment(Number(e.target.value))}
              className="bg-[#0E1117] border border-gray-700 rounded-lg px-4 py-3 text-white w-40 focus:outline-none focus:border-purple-500"
              min={100}
            />
          </div>
          <button
            disabled={isLoading}
            type="submit"
            className="bg-purple-600 hover:bg-purple-500 text-white px-8 py-3 rounded-lg font-medium transition-colors shadow-lg shadow-purple-500/20 disabled:opacity-50 flex items-center gap-2"
          >
            {isLoading && <Loader2 className="animate-spin h-5 w-5" />}
            {isLoading ? "Running…" : "Run Backtest"}
          </button>
        </form>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 mb-8">{error}</div>
      )}

      {result && (
        <div className="space-y-6 animate-in fade-in duration-500">
          {/* Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              title="Strategy Final Value"
              value={formatCurrency(result.metrics.final_equity)}
              sub={`Return: ${formatPct(result.metrics.strategy_return)}`}
              icon={<DollarSign className="text-purple-400"/>}
              positive={result.metrics.strategy_return > 0}
            />
            <MetricCard
              title="Buy & Hold Final"
              value={formatCurrency(result.metrics.final_baseline_equity)}
              sub={`Return: ${formatPct(result.metrics.baseline_return)}`}
              icon={<DollarSign className="text-blue-400"/>}
              positive={result.metrics.baseline_return > 0}
            />
            <MetricCard
              title="Alpha (Excess Return)"
              value={formatPct(result.metrics.excess_alpha)}
              sub="vs Buy & Hold"
              icon={result.metrics.excess_alpha >= 0 ? <ArrowUpRight className="text-emerald-400"/> : <ArrowDownRight className="text-red-400"/>}
              positive={result.metrics.excess_alpha >= 0}
            />
            <MetricCard
              title="Trades Executed"
              value={String(result.history.length)}
              sub="Total switches"
              icon={<TrendingUp className="text-yellow-400"/>}
              positive={true}
            />
          </div>

          {/* Chart */}
          <div className="bg-[#1A1F2B] rounded-xl p-6 border border-gray-800 shadow-xl">
            <h2 className="text-lg font-semibold text-white mb-6">Portfolio Equity Curve (10 Years)</h2>
            <ResponsiveContainer width="100%" height={380}>
              <AreaChart data={result.chart} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
                <defs>
                  <linearGradient id="stratGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="baseGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="Date" tick={{ fill: "#6b7280", fontSize: 11 }} tickFormatter={(v) => v.slice(0, 7)} interval={180} />
                <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fill: "#6b7280", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1A1F2B", border: "1px solid #374151", borderRadius: "8px" }}
                  labelStyle={{ color: "#9ca3af" }}
                  formatter={(val: any) => [`$${Number(val).toLocaleString()}`, ""]}
                />
                <Legend wrapperStyle={{ color: "#9ca3af" }} />
                <Area type="monotone" dataKey="Equity" name="Strategy" stroke="#a855f7" fill="url(#stratGrad)" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="Baseline_Equity" name="Buy & Hold" stroke="#3b82f6" fill="url(#baseGrad)" strokeWidth={1.5} strokeDasharray="5 3" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Trade Ledger */}
          {result.history.length > 0 && (
            <div className="bg-[#1A1F2B] rounded-xl border border-gray-800 overflow-hidden shadow-xl">
              <div className="p-5 border-b border-gray-800">
                <h2 className="text-lg font-semibold text-white">Trade Ledger</h2>
              </div>
              <div className="overflow-x-auto max-h-72 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-[#1A1F2B]">
                    <tr className="text-gray-500 text-xs uppercase border-b border-gray-800">
                      <th className="px-5 py-3 text-left">Date</th>
                      <th className="px-5 py-3 text-left">Action</th>
                      <th className="px-5 py-3 text-left">Position</th>
                      <th className="px-5 py-3 text-right">Equity</th>
                      <th className="px-5 py-3 text-right">Cash</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/50">
                    {result.history.map((trade: any, i: number) => (
                      <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                        <td className="px-5 py-2.5 text-gray-400 font-mono">{trade.Date}</td>
                        <td className="px-5 py-2.5">
                          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                            trade.Action?.includes("Buy") ? "bg-emerald-500/10 text-emerald-400" :
                            trade.Action?.includes("Sell") ? "bg-red-500/10 text-red-400" :
                            "bg-gray-500/10 text-gray-400"
                          }`}>
                            {trade.Action}
                          </span>
                        </td>
                        <td className="px-5 py-2.5 text-gray-300">{trade.Position}</td>
                        <td className="px-5 py-2.5 text-right text-white font-mono">{formatCurrency(trade.Equity)}</td>
                        <td className="px-5 py-2.5 text-right text-gray-400 font-mono">{formatCurrency(trade.Cash)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MetricCard({ title, value, sub, icon, positive }: any) {
  return (
    <div className="bg-[#1A1F2B] p-5 rounded-xl border border-gray-800 hover:border-gray-600 transition-colors">
      <div className="flex justify-between items-start mb-3">
        <div className="text-gray-400 text-sm font-medium">{title}</div>
        <div className="opacity-70">{icon}</div>
      </div>
      <div className={`text-2xl font-bold ${positive ? "text-white" : "text-red-400"}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-1">{sub}</div>
    </div>
  );
}
