import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: resolve(__dirname, 'src/main.jsx'),
      output: {
        // 단일 파일로 출력
        format: 'iife',
        name: 'MapModule',
        entryFileNames: 'map-react.js',
        inlineDynamicImports: true
      }
    },
    outDir: resolve(__dirname, '../static/js'),
    emptyOutDir: false // 기존 파일 유지
  }
});
