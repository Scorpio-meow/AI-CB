import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react-swc';
import viteCompression from 'vite-plugin-compression';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // 載入環境變數
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    plugins: [
      react(),
      viteCompression({
        apply: 'build',
      }),
    ],
    
    // 開發伺服器配置
    server: {
      port: parseInt(env.PORT) || 3000,
      host: true,
      open: false,
      
      // API 代理配置 - 將 /api 請求轉發到後端
      proxy: {
        '/api': {
          target: env.VITE_API_BASE || 'http://127.0.0.1:8001',
          changeOrigin: true,
          secure: false,
          ws: true, // 支援 WebSocket
        },
      },
    },
    
    // 預覽伺服器配置
    preview: {
      port: 3000,
      host: true,
    },
    
    // 建構配置
    build: {
      outDir: 'build',
      sourcemap: env.GENERATE_SOURCEMAP !== 'false',
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom', 'react-router-dom'],
            mui: ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
          },
        },
      },
      // 優化設定
      chunkSizeWarningLimit: 1000,
    },
    
    // 路徑別名
    resolve: {
      extensions: ['.mjs', '.js', '.jsx', '.ts', '.tsx', '.json'],
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@components': path.resolve(__dirname, './src/components'),
        '@pages': path.resolve(__dirname, './src/pages'),
        '@services': path.resolve(__dirname, './src/services'),
        '@utils': path.resolve(__dirname, './src/utils'),
        '@contexts': path.resolve(__dirname, './src/contexts'),
      },
    },
    
    // 定義全局常量
    define: {
      // 為了兼容某些使用 process.env 的庫
      'process.env.NODE_ENV': JSON.stringify(mode),
    },
    
    // 優化配置
    optimizeDeps: {
      include: ['react', 'react-dom', 'react-router-dom', '@mui/material', 'axios'],
    },
    
    // ESBuild 配置
    esbuild: {
      jsxInject: undefined,
    },
  };
});
