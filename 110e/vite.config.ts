import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3002,
    host: '0.0.0.0', // 允许局域网访问
    proxy: {
      '/api': {
        // 代理到本地后端服务
        // 如果需要代理到其他机器，修改 target 为对应的地址
        // 例如：target: 'http://192.168.1.100:8080'
        target: 'http://localhost:8000',
        changeOrigin: true,
        // 后端没有 /api 前缀，转发时需要去掉 /api
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
