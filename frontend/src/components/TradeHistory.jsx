import { useCallback, useEffect, useState } from "react";
import { getTrades } from "../api.js";

function actionBadge(action) {
  const a = (action || "").toUpperCase();
  if (a === "BUY")
    return "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40";
  if (a === "SELL")
    return "bg-rose-500/20 text-rose-300 ring-1 ring-rose-500/40";
  return "bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/35";
}

function formatUSD(n) {
  if (typeof n !== "number") return "—";
  if (Math.abs(n) >= 1000)
    return `$${(n / 1000).toFixed(1)}k`;
  return `$${n.toFixed(2)}`;
}

export default function TradeHistory() {
  const [trades, setTrades] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getTrades();
      setTrades(Array.isArray(data) ? data : []);
      setError(null);
    } catch (e) {
      setError(e?.message || "Error loading trades");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 shadow-xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-white">
            Trade History
          </h2>
          <p className="text-sm text-slate-400">
            Recent executed trades from database
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="rounded-lg bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-200 ring-1 ring-slate-700 hover:bg-slate-800/80 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {error && (
        <p className="mb-3 rounded-lg border border-rose-900/50 bg-rose-950/40 px-3 py-2 text-sm text-rose-200">
          {error}
        </p>
      )}

      <div className="overflow-x-auto">
        {trades.length === 0 && !error && (
          <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 px-4 py-8 text-center text-slate-500">
            No trades in the database. Run the agent to execute trades.
          </div>
        )}

        {trades.length > 0 && (
          <p className="mb-3 text-xs text-slate-500">
            Showing last {Math.min(5, trades.length)} of {trades.length} trades
          </p>
        )}

        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="pb-2 pr-3">Time</th>
              <th className="pb-2 pr-3">Ticker</th>
              <th className="pb-2 pr-3">Action</th>
              <th className="pb-2 pr-3 text-right">Value</th>
              <th className="pb-2 pr-3 text-right">Price</th>
              <th className="pb-2 pr-3 text-center">Lev</th>
              <th className="pb-2 text-right">Mode</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {trades.slice(0, 5).map((t, i) => (
              <tr key={i} className="text-slate-300">
                <td className="whitespace-nowrap py-3 pr-3 font-mono text-xs text-slate-400">
                  {new Date(t.timestamp).toLocaleString(undefined, {
                    month: "2-digit",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </td>
                <td className="py-3 pr-3 text-xs text-slate-400">{t.ticker}</td>
                <td className="py-3 pr-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${actionBadge(t.action)}`}
                  >
                    {t.action}
                  </span>
                </td>
                <td className="whitespace-nowrap py-3 pr-3 text-right font-mono font-medium text-slate-100">
                  {formatUSD(t.usd_volume)}
                </td>
                <td className="whitespace-nowrap py-3 pr-3 text-right font-mono text-slate-300">
                  {typeof t.price === "number" ? `$${t.price.toFixed(2)}` : "—"}
                </td>
                <td className="py-3 pr-3 text-center font-mono text-xs text-slate-500">
                  {typeof t.leverage === "number" ? `${t.leverage}x` : "—"}
                </td>
                <td className="py-3 text-right">
                  <span className="text-xs capitalize text-slate-500">{t.mode}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
