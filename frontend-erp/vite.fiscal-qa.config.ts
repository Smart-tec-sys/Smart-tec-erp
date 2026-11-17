import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    outDir: 'dist-fiscal-qa',
    emptyOutDir: true,
    rollupOptions: {
      input: { qa: resolve(__dirname, 'qa-fiscal.html') },
    },
  },
})
