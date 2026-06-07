/** @param {string} path */
export function apiUrl(path) {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  if (base) return `${base}${path}`;
  const loc = window.location;
  const host = loc.hostname === "localhost" ? "localhost:8000" : loc.host;
  return `${loc.protocol}//${host}${path}`;
}

export function wsUrl() {
  const base = import.meta.env.VITE_API_URL;
  if (base) {
    const u = new URL(base.replace(/\/$/, ""));
    const wsProto = u.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProto}//${u.host}/ws`;
  }
  const loc = window.location;
  const proto = loc.protocol === "https:" ? "wss" : "ws";
  const host = loc.hostname === "localhost" ? "localhost:8000" : loc.host;
  return `${proto}://${host}/ws`;
}

export async function getConfig() {
  const res = await fetch(apiUrl("/config"));
  if (!res.ok) throw new Error("Failed to fetch config");
  return res.json();
}

export async function updateConfig(config) {
  const res = await fetch(apiUrl("/config"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error("Failed to update config");
  return res.json();
}

export async function getPosition() {
  const res = await fetch(apiUrl("/position"));
  if (!res.ok) throw new Error("Failed to fetch position");
  return res.json();
}

export async function getAgentStatus() {
  const res = await fetch(apiUrl("/status"));
  if (!res.ok) throw new Error("Failed to fetch agent status");
  return res.json();
}

export async function getTrades() {
  const res = await fetch(apiUrl("/trades"));
  if (!res.ok) throw new Error("Failed to fetch trades");
  return res.json();
}

export async function emergencyClose() {
  const res = await fetch(apiUrl("/emergency-close"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to execute emergency close");
  return res.json();
}
