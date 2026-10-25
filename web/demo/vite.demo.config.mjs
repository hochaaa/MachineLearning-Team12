// Local-only launch overlay: same plugins/source/design; explicit loopback proxy.
import base from '../frontend/vite.config.ts'
import { fileURLToPath } from 'node:url'
export default {
  ...base,
  root: fileURLToPath(new URL('../frontend', import.meta.url)),
  cacheDir: fileURLToPath(new URL(`.state/vite-${process.env.SCENT_DEMO_FRONT_PORT || '5173'}`,import.meta.url)),
  server: {...base.server, host:'127.0.0.1', strictPort:true,
    port:Number(process.env.SCENT_DEMO_FRONT_PORT || '5173'),
    proxy:{'/api':`http://127.0.0.1:${process.env.SCENT_DEMO_BACK_PORT || '8000'}`}}
}
