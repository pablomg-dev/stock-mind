import { useEffect, useState, useCallback } from "react";
import { apiUrl, getAgentStatus, emergencyClose } from "./api.js";
import ConfigPanel from "./components/ConfigPanel.jsx";
import PnLChart from "./components/PnLChart.jsx";
import Portfolio from "./components/Portfolio.jsx";
import ReasoningFeed from "./components/ReasoningFeed.jsx";
import TradeHistory from "./components/TradeHistory.jsx";

export default function App() {
  const envMode = (import.meta.env.VITE_MODE || "").toLowerCase();
  const [mode, setMode] = useState(envMode || "paper");
  const [agentStatus, setAgentStatus] = useState("unknown");
  const [lastHeartbeat, setLastHeartbeat] = useState(null);
  const [isEmergencyLoading, setIsEmergencyLoading] = useState(false);
  const [emergencyResult, setEmergencyResult] = useState(null);

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

  const pollAgentStatus = useCallback(async () => {
    try {
      const status = await getAgentStatus();
      setAgentStatus(status.status || "unknown");
      setLastHeartbeat(status.last_heartbeat);
    } catch {
      setAgentStatus("unknown");
    }
  }, []);

  useEffect(() => {
    pollAgentStatus();
    const id = setInterval(pollAgentStatus, 10000);
    return () => clearInterval(id);
  }, [pollAgentStatus]);

  const handleEmergencyClose = async () => {
    if (!confirm("Are you sure you want to close all open positions immediately?")) return;
    setIsEmergencyLoading(true);
    setEmergencyResult(null);
    try {
      const result = await emergencyClose();
      setEmergencyResult(result);
    } catch (e) {
      setEmergencyResult({ error: e.message });
    } finally {
      setIsEmergencyLoading(false);
    }
  };

  const isLive = mode === "live";
  const badge = isLive
    ? "bg-rose-600/90 text-white ring-rose-400/50"
    : "bg-amber-500/90 text-slate-950 ring-amber-300/50";

  const statusColors = {
    running: "bg-emerald-500/20 text-emerald-300 ring-emerald-500/40",
    stopped: "bg-slate-500/20 text-slate-300 ring-slate-500/40",
    error: "bg-rose-500/20 text-rose-300 ring-rose-500/40",
    unknown: "bg-amber-500/15 text-amber-200 ring-amber-500/35",
  };

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
        <div className="flex items-center gap-3">
          <span
            className={`rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wider ring-2 ${statusColors[agentStatus] || statusColors.unknown}`}
            title={lastHeartbeat ? `Last heartbeat: ${new Date(lastHeartbeat).toLocaleString()}` : "No heartbeat"}
          >
            Agent: {agentStatus}
          </span>
          <span
            className={`rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-wider ring-2 ${badge}`}
          >
            {isLive ? "Live" : "Paper"}
          </span>
        </div>
      </header>

      {emergencyResult && (
        <div className={`mb-4 rounded-xl border p-4 ${emergencyResult.error ? "border-rose-800 bg-rose-950/30" : "border-emerald-800 bg-emerald-950/30"}`}>
          <p className={`text-sm ${emergencyResult.error ? "text-rose-300" : "text-emerald-300"}`}>
            {emergencyResult.error || emergencyResult.message}
          </p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-end gap-3">
            <button
              onClick={handleEmergencyClose}
              disabled={isEmergencyLoading}
              className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-rose-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isEmergencyLoading ? "Closing..." : "Emergency Close All"}
            </button>
          </div>
          <ReasoningFeed />
        </div>
        <ConfigPanel />
        <Portfolio />
        <PnLChart />
        <TradeHistory />
      </div>
    </div>
  );
}
