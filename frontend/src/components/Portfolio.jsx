import { useCallback, useEffect, useState } from "react";
import { apiUrl } from "../api.js";

export default function Portfolio() {
  const [mode, setMode] = useState("paper");
  const [decisions, setDecisions] = useState([]);
  const [error, setError] = useState(null);

  const poll = useCallback(async () => {
    try {
      const [cfg, dec] = await Promise.all([
        fetch(apiUrl("/config")),
        fetch(apiUrl("/decisions")),
      ]);
      if (cfg.ok) {
        const j = await cfg.json();
        if (j?.mode) setMode(String(j.mode).toLowerCase());
      }
      if (dec.ok) {
        const list = await dec.json();
        setDecisions(Array.isArray(list) ? list : []);
      }
      setError(null);
    } catch (e) {
      setError(e?.message || "Error de red");
    }
  }, []);

  useEffect(() => {
    poll();
    const id = setInterval(poll, 30_000);
    return () => clearInterval(id);
  }, [poll]);

  const last = decisions[0];
  const buys = decisions.filter((d) => String(d.action).toUpperCase() === "BUY").length;
  const sells = decisions.filter((d) => String(d.action).toUpperCase() === "SELL").length;
  const holds = decisions.filter((d) => String(d.action).toUpperCase() === "HOLD").length;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 shadow-xl">
      <div className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight text-white">Portfolio (resumen)</h2>
        <p className="text-sm text-slate-400">Polling cada 30s. Balance en vivo requiere endpoint dedicado.</p>
      </div>

      {error && (
        <p className="mb-3 text-sm text-rose-300">{error}</p>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Ultima decision</p>
          <p className="mt-1 font-mono text-sm text-white">{last ? last.action : "—"}</p>
          <p className="mt-1 text-xs text-slate-400">{last ? last.ticker : ""}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Conteo (ventana API)</p>
          <p className="mt-1 text-sm text-slate-200">
            BUY <span className="text-emerald-400">{buys}</span> · SELL{" "}
            <span className="text-rose-400">{sells}</span> · HOLD{" "}
            <span className="text-amber-300">{holds}</span>
          </p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">PnL (placeholder)</p>
          <p className="mt-1 text-lg font-semibold text-slate-500">—</p>
          <p className="text-xs text-slate-500">Conecta Kraken paper + endpoint de balance para valores reales.</p>
        </div>
      </div>

      <p className="mt-3 text-xs text-slate-500">Modo servidor: {mode}</p>
    </section>
  );
}
