// Build-time configuration guard only; never uploads files or checks a live account.
import { pathToFileURL } from 'node:url'
import { isIP } from 'node:net'
export function validateApiBase(value) {
  if (!value) throw new Error('Set VITE_API_BASE_URL to an approved HTTPS backend origin.')
  const url = new URL(value)
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || !['','/'].includes(url.pathname)) throw new Error('API base must be an HTTPS origin without credentials, path, query or fragment.')
  if (isIP(url.hostname.replace(/^\[|\]$/g,'')) || !url.hostname.includes('.') || url.hostname.includes('_') || /your[_-]/i.test(value) || ['localhost','127.0.0.1','[::1]','0.0.0.0'].includes(url.hostname) || /\.(local|localhost|internal|invalid|example|test)$/.test(url.hostname) || /(^|\.)example\.(com|net|org)$/.test(url.hostname)) throw new Error('Local, literal-IP or placeholder backend origins cannot serve a public deployment.')
  return url.origin
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    validateApiBase(process.env.VITE_API_BASE_URL)
    console.log('API origin format valid. Hosting permissions, availability and CORS still require review.')
  } catch (error) {
    console.error(error.message)
    process.exitCode = 1
  }
}
