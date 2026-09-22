// vite.config.js
// ---------------
// Vite is the build tool/dev server for the React frontend. It's used
// (instead of Create React App) because it's the current open-source
// standard: near-instant dev server start and hot-reload, and small,
// optimized production bundles.

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls to the backend during local development so the
    // frontend can simply call "/api/..." without worrying about CORS
    // or hard-coding a backend port.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
