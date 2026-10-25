import React, { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

type Perfume = { id: string; name: string; brand: string; accords: string[]; notes: string[]; matched_notes?: string[]; matched_accords?: string[] }
type Selection = Perfume & { rating: number }
type Result = Perfume & { rank: number; score: number; shared_tokens: string[] }
type Suggestion = { query: string; label: string; similarity: number | null }
type SearchMode = 'name' | 'notes'
type Scent = 'none' | 'woody' | 'floral' | 'rose'
const API = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const display = (value: string) => value.replaceAll('-', ' ')
const scentOptions: {key: Scent; label: string; desc: string}[] = [
  {key: 'none', label: 'Open to discovery', desc: '조건 없이 새로운 향을 만나보세요'},
  {key: 'woody', label: 'Woody', desc: '나무의 깊이와 차분한 잔향'},
  {key: 'floral', label: 'Floral', desc: '꽃의 결을 담은 향'},
  {key: 'rose', label: 'Rose', desc: '장미 노트가 있는 향'},
]
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API + path, {...init, signal: init?.signal ?? AbortSignal.timeout(20000)})
  if (!response.ok) throw new Error(response.status === 503 ? '모델이 준비되지 않았습니다. 백엔드 실행 상태를 확인해 주세요.' : response.status === 422 ? '입력값을 확인해 주세요. 평점은 0~10점이며 중복 향수는 허용되지 않습니다.' : 'API 요청을 완료하지 못했습니다. 백엔드 연결을 확인해 주세요.')
  return response.json()
}
function App() {
  const [selected, setSelected] = useState<Selection[]>([])
  const [query, setQuery] = useState('')
  const [searchMode, setSearchMode] = useState<SearchMode>('name')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [searchHint, setSearchHint] = useState('')
  const [hits, setHits] = useState<Perfume[]>([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [scent, setScent] = useState<Scent>('none')
  const [results, setResults] = useState<Result[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [ready, setReady] = useState<boolean | null>(null)
  const [stale, setStale] = useState(false)
  const resultRef = useRef<HTMLElement>(null)
  useEffect(() => {request<{recommendation_ready: boolean}>('/api/health').then(h => setReady(h.recommendation_ready)).catch(() => setReady(false))}, [])
  useEffect(() => {
    const controller = new AbortController()
    if (!query.trim()) {setHits([]); setSuggestions([]); setSearchHint(''); setSearching(false); setSearchError(''); return () => controller.abort()}
    setSearching(true); setSearchError(''); setHits([]); setSuggestions([]); setSearchHint('')
    const timer = setTimeout(() => {
      request<{results: Perfume[]; suggestions: Suggestion[]; hint?: string}>('/api/perfumes?mode=' + searchMode + '&q=' + encodeURIComponent(query.trim()), {signal: controller.signal})
        .then(data => {if (!controller.signal.aborted) {setHits(data.results); setSuggestions(data.suggestions ?? []); setSearchHint(data.hint ?? '')}})
        .catch(() => {if (!controller.signal.aborted) setSearchError('검색 서버에 연결할 수 없습니다. FastAPI 실행 상태를 확인해 주세요.')})
        .finally(() => {if (!controller.signal.aborted) setSearching(false)})
    }, 220)
    return () => {clearTimeout(timer); controller.abort()}
  }, [query, searchMode])
  function changed() {setStale(true); setError('')}
  async function recommend() {
    setBusy(true); setError('')
    try {
      const data = await request<{results: Result[]}>('/api/recommend', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ratings: selected.map(p => ({perfume_id: p.id, rating: p.rating})), required_scent: scent, top_k: 5})})
      setResults(data.results); setStale(false); setReady(true)
      setTimeout(() => resultRef.current?.scrollIntoView({behavior: 'smooth', block: 'start'}), 50)
    } catch (e) {setError(e instanceof Error ? e.message : '연결 오류가 발생했습니다.')}
    finally {setBusy(false)}
  }
  return <>
    <nav className="site-nav"><a href="#" className="wordmark">SCENT MATCH<span>TEAM 12 / PERFUME CURATION</span></a><a href="#preferences" className="nav-link">Discover your scent <span>↗</span></a></nav>
    <main>
      <section className="hero">
        <div className="hero-copy"><p className="eyebrow">A PERSONAL EXPLORATION OF SCENT</p><h1>Your taste.<br/>A new <em>signature.</em></h1><p className="hero-description">좋아하는 향수에서 시작하는, 다음 향의 발견.<br/>당신의 취향과 향의 특성이 만나는 다섯 가지 제안.</p><a className="primary-button" href="#preferences">Find your scent <span>↗</span></a><p className="hero-footnote">CONTENT + COLLABORATIVE · FROZEN HYBRID MODEL</p></div>
        <div className="hero-art" aria-hidden="true"><div className="orb orb-one"/><div className="orb orb-two"/><div className="bottle"><div className="bottle-cap"/><div className="bottle-neck"/><div className="bottle-body"><div className="bottle-label"><span>SCENT<br/>MATCH</span><small>YOUR NEXT SIGNATURE<br/>EAU DE CURIOSITÉ</small></div></div></div><span className="art-note">NOTES OF POSSIBILITY</span><span className="art-number">01 — 05</span></div>
      </section>
      <div className="editorial-strip"><span>BUILT AROUND YOUR TASTE</span><p>취향을 기록하고 <i>→</i> 향의 결을 고르고 <i>→</i> 새로운 향을 발견하세요</p><span>479 CURATED CANDIDATES</span></div>
      <section id="preferences" className="preferences section-shell">
        <div className="section-title"><div><p className="eyebrow">01 / YOUR PREFERENCES</p><h2>Start with what<br/>you <em>know.</em></h2></div><p>사용해 본 향수를 선택하고 평점을 남겨주세요.<br/>3개 이상이면 취향을 더 풍부하게 전달할 수 있어요.<br/><span>1~2개도 가능하며, 추천 품질은 제한될 수 있습니다.</span></p></div>
        {ready === false && <p className="notice" role="status">백엔드 연결 또는 모델 준비 상태를 확인해 주세요. 연결 복구 후 검색과 추천을 다시 시도할 수 있습니다.</p>}
        <div className="preference-grid"><div className="search-pane"><div className="search-mode" role="group" aria-label="검색 방식"><button type="button" aria-pressed={searchMode === 'name'} onClick={() => setSearchMode('name')}>향수명 / 브랜드</button><button type="button" aria-pressed={searchMode === 'notes'} onClick={() => setSearchMode('notes')}>향수 노트</button></div><label htmlFor="perfume-search" className="field-label">{searchMode === 'name' ? 'FIND A PERFUME' : 'EXPLORE NOTES'} <span>{searchMode === 'name' ? '이름 또는 브랜드' : '노트 또는 어코드'}</span></label><div className="search-input"><span aria-hidden="true">⌕</span><input id="perfume-search" maxLength={100} value={query} onChange={e => setQuery(e.target.value)} placeholder={searchMode === 'name' ? 'Try Dior, 톰포드, or your signature…' : 'Try vanilla, 장미, or bergamot…'} autoComplete="off"/></div>
          <p className="micro-copy">동결 모델과 호환되는 479개 향수 · 최대 10개 검색 결과{searchMode === 'notes' && <><br/>노트·어코드 검색은 아래 추천 향 조건과 별개입니다.</>}</p>
          <div className="search-results" aria-live="polite" aria-busy={searching}>
            {searching && <p className="empty-small">향을 찾고 있습니다…</p>}
            {searchError && <p role="alert" className="error">{searchError}</p>}
            {!query.trim() && <div className="search-hint"><span>↗</span><p>기억에 남는 향수를 찾아보세요.</p><small>브랜드나 향수명의 일부만 입력해도 됩니다.</small></div>}
            {!!query.trim() && !searching && !searchError && hits.length === 0 && suggestions.length === 0 && !searchHint && <p className="empty-small">{searchMode === 'notes' ? '검색 결과가 없습니다. 노트나 어코드 이름을 다시 확인해주세요.' : '검색 결과가 없습니다. 브랜드명이나 향수 이름을 다시 확인해주세요.'}</p>}
            {searchHint && !searching && <p className="empty-small">{searchHint}</p>}
            {suggestions.length > 0 && !searching && <div className="suggestions"><p>‘{query}’와 일치하는 {searchMode === 'notes' ? '노트·어코드' : '향수'}가 없습니다. 혹시 다음 검색어를 찾으셨나요?</p>{suggestions.map(s => <button type="button" key={s.query} disabled={busy} onClick={() => setQuery(s.query)}>{display(s.label)} <span>↗</span></button>)}</div>}
            {hits.map(p => <div className="search-hit" key={p.id}><div><small>{display(p.brand)}</small><h3>{display(p.name)}</h3><p>{p.accords.slice(0,3).join(' · ')}</p>{p.matched_notes?.length ? <p className="matched-meta">Matched note: {p.matched_notes.join(' · ')}</p> : null}{p.matched_accords?.length ? <p className="matched-meta">Matched accord: {p.matched_accords.join(' · ')}</p> : null}</div><button aria-label={`${display(p.name)} 선택`} disabled={busy || selected.some(s => s.id === p.id) || selected.length >= 50} onClick={() => {setSelected(v => [...v, {...p, rating: 7}]); changed()}}>{selected.some(s => s.id === p.id) ? '선택됨' : '+ 추가'}</button></div>)}
          </div></div>
          <div className="selected-pane"><div className="selected-heading"><span className="field-label">YOUR SCENT WARDROBE</span><span>{String(selected.length).padStart(2,'0')}</span></div>
            {!selected.length && <div className="wardrobe-empty"><span>＋</span><h3>당신의 취향을 담을 공간</h3><p>왼쪽에서 향수를 찾아 추가해 주세요.<br/>평점은 0~10점으로 입력합니다.</p></div>}
            {selected.map(p => <div className="selection" key={p.id}><div className="selection-top"><div><small>{display(p.brand)}</small><h3>{display(p.name)}</h3></div><button className="remove" disabled={busy} aria-label={`${display(p.name)} 삭제`} onClick={() => {setSelected(v => v.filter(s => s.id !== p.id)); changed()}}>×</button></div><div className="rating-row"><input disabled={busy} aria-label={`${display(p.name)} 평점`} type="range" min="0" max="10" step="0.5" value={p.rating} onChange={e => {setSelected(v => v.map(s => s.id === p.id ? {...s, rating: Number(e.target.value)} : s)); changed()}}/><output>{p.rating}<span> / 10</span></output></div></div>)}
            <p className="privacy-note">평점은 이번 추천에만 사용되며 영구 저장하지 않습니다.</p>
          </div></div>
      </section>
      <section className="scent-section section-shell"><div className="section-title compact"><div><p className="eyebrow">02 / SCENT PREFERENCE</p><h2>A direction, <em>if you wish.</em></h2></div><p>지금 끌리는 향의 계열을 하나 골라보세요.<br/>선택한 조건을 만족하는 향수만 추천합니다.</p></div><fieldset disabled={busy} className="scent-options"><legend className="sr-only">원하는 향 조건</legend>{scentOptions.map((s, index) => <label className={`scent-option ${scent === s.key ? 'active' : ''}`} key={s.key}><input type="radio" name="scent" value={s.key} checked={scent === s.key} onChange={() => {setScent(s.key); changed()}}/><span className="option-top"><span>0{index+1}</span><span className="radio-dot"/></span><strong>{s.label}</strong><small>{s.desc}</small></label>)}</fieldset><div className="recommend-action"><p>{!selected.length ? '향수를 하나 이상 선택하면 추천을 시작할 수 있습니다.' : selected.length < 3 ? '입력이 적어 추천 품질이 제한될 수 있어요. 3개 이상을 권장합니다.' : `${selected.length}개의 향수로 당신의 다음 향을 찾아볼게요.`}</p><button className="primary-button" disabled={!selected.length || busy} onClick={recommend}>{busy ? 'Finding your match…' : 'Discover my matches'}<span>{busy ? '◌' : '↗'}</span></button></div>{error && <p className="error" role="alert">{error}</p>}<div className="sr-only" aria-live="polite">{busy ? '추천 결과를 불러오는 중입니다.' : ''}</div></section>
      <section className="recommendations section-shell" ref={resultRef}><div className="section-title compact"><div><p className="eyebrow">03 / YOUR RECOMMENDATIONS</p><h2>Your next <em>five.</em></h2></div><p>취향과 향 특성을 함께 고려한 Hybrid 추천.<br/>추천 점수는 확률이나 만족도 백분율이 아닙니다.</p></div>
        {stale && results && <p className="notice">입력이 바뀌었습니다. 아래는 이전 입력의 결과입니다. 추천 버튼을 눌러 갱신해 주세요.</p>}
        {results === null ? <div className="results-empty"><span>THE NEXT CHAPTER OF YOUR SCENT STORY</span><p>당신의 다섯 가지 향이 이곳에 펼쳐집니다.</p></div> : results.length === 0 ? <div className="results-empty"><p>현재 조건에 맞는 추천 결과가 없습니다. 향 조건을 바꿔보세요.</p></div> : <div className="result-grid">{results.map(r => <article className="result-card" key={r.id}><div className="card-top"><span>Nº {String(r.rank).padStart(2,'0')}</span><span>HYBRID MATCH</span></div><div className="card-accent" aria-hidden="true">{r.accords[0] || 'scent'}</div><p className="brand">{display(r.brand)}</p><h3>{display(r.name)}</h3><div className="tags">{r.accords.slice(0,3).map(t => <span key={t}>{t}</span>)}</div><div className="shared"><span>SHARED WITH YOUR SELECTION</span><p>{r.shared_tokens.slice(0,5).map(t => (t.startsWith('note:') ? 'note / ' : 'accord / ') + t.split(':')[1]).join(' · ') || '공통 향 특성 없음'}</p></div><div className="card-score"><span>추천 점수</span><strong>{r.score.toFixed(4)}</strong></div></article>)}</div>}
        {results && <p className="micro-copy">공통 향 특성은 입력 향수와 추천 향수의 메타데이터 교집합입니다. 선호 원인을 설명하지 않습니다. 조건에 맞는 향수가 5개 미만이면 가능한 개수만 표시합니다.</p>}
      </section>
    </main><footer><a className="wordmark" href="#">SCENT MATCH</a><p>PERSONALIZED PERFUME RECOMMENDATION<br/>TEAM 12 · MACHINE LEARNING TERM PROJECT</p><span>LOCAL DEMO / FROZEN MODEL α 0.25</span></footer>
  </>
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
