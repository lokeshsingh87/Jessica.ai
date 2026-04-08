import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
  // 🚩 ADD THIS: Ensures assets are linked relatively (./assets/...) 
  // instead of absolutely (/assets/...)
  base: './', 
  
  plugins: [react(), tailwindcss()],
  
  server: {
    proxy: {
      '/audit': {
        target: 'http://127.0.0.1:7860',
        changeOrigin: true,
      },
      '/developer': {
        target: 'http://127.0.0.1:7860',
        changeOrigin: true,
      },
      '/stats': {
        target: 'http://127.0.0.1:7860',
        changeOrigin: true,
      },
      '/export': { // 🚩 Add this if you missed it for PDF exports
        target: 'http://127.0.0.1:7860',
        changeOrigin: true,
      },
      '/data': { // 🚩 Add this for session detail loading
        target: 'http://127.0.0.1:7860',
        changeOrigin: true,
      }
    }
  }
})