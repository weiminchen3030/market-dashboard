"use client";

import { useEffect, useRef } from "react";
import { createChart, ColorType, CrosshairMode, CandlestickSeries, LineSeries, createSeriesMarkers } from "lightweight-charts";

export function CandlestickChart({
  data,
  colors = {
    backgroundColor: '#1A1F2B',
    textColor: '#D1D5DB',
    upColor: '#26a69a',
    downColor: '#ef5350',
  }
}: { data: any[], colors?: any }) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return;

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current?.clientWidth });
    };

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.backgroundColor },
        textColor: colors.textColor,
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      width: chartContainerRef.current.clientWidth,
      height: 500,
    });
    
    // Auto-fit bounds
    chart.timeScale().fitContent();

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: colors.upColor,
      downColor: colors.downColor,
      borderVisible: false,
      wickUpColor: colors.upColor,
      wickDownColor: colors.downColor,
    });

    const ohlc = data.map(d => ({
      time: d.Date,
      open: d.Open,
      high: d.High,
      low: d.Low,
      close: d.Close,
    }));
    candlestickSeries.setData(ohlc);
    
    // Add Markers
    const markers: any[] = [];
    data.forEach((d) => {
      if (d.Is_Buy) {
        markers.push({ time: d.Date, position: 'belowBar', color: colors.upColor, shape: 'arrowUp', text: 'BUY' });
      } else if (d.Is_Sell) {
        markers.push({ time: d.Date, position: 'aboveBar', color: colors.downColor, shape: 'arrowDown', text: 'SELL' });
      }
    });
    createSeriesMarkers(candlestickSeries, markers);

    // Add EMAs
    const ema5 = chart.addSeries(LineSeries, { color: '#F9A825', lineWidth: 1, crosshairMarkerVisible: false });
    ema5.setData(data.map(d => ({ time: d.Date, value: d.EMA5 })));

    const ema13 = chart.addSeries(LineSeries, { color: '#29B6F6', lineWidth: 1, crosshairMarkerVisible: false });
    ema13.setData(data.map(d => ({ time: d.Date, value: d.EMA13 })));

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data, colors]);

  if (!data || data.length === 0) return <div className="text-gray-500 text-center py-20">No historical data available.</div>;

  return <div ref={chartContainerRef} className="w-full relative shadow-2xl rounded-xl overflow-hidden border border-gray-800/80" />;
}
