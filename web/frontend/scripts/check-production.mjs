// Build-time configuration guard only; never uploads files or checks a live account.
import { pathToFileURL } from 'node:url'
import { isIP } from 'node:net'
export function validateApiBase(value) {
  // Empty means same-origin /api, used by the combined Vercel deployment.
  if (!value) return ''
  const url = new URL(value)
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || !['','/'].includes(url.pathname)) throw new Error('API base must be an HTTPS origin without credentials, path, query or fragment.')
  if (isIP(url.hostname.replace(/^\[|\]$/g,'')) || !url.hostname.includes('.') || url.hostname.includes('_') || /your[_-]/i.test(value) || ['localhost','127.0.0.1','[::1]','0.0.0.0'].includes(url.hostname) || /\.(local|localhost|internal|invalid|example|test)$/.test(url.hostname) || /(^|\.)example\.(com|net|org)$/.test(url.hostname)) throw new Error('Local, literal-IP or placeholder backend origins cannot serve a public deployment.')
  return url.origin
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    validateApiBase(process.env.VITE_API_BASE_URL)
    console.log(process.env.VITE_API_BASE_URL ? 'HTTPS API origin format valid.' : 'Using same-origin /api.')
  } catch (error) {
    console.error(error.message)
    process.exitCode = 1
  }
}
