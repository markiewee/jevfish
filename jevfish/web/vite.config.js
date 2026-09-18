import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: '/',
  plugins: [vue()],
  // Built app ships INSIDE the package so the wheel carries it. See src/jevfish/assets.py.
  build: { outDir: '../src/jevfish/web_dist', emptyOutDir: true },
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:5055', changeOrigin: true } },
  },
})
