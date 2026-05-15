import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiUrl } from "../api.js";

export default function PnLChart() {
  const [decisions, setDecisions] = useState([]);

  const load = useCallback(async () => {
    try {
      const r = await fetch(apiUrl("/decisions"));
      if (!r.ok) return;
      const data = await r.json();
      setDecisions(Array.isArray(data) ? data : []);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const points = useMemo(() => {
    const chrono = [...decisions].reverse();
    let equity = 100;
    return chrono.map((d, i) => {
      const a = String(d.action || "").toUpperCase();
      const c = Number(d.confidence) || 0;
      if (a === "BUY") equity += c * 2;
      else if (a === "SELL") equity -= c * 2;
      else equity += (c - 0.5) * 0.5;
      return {
        name: i + 1,
        label: String(d.timestamp || "").slice(11, 19) || `#${i + 1}`,
        equity: Math.round(equity * 10) / 10,
      };
    });
  }, [decisions]);

  const data = points.length ? points : [{ name: 0, label: "—", equity: 100 }];

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 shadow-xl">
      <div className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight text-white">Curva sintetica</h2>
        <p className="text-sm text-slate-400">
          Serie derivada de decisiones (demo). No es PnL real hasta integrar trades.
        </p>
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} domain={["auto", "auto"]} />
            <Tooltip
              contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: "8px" }}
              labelStyle={{ color: "#e2e8f0" }}
            />
            <Line type="monotone" dataKey="equity" stroke="#38bdf8" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
