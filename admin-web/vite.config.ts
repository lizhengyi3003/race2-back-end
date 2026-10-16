import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  // 相对路径：使构建产物可挂载在任意子路径（如 /admin）下
  base: './',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    host: '0.0.0.0',
    // ⚠️ 与旧项目 race 的 5173 隔离，本环境（race3）改用 5176
    port: 5176,
    proxy: {
      '/api': {
        // race3 Docker 后端主机端口为 18001（8001 被 Windows 系统保留无法绑定）
        target: process.env.VITE_DEV_PROXY || 'http://localhost:18001',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
