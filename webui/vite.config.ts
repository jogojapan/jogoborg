import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// Backend the Vite dev server proxies /api to. Same default as local_test
// (web server on 8080). Override with JOGOBORG_API_PROXY if your backend
// runs elsewhere.
const apiProxyTarget = process.env.JOGOBORG_API_PROXY || 'http://localhost:8080';

export default defineConfig({
  plugins: [svelte()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
});