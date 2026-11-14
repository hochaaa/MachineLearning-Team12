import test from 'node:test'
import assert from 'node:assert/strict'
import { validateApiBase } from './check-production.mjs'
import { readFileSync } from 'node:fs'
test('empty API origin uses the same-origin API',()=>assert.equal(validateApiBase(''),''))
test('HTTP and local/placeholder origins are rejected',()=>{
  for (const value of ['http://api.example.net','https://localhost','https://127.0.0.1','https://host.invalid','https://api.example.com','https://YOUR_BACKEND_DOMAIN','https://192.168.1.1','https://[::1]','https://2130706433','https://backend.internal']) assert.throws(()=>validateApiBase(value))
})
test('credentials and API paths/query are rejected',()=>{
  for (const value of ['https://u:p@api.example.net','https://api.example.net/api','https://api.example.net?q=x']) assert.throws(()=>validateApiBase(value))
})
test('HTTPS origin format is accepted without any network request',()=>assert.equal(validateApiBase('https://api.unit-check.dev/'),'https://api.unit-check.dev'))
test('SPA fallback excludes both bare and nested API routes',()=>{
  const config=JSON.parse(readFileSync(new URL('../vercel.json',import.meta.url),'utf8'))
  const pattern=new RegExp('^'+config.rewrites[0].source+'$')
  for (const path of ['/api','/api/health','/api/perfumes']) assert.equal(pattern.test(path),false)
  for (const path of ['/','/preferences','/preferences/detail']) assert.equal(pattern.test(path),true)
})
