import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// Change VITE_PROXY_TARGET in .env to switch between the mock (4010) and the real backend (8000).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const target = env.VITE_PROXY_TARGET || 'http://localhost:4010';
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': { target, changeOrigin: true },
        '/ws': { target, changeOrigin: true, ws: true },
      },
    },
  };
});
