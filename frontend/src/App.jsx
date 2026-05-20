import { useEffect, useState } from "react";
import { apiUrl } from "./api.js";
import ConfigPanel from "./components/ConfigPanel.jsx";
import PnLChart from "./components/PnLChart.jsx";
import Portfolio from "./components/Portfolio.jsx";
import ReasoningFeed from "./components/ReasoningFeed.jsx";

export default function App() {
  const envMode = (import.meta.env.VITE_MODE || "").toLowerCase();
  const [mode, setMode] = useState(envMode || "paper");

  useEffect(() => {
    let cancelled = false;
    fetch(apiUrl("/config"))
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (!cancelled && j?.mode) setMode(String(j.mode).toLowerCase());
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const isLive = mode === "live";
  const badge = isLive
    ? "bg-rose-600/90 text-white ring-rose-400/50"
    : "bg-amber-500/90 text-slate-950 ring-amber-300/50";

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            StockMind
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            xStocks · Kraken CLI · Gemini — reasoning dashboard
          </p>
        </div>
        <span
          className={`rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-wider ring-2 ${badge}`}
        >
          {isLive ? "Live" : "Paper"}
        </span>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <ReasoningFeed />
        </div>
        <ConfigPanel />
        <Portfolio />
        <PnLChart />
      </div>
    </div>
  );
}
