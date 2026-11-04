import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Vercel exposes VERCEL_GIT_COMMIT_SHA at build time; shown in the footer
  // so you can confirm which commit is live.
  define: {
    __APP_COMMIT__: JSON.stringify((process.env.VERCEL_GIT_COMMIT_SHA || 'dev').slice(0, 7)),
  },
  build: {
    rollupOptions: {
      output: {
        // Separate, long-cacheable vendor chunks; app pages are lazy-loaded in App.tsx.
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          motion: ['motion'],
          icons: ['lucide-react'],
        },
      },
    },
  },
})
