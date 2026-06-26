import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em dev, o frontend (5173) faz proxy de /api para o backend (8000).
// Em produção, o backend serve o build estático na mesma origem.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
