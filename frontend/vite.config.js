import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const api = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/decisions": { target: api, changeOrigin: true },
      "/config": { target: api, changeOrigin: true },
      "/ws": { target: api, ws: true, changeOrigin: true },
    },
  },
});
