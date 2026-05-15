/** @param {string} path */
export function apiUrl(path) {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  if (base) return `${base}${path}`;
  return path;
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
