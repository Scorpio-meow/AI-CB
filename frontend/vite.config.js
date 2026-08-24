import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import viteCompression from 'vite-plugin-compression';
import path from 'path';
import { fileURLToPath } from 'url';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '');
  return {
    plugins: [
      react(),
      viteCompression({
        apply: 'build',
      }),
    ],
    server: {
      port: parseInt(env.PORT) || 3000,
      host: true,
      open: false,
      proxy: {
        '/api': {
          target: env.VITE_API_BASE || 'http://127.0.0.1:8001',
          changeOrigin: true,
          secure: false,
          ws: true,
        },
      },
    },
    preview: {
      port: 3000,
      host: true,
    },
    build: {
      outDir: 'build',
      sourcemap: env.GENERATE_SOURCEMAP !== 'false',
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('@mui') || id.includes('@emotion')) {
                return 'mui';
              }
              if (id.includes('react') || id.includes('react-dom') || id.includes('react-router-dom')) {
                return 'vendor';
              }
            }
          },
        },
      },
      chunkSizeWarningLimit: 1000,
    },
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
    define: {
      'process.env.NODE_ENV': JSON.stringify(mode),
    },
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        '@mui/material',
        '@mui/material/styles',
        '@emotion/react',
        '@emotion/styled',
        'axios'
      ],
    },
  };
});