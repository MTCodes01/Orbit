import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['orbit-icon.svg'],
      manifest: {
        name: 'Orbit Controller',
        short_name: 'Orbit',
        description: 'Universal multi-laptop remote control from your phone',
        theme_color: '#0d0d0f',
        background_color: '#0d0d0f',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          { src: '/orbit-icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/orbit-icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/orbit-icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^https?:\/\/.+\/api\//,
            handler: 'NetworkFirst',
            options: { cacheName: 'orbit-api-cache' },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true, changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    globals: true,
  },
})
