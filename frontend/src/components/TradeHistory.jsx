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

export default function TradeHistory() {
  const [trades, setTrades] = useState([]);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const data = await getTrades();
      setTrades(Array.isArray(data) ? data : []);
      setError(null);
    } catch (e) {
      setError(e?.message || "Error loading trades");
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
          className="rounded-lg bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-200 ring-1 ring-slate-700 hover:bg-slate-800/80"
        >
          Refresh
        </button>
      </div>

      {error && (
        <p className="mb-3 rounded-lg border border-rose-900/50 bg-rose-950/40 px-3 py-2 text-sm text-rose-200">
          {error}
        </p>
      )}

      <div className="max-h-[400px] overflow-y-auto">
        {trades.length === 0 && !error && (
          <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 px-4 py-8 text-center text-slate-500">
            No trades in the database. Run the agent to execute trades.
          </div>
        )}

        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-slate-900/95">
            <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="pb-2 pr-4">Time</th>
              <th className="pb-2 pr-4">Ticker</th>
              <th className="pb-2 pr-4">Action</th>
              <th className="pb-2 pr-4 text-right">Volume</th>
              <th className="pb-2 pr-4 text-right">Price</th>
              <th className="pb-2 text-right">Mode</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {trades.map((t, i) => (
              <tr key={i} className="text-slate-300">
                <td className="py-3 pr-4 font-mono text-xs text-slate-400">
                  {new Date(t.timestamp).toLocaleString(undefined, {
                    month: "2-digit",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </td>
                <td className="py-3 pr-4">{t.ticker}</td>
                <td className="py-3 pr-4">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${actionBadge(t.action)}`}
                  >
                    {t.action}
                  </span>
                </td>
                <td className="py-3 pr-4 text-right font-mono">
                  {typeof t.volume === "number" ? t.volume.toFixed(4) : "—"}
                </td>
                <td className="py-3 pr-4 text-right font-mono">
                  {typeof t.price === "number" ? `$${t.price.toFixed(2)}` : "—"}
                </td>
                <td className="py-3 text-right">
                  <span className="text-xs capitalize text-slate-400">{t.mode}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
