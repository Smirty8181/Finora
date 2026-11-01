import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backend = process.env.VITE_BACKEND_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/ws': { target: backend.replace(/^http/, 'ws'), ws: true, changeOrigin: true },
    },
  },
})
