import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development, /api is proxied to the backend so the app works the same
// as in Docker (where nginx does the proxying).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': process.env.VITE_PROXY_TARGET || 'http://localhost:8000' },
  },
})
