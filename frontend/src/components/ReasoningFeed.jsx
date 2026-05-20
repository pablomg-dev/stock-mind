import { useCallback, useEffect, useState } from "react";
import { apiUrl, wsUrl } from "../api.js";

// Singleton WebSocket connection
let ws = null;
let reconnectTimer = null;
let listeners = new Set();

/**
 * @typedef {{ timestamp: string, ticker: string, action: string, confidence: number, reasoning: string, risk_note: string }} Decision
 */

function actionBadge(action) {
  const a = (action || "").toUpperCase();
  if (a === "BUY")
    return "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40";
  if (a === "SELL")
    return "bg-rose-500/20 text-rose-300 ring-1 ring-rose-500/40";
  return "bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/35";
}

function getWebSocket() {
  if (
    ws &&
    (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
  ) {
    return ws;
  }

  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
  }

  const url = wsUrl();
  console.log("Creating singleton WebSocket connection to:", url);

  ws = new WebSocket(url);

  ws.onopen = () => {
    console.log("Singleton WebSocket connected");
  };

  ws.onclose = () => {
    console.log("Singleton WebSocket closed, reconnecting in 3 seconds");
    ws = null;
    reconnectTimer = setTimeout(getWebSocket, 3000);
  };

  ws.onerror = (e) => {
    console.error("Singleton WebSocket error:", e);
  };

  ws.onmessage = (ev) => {
    try {
      const d = JSON.parse(ev.data);
      listeners.forEach((listener) => listener(d));
    } catch {
      /* ignore */
    }
  };

  return ws;
}

export default function ReasoningFeed() {
  /** @type {[Decision[], React.Dispatch<React.SetStateAction<Decision[]>>]} */
  const [items, setItems] = useState([]);
  /** @type {[Decision | null, React.Dispatch<React.SetStateAction<Decision | null>>]} */
  const [live, setLive] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch(apiUrl("/decisions"));
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setItems(Array.isArray(data) ? data : []);
      setError(null);
    } catch (e) {
      setError(e?.message || "Error loading decisions");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    console.log("Component mounted, subscribing to WebSocket");

    const handleMessage = (data) => {
      setLive(data);
    };

    listeners.add(handleMessage);
    getWebSocket();

    return () => {
      console.log("Component unmounted, unsubscribing from WebSocket");
      listeners.delete(handleMessage);
    };
  }, []);

  const merged =
    live &&
    !items.some(
      (x) => x.timestamp === live.timestamp && x.reasoning === live.reasoning,
    )
      ? [live, ...items]
      : items;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 shadow-xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-white">
            Agent Reasoning
          </h2>
          <p className="text-sm text-slate-400">
            Recent decisions and real-time feed (WebSocket)
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

      <ul className="max-h-[480px] space-y-3 overflow-y-auto pr-1">
        {merged.length === 0 && !error && (
          <li className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 px-4 py-8 text-center text-slate-500">
            No decisions in the database. Run the agent to populate the history.
          </li>
        )}
        {merged.map((d, i) => (
          <li
            key={`${d.timestamp}-${i}`}
            className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"
          >
            <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
              <span className="font-mono text-xs text-slate-500">
                {new Date(d.timestamp).toLocaleString(undefined, {
                  year: "numeric",
                  month: "2-digit",
                  day: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </span>
              <span className="text-slate-300">{d.ticker}</span>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${actionBadge(d.action)}`}
              >
                {d.action}
              </span>
              <span className="ml-auto font-mono text-slate-200">
                {Math.round((Number(d.confidence) || 0) * 100)}% confidence
              </span>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-slate-200">
              {d.reasoning}
            </p>
            <p className="mt-2 text-xs text-amber-200/90">
              <span className="font-semibold text-amber-400/90">Risk: </span>
              {d.risk_note}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
