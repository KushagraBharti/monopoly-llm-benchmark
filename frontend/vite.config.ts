import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
const currentDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(currentDir, '..')
const contractsPath = path.resolve(repoRoot, 'contracts', 'ts')
const contractsDataPath = path.resolve(repoRoot, 'contracts', 'data')
const srcPath = path.resolve(currentDir, 'src')

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': srcPath,
      '@contracts': contractsPath,
      '@contracts-data': contractsDataPath,
    },
  },
  server: {
    fs: {
      allow: [repoRoot],
    },
  },
})
