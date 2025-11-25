import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],





  server: {
    host: "0.0.0.0",
    port: 5000,
    proxy: (() => {
      const target = process.env.API_TARGET || 'http://10.0.1.194:8001'
      return {
        '/api': {
          target,
          changeOrigin: true,
          secure: false,
        },
        '/media': {
          target,
          changeOrigin: true,
          secure: false,
        },
      }
    })(),
  },
})
