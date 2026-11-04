import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  define: { __APP_COMMIT__: JSON.stringify('test') },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.tsx'],
    setupFiles: ['src/test/setup.ts'],
  },
})
