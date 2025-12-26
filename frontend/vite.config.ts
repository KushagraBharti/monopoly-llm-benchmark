import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
const currentDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(currentDir, '..')
const contractsPath = path.resolve(repoRoot, 'contracts', 'ts')

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@contracts': contractsPath,
    },
  },
  server: {
    fs: {
      allow: [repoRoot],
    },
  },
})
