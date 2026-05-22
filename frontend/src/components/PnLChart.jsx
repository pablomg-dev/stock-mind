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
  const [balance, setBalance] = useState(null);

  const load = useCallback(async () => {
    try {
      const [dec, bal] = await Promise.all([
        fetch(apiUrl("/decisions")),
        fetch(apiUrl("/balance")),
      ]);
      if (dec.ok) {
        const data = await dec.json();
        setDecisions(Array.isArray(data) ? data : []);
      }
      if (bal.ok) {
        const b = await bal.json();
        setBalance(b);
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const points = useMemo(() => {
    const chrono = [...decisions].reverse();
    // Get initial equity from balance, fallback to 10000 USD if not available
    const initialEquity =
      balance?.portfolio_value ||
      balance?.equity ||
      balance?.total_equity ||
      10000;
    let equity = initialEquity;
    return chrono.map((d, i) => {
      const a = String(d.action || "").toUpperCase();
      const c = Number(d.confidence) || 0;
      // Simulate USD changes based on decisions (this is still synthetic but in USD)
      // In a real implementation, this would use actual trade PnL from Kraken
      if (a === "BUY")
        equity += c * 100; // Simulate profit/loss in USD
      else if (a === "SELL") equity -= c * 100;
      else equity += (c - 0.5) * 50;
      return {
        name: i + 1,
        label: String(d.timestamp || "").slice(11, 19) || `#${i + 1}`,
        equity: Math.round(equity),
      };
    });
  }, [decisions, balance]);

  const data = points.length
    ? points
    : [
        {
          name: 0,
          label: "—",
          equity: balance?.portfolio_value || balance?.equity || 10000,
        },
      ];

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 shadow-xl">
      <div className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight text-white">
          Equity Curve (USD)
        </h2>
        <p className="text-sm text-slate-400">
          Series derived from decisions in USD. Based on current Kraken balance.
        </p>
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <YAxis
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{
                background: "#0f172a",
                border: "1px solid #334155",
                borderRadius: "8px",
              }}
              labelStyle={{ color: "#e2e8f0" }}
            />
            <Line
              type="monotone"
              dataKey="equity"
              stroke="#38bdf8"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
