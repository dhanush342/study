import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:7860'
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'terser',
    target: 'es2020',
    cssMinify: true,
    // Aggressive code splitting for parallel loading
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React — cached long-term
          'vendor-react': ['react', 'react-dom'],
          // Map library — large, separate chunk
          'vendor-map': ['maplibre-gl', 'react-map-gl'],
          // Charts — loaded only when analytics opened
          'vendor-charts': ['recharts'],
          // Search — small utility
          'vendor-search': ['fuse.js'],
        },
        // Content-hash filenames for cache busting
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      }
    },
    terserOptions: {
      compress: {
        drop_console: true,  // Remove console.log in prod
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.debug'],
      },
    },
    // Chunk size warning threshold
    chunkSizeWarningLimit: 600,
  },
  // Dependency optimization
  optimizeDeps: {
    include: ['react', 'react-dom', 'maplibre-gl', 'react-map-gl', 'fuse.js'],
  },
})
