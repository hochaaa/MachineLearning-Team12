// Team12 demo UI; visual flow inspired by our existing web/frontend/src/main.tsx.
// No original data, images, aliases or runtime assets are included.
import React, {useEffect, useState} from 'react'
import {createRoot} from 'react-dom/client'
import './style.css'
type Perfume = {id: string; brand: string; name: string; notes: string[]; accords: string[]; description: string; top_notes: string[]; middle_notes: string[]; base_notes: string[]}
type Selection = Perfume & {rating: number}
type Result = Perfume & {rank: number; score: number; shared_tokens: string[]}
type Response = {mode: string; data_origin: string; engine: string; results: Result[]; eligible_count: number; unseen_count: number; notice: string}
const API = (import.meta.env.VITE_DEMO_API_URL || 'http://127.0.0.1:8002').replace(/\/$/, '')
const rules = [{key: 'woody', label: 'Woody', desc: '나무 계열 어코드'}, {key: 'floral', label: 'Floral', desc: '꽃 계열 어코드'}, {key: 'rose', label: 'Rose', desc: '장미 노트'}]
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(API + path, {...init, signal: init.signal ?? AbortSignal.timeout(15000)}).catch(() => {throw new Error('데모 서버에 연결할 수 없습니다. 백엔드 실행 상태와 API 주소를 확인하세요.')})
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : '데모 API 오류입니다. 서버와 입력을 확인하세요.')
  }
  return response.json()
}
function App() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('name')
  const [hits, setHits] = useState<Perfume[]>([])
  const [selected, setSelected] = useState<Selection[]>([])
  const [filters, setFilters] = useState<string[]>([])
  const [results, setResults] = useState<Response | null>(null)
  const [detail, setDetail] = useState<Perfume | null>(null)
  const [busy, setBusy] = useState(false)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState('')
  const [searchError, setSearchError] = useState('')
  const [ready, setReady] = useState(false)
  const [status, setStatus] = useState('데모 서버 확인 중')
  useEffect(() => {
    request<{mode: string; data_origin: string; recommendation_ready: boolean; candidate_count: number}>('/api/health')
      .then(h => {if (h.mode !== 'demo' || h.data_origin !== 'synthetic' || !h.recommendation_ready) throw new Error('합성 데모 서버가 아닙니다. 실행 모드를 확인하세요.'); setReady(true); setStatus(`${h.candidate_count} fictional perfumes · ready`)})
      .catch(e => {setStatus('데모 서버 연결 필요'); setError(e instanceof Error ? e.message : '연결 실패')})
  }, [])
  useEffect(() => {
    const controller = new AbortController(); setSearching(true); setSearchError('')
    const timer = setTimeout(() => {
      request<{results: Perfume[]}>('/api/perfumes?q=' + encodeURIComponent(query.trim()) + '&mode=' + mode, {signal: controller.signal})
        .then(data => {if (!controller.signal.aborted) setHits(data.results)})
        .catch(e => {if (!controller.signal.aborted) {setHits([]); setSearchError(e instanceof Error ? e.message : '검색 연결 실패')}})
        .finally(() => {if (!controller.signal.aborted) setSearching(false)})
    }, 180)
    return () => {clearTimeout(timer); controller.abort()}
  }, [query, mode])
  function changed() {setResults(null); setError('')}
  async function recommend() {
    setBusy(true); setError('')
    try {
      const data = await request<Response>('/api/recommend', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ratings:selected.map(p => ({perfume_id:p.id, rating:p.rating})), required_scents:filters, top_k:5})})
      if (data.mode !== 'demo' || data.data_origin !== 'synthetic' || data.engine !== 'content_tfidf_cosine') throw new Error('추천 응답의 Demo 모드가 일치하지 않습니다.')
      setResults(data)
    } catch (e) {setResults(null); setError(e instanceof Error ? e.message : '연결 실패')}
    finally {setBusy(false)}
  }
  async function showDetail(id: string) {
    try {setDetail(await request<Perfume>('/api/perfumes/' + encodeURIComponent(id)))}
    catch (e) {setError(e instanceof Error ? e.message : '상세 정보 오류')}
  }
  return <>
    <div className="demo-banner"><strong>DEMO MODE — Synthetic Data</strong><span>가상 향수 · 콘텐츠 기반 추천 알고리즘 · Frozen V1 Hybrid 모델을 실행하지 않습니다.</span></div>
    <header><a className="wordmark" href="#">SCENT MATCH<small>TEAM 12 / SYNTHETIC LAB</small></a><span className={ready ? 'status ready' : 'status'}>{status}</span></header>
    <main>
      <section className="hero"><div><p className="eyebrow">A FICTIONAL WORLD. YOUR REAL CHOICES.</p><h1>Your taste.<br/>An imagined <em>signature.</em></h1><p className="lead">존재하지 않는 향수로, 추천의 원리를 경험하세요.<br/>세 가지 향과 평점을 고르면 실제 계산으로 다음 향을 찾습니다.</p><a className="primary" href="#preferences">Explore the collection ↗</a><p className="fine">TF-IDF · CENTERED PREFERENCES · COSINE SIMILARITY</p></div><div className="hero-art" aria-hidden="true"><div className="bottle"><div className="cap"/><div className="glass"><span>SCENT<br/>MATCH<small>IMAGINARY ATELIER<br/>NOT A REAL PRODUCT</small></span></div></div><span className="art-caption">A STUDY IN PERSONAL PREFERENCE</span></div></section>
      <div className="divider"><span>80 FICTIONAL PERFUMES / 10 SCENT FAMILIES</span><span>NO REAL USER RATINGS</span></div>
      <section id="preferences"><div className="section-heading"><div><p className="eyebrow">01 / YOUR SCENT WARDROBE</p><h2>Choose three.<br/><em>Make them yours.</em></h2></div><p>0점은 비선호, 5점은 중립, 10점은 선호입니다.<br/>낮은 평점은 비선호 신호로 반영합니다.</p></div>
        <div className="workspace"><div className="panel"><label htmlFor="search">SEARCH THE FICTIONAL COLLECTION</label><div className="search-controls"><select aria-label="검색 모드" value={mode} onChange={e => setMode(e.target.value)}><option value="name">이름 / 브랜드</option><option value="notes">향 노트 / 계열</option></select><input id="search" maxLength={100} placeholder={mode === 'name' ? 'Invented Citrus, DEMO-001…' : 'rose, woody, vanilla…'} value={query} onChange={e => setQuery(e.target.value)}/></div><p className="fine">가상 브랜드·제품만 검색됩니다. 실제 브랜드 alias는 포함하지 않습니다.</p>
          {searching && <p role="status">검색 중…</p>}{searchError && <p className="error" role="alert">{searchError}</p>}{!searching && !searchError && !hits.length && <p>검색 결과가 없습니다. 가상 이름 또는 일반 영어 노트를 입력하세요.</p>}
          <div className="hit-list">{hits.map(p => <div className="hit" key={p.id}><div><small>{p.brand} · {p.id}</small><h3>{p.name}</h3><p>{p.accords.join(' · ')}</p><button className="text-button" onClick={() => showDetail(p.id)}>상세 정보</button></div><button className="add" aria-label={`${p.id} 추가`} disabled={busy || selected.length >= 3 || selected.some(s => s.id === p.id)} onClick={() => {setSelected(v => [...v, {...p, rating:7}]); changed()}}>{selected.some(s => s.id === p.id) ? '선택됨' : '+ 추가'}</button></div>)}</div>
        </div><div className="panel wardrobe"><div className="wardrobe-title"><label>YOUR THREE CHOICES</label><strong>{selected.length} / 3</strong></div>{!selected.length && <div className="empty">＋<h3>취향을 담을 공간</h3><p>왼쪽에서 가상 향수를 선택하세요.</p></div>}{selected.map(p => <div className="selection" key={p.id}><div className="selection-heading"><div><small>{p.id}</small><h3>{p.name}</h3></div><button aria-label={`${p.id} 삭제`} disabled={busy} onClick={() => {setSelected(v => v.filter(s => s.id !== p.id)); changed()}}>×</button></div><label htmlFor={'rating-'+p.id}>{p.id} 평점 <output>{p.rating} / 10</output></label><input id={'rating-'+p.id} aria-label={`${p.id} 평점`} type="range" min={0} max={10} step={0.5} disabled={busy} value={p.rating} onChange={e => {setSelected(v => v.map(s => s.id === p.id ? {...s,rating:Number(e.target.value)} : s)); changed()}}/></div>)}<p className="fine">데모 UI는 3개를 선택합니다. 평점은 저장하지 않습니다.</p></div></div>
      </section>
      <section><div className="section-heading"><div><p className="eyebrow">02 / KNOWLEDGE-BASED RULES</p><h2>A direction,<br/><em>if you wish.</em></h2></div><p>선택한 조건을 모두 만족하는 향수만 추천합니다.<br/>아무것도 선택하지 않으면 필터를 적용하지 않습니다.</p></div><fieldset disabled={busy} className="filters"><legend className="sr-only">향 조건 조합</legend>{rules.map(r => <label className={filters.includes(r.key) ? 'filter active' : 'filter'} key={r.key}><input type="checkbox" checked={filters.includes(r.key)} onChange={() => {setFilters(v => v.includes(r.key) ? v.filter(s => s !== r.key) : [...v,r.key]); changed()}}/><strong>{r.label}</strong><span>{r.desc}</span></label>)}</fieldset><div className="action"><p>{selected.length === 3 ? '선택한 평점으로 콘텐츠 선호도 프로필을 계산합니다.' : '가상 향수 3개를 선택해 주세요.'}</p><button className="primary" disabled={!ready || selected.length !== 3 || busy} onClick={recommend}>{busy ? '계산 중…' : 'Discover my matches ↗'}</button></div>{error && <p className="error" role="alert">{error}</p>}</section>
      <section aria-live="polite"><div className="section-heading"><div><p className="eyebrow">03 / YOUR RECOMMENDATIONS</p><h2>Your next <em>five.</em></h2></div><p>실제 계산한 콘텐츠 유사도입니다.<br/>점수는 확률이나 기존 모델의 성능이 아닙니다.</p></div>{results === null ? <div className="empty result-placeholder">YOUR NEXT IMAGINARY SCENT STARTS HERE</div> : <><p className="notice" role="status">{results.unseen_count}개 입력 제외 후보 → 필터 후 {results.eligible_count}개. {results.notice}</p>{results.results.length === 0 && <p>모든 조건을 만족하는 향수가 없습니다. 필터를 줄여 주세요.</p>}<div className="result-grid">{results.results.map(r => <article className="result-card" key={r.id}><div className="card-top"><span>Nº {r.rank}</span><span>CONTENT MATCH</span></div><small>{r.brand} · {r.id}</small><h3>{r.name}</h3><div className="tags">{r.accords.map(a => <span key={a}>{a}</span>)}</div><p>{r.description}</p><p className="fine">공통 특성: {r.shared_tokens.join(' · ') || '없음'}</p><div className="score"><span>Cosine score</span><strong>{r.score.toFixed(4)}</strong></div><button className="text-button" onClick={() => showDetail(r.id)}>상세 정보</button></article>)}</div></>}</section>
    </main><footer>SCENT MATCH / TEAM 12 · SYNTHETIC ALGORITHM DEMONSTRATION<br/>No MF, no Hybrid model, no real perfume records or research performance claims.</footer>
    {detail && <div className="modal-backdrop"><section role="dialog" aria-modal="true" aria-label="향수 상세 정보" className="modal"><button className="close" aria-label="상세 닫기" onClick={() => setDetail(null)}>닫기 ×</button><p className="eyebrow">FICTIONAL PERFUME / {detail.id}</p><h2>{detail.name}</h2><p>{detail.brand}</p><p>{detail.description}</p><dl><dt>Top notes</dt><dd>{detail.top_notes.join(', ')}</dd><dt>Middle notes</dt><dd>{detail.middle_notes.join(', ')}</dd><dt>Base notes</dt><dd>{detail.base_notes.join(', ')}</dd><dt>Accords</dt><dd>{detail.accords.join(', ')}</dd></dl></section></div>}
  </>
}
createRoot(document.getElementById('root')!).render(<App/>)
