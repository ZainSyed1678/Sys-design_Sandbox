import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const port = parseInt(process.env.VITE_PORT || process.env.FRONTEND_PORT || '3001', 10)

export default defineConfig({
  plugins: [react()],
  server: {
    port: port,
    host: true,
    watch: {
      usePolling: true
    }
  }
})
