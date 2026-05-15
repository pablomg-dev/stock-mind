import { useCallback, useEffect, useState } from "react";
import { apiUrl } from "../api.js";

export default function Portfolio() {
  const [mode, setMode] = useState("paper");
  const [decisions, setDecisions] = useState([]);
  const [balance, setBalance] = useState(null);
  const [error, setError] = useState(null);

  const poll = useCallback(async () => {
    try {
      console.log("Portfolio: Starting poll");
      const [cfg, dec, bal] = await Promise.all([
        fetch(apiUrl("/config")),
        fetch(apiUrl("/decisions")),
        fetch(apiUrl("/balance")),
      ]);
      console.log("Portfolio: Fetches completed", {
        cfg: cfg.ok,
        dec: dec.ok,
        bal: bal.ok,
      });
      if (cfg.ok) {
        const j = await cfg.json();
        if (j?.mode) setMode(String(j.mode).toLowerCase());
      }
      if (dec.ok) {
        const list = await dec.json();
        setDecisions(Array.isArray(list) ? list : []);
      }
      if (bal.ok) {
        const b = await bal.json();
        console.log("Portfolio: Balance data", b);
        setBalance(b);
      } else {
        console.error(
          "Portfolio: Balance fetch failed",
          bal.status,
          bal.statusText,
        );
        const errorText = await bal.text();
        console.error("Portfolio: Balance error response", errorText);
      }
      setError(null);
    } catch (e) {
      console.error("Portfolio: Poll error", e);
      setError(e?.message || "Error de red");
    }
  }, []);

  useEffect(() => {
    poll();
    const id = setInterval(poll, 30_000);
    return () => clearInterval(id);
  }, [poll]);

  const last = decisions[0];
  const buys = decisions.filter(
    (d) => String(d.action).toUpperCase() === "BUY",
  ).length;
  const sells = decisions.filter(
    (d) => String(d.action).toUpperCase() === "SELL",
  ).length;
  const holds = decisions.filter(
    (d) => String(d.action).toUpperCase() === "HOLD",
  ).length;

  // Extract balance data from Kraken Futures response
  const equity =
    balance?.collateral || balance?.portfolio_value || balance?.equity || 0;
  const dailyPnl =
    balance?.unrealized_pnl || balance?.pnl || balance?.daily_pnl || 0;
  const margin = balance?.available_margin || balance?.margin || 0;
  const balanceError = balance?.error;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 shadow-xl">
      <div className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight text-white">
          Portfolio
        </h2>
        <p className="text-sm text-slate-400">
          Polling cada 30s. Balance en vivo desde Kraken.
        </p>
      </div>

      {error && <p className="mb-3 text-sm text-rose-300">{error}</p>}

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Equity Total
          </p>
          <p className="mt-1 font-mono text-lg font-semibold text-white">
            $
            {typeof equity === "number"
              ? equity.toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })
              : "—"}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Balance total de la cuenta
          </p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            PnL del Día
          </p>
          <p
            className={`mt-1 font-mono text-lg font-semibold ${dailyPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}
          >
            {typeof dailyPnl === "number"
              ? (dailyPnl >= 0 ? "+" : "") +
                dailyPnl.toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })
              : "—"}
          </p>
          <p className="mt-1 text-xs text-slate-400">Ganancia/pérdida diaria</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Margen Disponible
          </p>
          <p className="mt-1 font-mono text-lg font-semibold text-white">
            $
            {typeof margin === "number"
              ? margin.toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })
              : "—"}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Margen disponible para trades
          </p>
        </div>
      </div>

      {balanceError && (
        <p className="mt-3 text-xs text-amber-300">
          Error de balance: {balanceError}
        </p>
      )}

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Última Decisión
          </p>
          <p className="mt-1 font-mono text-sm text-white">
            {last ? last.action : "—"}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            {last ? last.ticker : ""}
          </p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Conteo (ventana API)
          </p>
          <p className="mt-1 text-sm text-slate-200">
            BUY <span className="text-emerald-400">{buys}</span> · SELL{" "}
            <span className="text-rose-400">{sells}</span> · HOLD{" "}
            <span className="text-amber-300">{holds}</span>
          </p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Modo</p>
          <p className="mt-1 text-sm text-slate-200 capitalize">{mode}</p>
          <p className="mt-1 text-xs text-slate-400">Configuración actual</p>
        </div>
      </div>
    </section>
  );
}
