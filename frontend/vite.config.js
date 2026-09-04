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
  // `vite preview` (serving the production build) needs the same Host-header allowance and port
  // as the dev server above, since it's the same named Cloudflare Tunnel forwarding to it - the
  // preview server has its own separate config block, it doesn't inherit `server`'s.
  preview: {
    port: 5173,
    allowedHosts: true,
  },
  test: {
    // jsdom, not the default node environment - these are component tests that need a DOM.
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    // Only our own specs. Without this, vitest also walks node_modules and the built dist/.
    include: ['src/**/*.test.{js,jsx}'],
  },
})
