import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Vite rejects requests whose Host header it doesn't recognize (DNS-rebinding
    // protection) - a cloudflared quick tunnel forwards the real trycloudflare.com
    // Host header through, which fails that check without this.
    allowedHosts: true,
  },
})
