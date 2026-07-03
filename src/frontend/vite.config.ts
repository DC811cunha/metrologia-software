import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://backend:3001',
        changeOrigin: true,
      },
    },
    // Bind mounts do Docker em hosts Windows não propagam eventos inotify de forma
    // confiável; sem polling, o HMR para de detectar alterações em src/ silenciosamente.
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
});
