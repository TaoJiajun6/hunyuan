import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://123.207.14.127:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://123.207.14.127:8000',
        changeOrigin: true,
      },
    },
  },
})

