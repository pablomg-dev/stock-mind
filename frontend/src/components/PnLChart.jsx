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
import { apiUrl, getTrades } from "../api.js";

export default function PnLChart() {
  const [trades, setTrades] = useState([]);
  const [balance, setBalance] = useState(null);

  const load = useCallback(async () => {
    try {
      const [tradesData, bal] = await Promise.all([
        getTrades(),
        fetch(apiUrl("/balance")),
      ]);
      setTrades(Array.isArray(tradesData) ? tradesData : []);
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
    if (!trades.length) {
      return [
        {
          name: 0,
          label: "—",
          equity: balance?.portfolio_value || balance?.equity || 10000,
        },
      ];
    }

    const chrono = [...trades].reverse();
    const initialEquity =
      balance?.portfolio_value || balance?.equity || balance?.total_equity || 10000;
    let equity = initialEquity;
    let totalPnl = 0;

    return chrono.map((t, i) => {
      const a = String(t.action || "").toUpperCase();
      const price = Number(t.price) || 0;
      const volume = Number(t.volume) || 0;
      
      // Simple P&L estimation: for SELL, assume profit is (current_price - entry_price) * volume
      // We don't have exact fills, so we estimate based on trade direction
      if (a === "SELL" && i > 0) {
        const prevTrade = chrono[i - 1];
        if (prevTrade && String(prevTrade.action).toUpperCase() === "BUY") {
          const entryPrice = Number(prevTrade.price) || price;
          const pnl = (price - entryPrice) * volume;
          totalPnl += pnl;
        }
      }
      
      equity = initialEquity + totalPnl;
      
      return {
        name: i + 1,
        label: String(t.timestamp || "").slice(11, 19) || `#${i + 1}`,
        equity: Math.round(equity * 100) / 100,
      };
    });
  }, [trades, balance]);

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 shadow-xl">
      <div className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight text-white">
          Equity Curve (USD)
        </h2>
        <p className="text-sm text-slate-400">
          Based on actual trade history from database.
        </p>
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={points}
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
