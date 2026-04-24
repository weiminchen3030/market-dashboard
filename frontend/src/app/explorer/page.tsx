"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { Search, DollarSign, Activity, Building2 } from "lucide-react";
import { CandlestickChart } from "@/components/CandlestickChart";

const fetcher = (url: string) => fetch(url).then(res => res.json());

function ExplorerContent() {
  const searchParams = useSearchParams();
  const initialTicker = searchParams.get("ticker")?.toUpperCase() || "AAPL";

  const [query, setQuery] = useState(initialTicker);
  const [ticker, setTicker] = useState(initialTicker);

  useEffect(() => {
    const t = searchParams.get("ticker");
    if (t) {
      const upper = t.toUpperCase();
      setQuery(upper);
      setTicker(upper);
    }
  }, [searchParams]);

  const { data: profileData, error: profileErr, isLoading: isProfileLoading } = useSWR(
    ticker ? `http://127.0.0.1:8000/api/market/stock/${ticker}` : null,
    fetcher
  );

  const { data: histData, error: histErr, isLoading: isHistLoading } = useSWR(
    ticker ? `http://127.0.0.1:8000/api/market/stock/${ticker}/history` : null,
    fetcher
  );

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query) setTicker(query.toUpperCase());
  };

  const formatMcap = (val: number | null) => {
    if (!val) return "N/A";
    if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
    if (val >= 1e9)  return `$${(val / 1e9).toFixed(2)}B`;
    if (val >= 1e6)  return `$${(val / 1e6).toFixed(2)}M`;
    return `$${val}`;
  };

  return (
    <div className="p-8 font-sans w-full">
      <div className="space-y-6">
        <div className="flex flex-col gap-2 mb-8">
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Activity className="h-8 w-8 text-blue-500" />
            Stock Explorer
          </h1>
          <p className="text-gray-400">Instantly pull up technical charts and historical buy/sell signals.</p>
        </div>

        <form onSubmit={handleSearch} className="flex gap-4">
          <div className="relative max-w-md w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter ticker (e.g. AAPL, NVDA)..."
              className="w-full bg-[#1A1F2B] border border-gray-700/50 rounded-lg py-3 pl-10 pr-4 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button type="submit" className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-lg font-medium transition-colors">
            Analyze
          </button>
        </form>

        {(isProfileLoading || isHistLoading) && (
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        )}

        {(profileErr || histErr) && (
          <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400">
            Failed to load data for {ticker}. The ticker might not exist.
          </div>
        )}

        {profileData && profileData.profile && histData && histData.data && (
          <div className="space-y-6 animate-in fade-in duration-500">
            <div className="bg-[#1A1F2B] rounded-xl p-6 border border-gray-800/80 shadow-2xl space-y-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                    {profileData.profile.name}{" "}
                    <span className="text-gray-500 font-normal text-lg">({profileData.symbol})</span>
                  </h2>
                  <div className="flex gap-4 mt-2 text-sm text-gray-400">
                    <span className="flex items-center gap-1"><Building2 className="h-4 w-4"/> {profileData.profile.sector}</span>
                    <span>•</span>
                    <span>{profileData.profile.industry}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-extrabold text-white">${profileData.latest_technicals?.price?.toFixed(2)}</div>
                </div>
              </div>
              <CandlestickChart data={histData.data} />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard title="Market Cap" value={formatMcap(profileData.profile.marketCap)} icon={<DollarSign className="text-blue-400"/>} />
              <MetricCard title="P/E Ratio" value={profileData.profile.trailingPE ? profileData.profile.trailingPE.toFixed(2) : "N/A"} icon={<Activity className="text-purple-400"/>} />
              <MetricCard title="Analyst Avg Target" value={profileData.profile.targetMeanPrice ? `$${profileData.profile.targetMeanPrice.toFixed(2)}` : "N/A"} icon={<Activity className="text-emerald-400"/>} />
              <MetricCard title="Beta" value={profileData.profile.beta?.toFixed(2) || "N/A"} icon={<Activity className="text-yellow-400"/>} />
            </div>

            <div className="bg-[#1A1F2B] rounded-xl p-6 border border-gray-800/80">
              <h3 className="text-lg font-semibold text-gray-200 mb-3">Business Summary</h3>
              <p className="text-gray-400 leading-relaxed text-sm">{profileData.profile.summary}</p>
              {profileData.profile.website && (
                <a href={profileData.profile.website} target="_blank" rel="noreferrer" className="inline-block mt-4 text-blue-400 hover:text-blue-300 text-sm font-medium">
                  Visit Official Website →
                </a>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon }: { title: string, value: string | number, icon: React.ReactNode }) {
  return (
    <div className="bg-[#1A1F2B] p-5 rounded-xl border border-gray-800/80 hover:border-gray-600 transition-colors flex flex-col justify-between">
      <div className="text-gray-400 font-medium text-sm mb-2">{title}</div>
      <div className="text-2xl font-bold flex items-center justify-between">
        {value}
        <div className="opacity-70 h-6 w-6">{icon}</div>
      </div>
    </div>
  );
}

export default function SingleStockExplorer() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-screen"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div></div>}>
      <ExplorerContent />
    </Suspense>
  );
}
