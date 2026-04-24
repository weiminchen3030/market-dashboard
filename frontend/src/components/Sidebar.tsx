"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, LayoutDashboard, LineChart, Search, BarChart3, Sparkles } from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const routes = [
    { name: "Dashboard", path: "/", icon: LayoutDashboard },
    { name: "Dual-Asset Strategy", path: "/strategy", icon: LineChart },
    { name: "Market Screener", path: "/screener", icon: Search },
    { name: "Custom Screener", path: "/custom-screener", icon: Activity },
    { name: "Stock Explorer", path: "/explorer", icon: LayoutDashboard },
    { name: "Breadth Analysis", path: "/breadth", icon: BarChart3 },
  ];

  return (
    <div className="flex flex-col w-64 bg-[#11151d] border-r border-gray-800/80 min-h-screen p-4">
      <div className="flex items-center gap-3 px-2 py-6 mb-4">
        <div className="h-8 w-8 rounded bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
          <Activity className="h-5 w-5 text-white" />
        </div>
        <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-gray-100 to-gray-400">
          QuantOS
        </h1>
      </div>

      <nav className="flex-1 space-y-1.5">
        {routes.map((route) => {
          const isActive = pathname === route.path;
          const Icon = route.icon;
          return (
            <Link
              key={route.path}
              href={route.path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
                isActive
                  ? "bg-blue-600/10 text-blue-400 font-medium"
                  : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
              }`}
            >
              <Icon className="h-5 w-5" />
              {route.name}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto pt-6 border-t border-gray-800/80 pb-4 px-2">
        <p className="text-xs text-gray-500 font-mono">System Active • Port 8000</p>
      </div>
    </div>
  );
}
