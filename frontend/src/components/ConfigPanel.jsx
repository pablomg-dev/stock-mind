import { useState, useEffect } from "react";
import { getConfig, updateConfig } from "../api.js";

export default function ConfigPanel() {
  const [leverage, setLeverage] = useState(5);
  const [maxPositionPct, setMaxPositionPct] = useState(10);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState("");

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const config = await getConfig();
      setLeverage(config.leverage || 5);
      setMaxPositionPct(config.max_position_pct || 10);
    } catch (error) {
      console.error("Failed to load config:", error);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus("");
    try {
      await updateConfig({ leverage, max_position_pct: maxPositionPct });
      setSaveStatus("Configuración guardada");
      setTimeout(() => setSaveStatus(""), 2000);
    } catch (error) {
      console.error("Failed to save config:", error);
      setSaveStatus("Error al guardar");
      setTimeout(() => setSaveStatus(""), 2000);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Configuración</h2>
        {saveStatus && (
          <span className={`text-sm ${saveStatus.includes("Error") ? "text-red-400" : "text-green-400"}`}>
            {saveStatus}
          </span>
        )}
      </div>

      <div className="space-y-6">
        {/* Leverage Slider */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-sm font-medium text-slate-300">Leverage</label>
            <span className="text-lg font-bold text-white">{leverage}x</span>
          </div>
          <input
            type="range"
            min="1"
            max="10"
            step="1"
            value={leverage}
            onChange={(e) => setLeverage(parseInt(e.target.value))}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <div className="mt-1 flex justify-between text-xs text-slate-500">
            <span>1x</span>
            <span>10x</span>
          </div>
        </div>

        {/* Max Position Percentage Slider */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-sm font-medium text-slate-300">Max Position</label>
            <span className="text-lg font-bold text-white">{maxPositionPct}%</span>
          </div>
          <input
            type="range"
            min="1"
            max="25"
            step="0.5"
            value={maxPositionPct}
            onChange={(e) => setMaxPositionPct(parseFloat(e.target.value))}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <div className="mt-1 flex justify-between text-xs text-slate-500">
            <span>1%</span>
            <span>25%</span>
          </div>
        </div>

        {/* Save Button */}
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? "Guardando..." : "Guardar Configuración"}
        </button>
      </div>
    </div>
  );
}
