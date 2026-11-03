import React, { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

type Perfume = { id: string; name: string; brand: string; accords: string[]; notes: string[]; matched_notes?: string[]; matched_accords?: string[] }
type Selection = Perfume & { rating: number }
type Result = Perfume & { rank: number; score: number }
type Suggestion = { query: string; label: string; similarity: number | null }
type SearchMode = 'name' | 'notes'
type Scent = 'none' | 'woody' | 'floral' | 'rose' | 'citrus' | 'amber' | 'vanilla'
const API = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const display = (value: string) => value.replaceAll('-', ' ')
const searchHints: Record<string, string> = {
  '여러 브랜드 접두어와 일치합니다. 브랜드를 선택해 주세요.': 'Several brands match. Choose one below.',
  '브랜드는 찾았지만 해당 향수는 479개 후보군에서 찾지 못했습니다. 향수명을 확인해 주세요.': 'We found the brand. Check the perfume name and try again.',
  '브랜드는 찾았지만 한국어 향수명 번역은 지원하지 않습니다. 향수명을 원문으로 입력해 주세요.': 'We found the brand. Enter the original perfume name.',
  '등록된 한국어 브랜드의 두 음절 이상을 입력해 주세요. 오타 제안은 세 음절부터 지원합니다.': 'Enter at least two syllables for a Korean brand. Suggestions start at three.',
  '여러 노트 별칭과 일치합니다. 검색어를 선택해 주세요.': 'Several notes match. Choose one below.',
  '한국어 노트는 두 글자 이상 입력해 주세요.': 'Enter at least two characters for a Korean note.',
  '일치하는 노트 별칭이 없습니다. 오타 제안은 세 글자부터 지원합니다.': 'No matching note. Suggestions start at three characters.',
  '영어 노트는 세 글자 이상 입력해 주세요.': 'Enter at least three letters for an English note.',
}

const scentOptions: {key: Scent; label: string; desc: string}[] = [
  {key: 'none', label: 'Open to discovery', desc: 'Explore all scent families'},
  {key: 'woody', label: 'Woody', desc: 'Warm woods and earthy depth'},
  {key: 'floral', label: 'Floral', desc: 'Soft petals and bright blooms'},
  {key: 'rose', label: 'Rose', desc: 'Fragrances with rose notes'},
  {key: 'citrus', label: 'Citrus', desc: 'Bright, zesty accords'},
  {key: 'amber', label: 'Amber', desc: 'Warm, resinous accords'},
  {key: 'vanilla', label: 'Vanilla', desc: 'Soft, sweet vanilla accords'},
]
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API + path, {...init, signal: init?.signal ?? AbortSignal.timeout(20000)})
  if (!response.ok) throw new Error(response.status === 503 ? 'The recommendation service is starting up. Please try again.' : response.status === 422 ? 'Choose distinct perfumes and enter ratings between 0 and 10.' : 'The service could not complete your request. Please try again.')
  return response.json()
}
function CloseIcon() {
  return <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M4 4l8 8m0-8-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
}

function matchScore(score: number) {
  return (1 + 9 * Math.max(0, Math.min(1, score))).toFixed(1)
}

async function downloadMatches(results: Result[]) {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Image rendering is unavailable.')

  const width = 880
  const padding = 48
  const cardWidth = width - 2 * padding
  const textWidth = cardWidth - 48
  ctx.font = '30px Georgia, serif'
  const cards = results.map(result => {
    const nameLines: string[] = []
    for (const word of display(result.name).split(/\s+/)) {
      const last = nameLines.at(-1)
      if (last && ctx.measureText(last + ' ' + word).width <= textWidth) {
        nameLines[nameLines.length - 1] = last + ' ' + word
      } else {
        nameLines.push(word)
      }
    }
    return { result, nameLines, height: 106 + nameLines.length * 36 }
  })
  const height = 162 + cards.reduce((sum, card) => sum + card.height + 14, 0) + padding
  canvas.width = width * 2
  canvas.height = height * 2
  ctx.scale(2, 2)
  ctx.fillStyle = '#f4f1eb'
  ctx.fillRect(0, 0, width, height)
  ctx.fillStyle = '#626e56'
  ctx.font = 'bold 16px Arial, sans-serif'
  ctx.fillText('SCENT MATCH', padding, 58)
  ctx.fillStyle = '#292e2b'
  ctx.font = '48px Georgia, serif'
  ctx.fillText('Your scent matches.', padding, 121)

  let y = 162
  for (const { result, nameLines, height: cardHeight } of cards) {
    ctx.beginPath()
    ctx.roundRect(padding, y, cardWidth, cardHeight, 16)
    ctx.fillStyle = '#faf9f4'
    ctx.fill()
    ctx.strokeStyle = '#d7d9ce'
    ctx.stroke()
    ctx.fillStyle = '#5f685b'
    ctx.font = '14px Arial, sans-serif'
    ctx.fillText(display(result.brand).toUpperCase(), padding + 24, y + 30, textWidth)
    ctx.fillStyle = '#292e2b'
    ctx.font = '30px Georgia, serif'
    nameLines.forEach((line, index) => ctx.fillText(line, padding + 24, y + 66 + index * 36, textWidth))
    ctx.fillStyle = '#5f685b'
    ctx.font = '16px Arial, sans-serif'
    ctx.fillText(result.accords.slice(0, 3).join(' · '), padding + 24, y + cardHeight - 42, textWidth)
    ctx.fillText(`Match score  ${matchScore(result.score)} / 10`, padding + 24, y + cardHeight - 17)
    y += cardHeight + 14
  }

  const png = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('PNG encoding failed.')), 'image/png')
  })
  const url = URL.createObjectURL(png)
  const link = document.createElement('a')
  link.href = url
  link.download = 'scent-match-recommendations.png'
  document.body.append(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000)
}

function App() {
  const [selected, setSelected] = useState<Selection[]>([])
  const [query, setQuery] = useState('')
  const [searchMode, setSearchMode] = useState<SearchMode>('name')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [searchHint, setSearchHint] = useState('')
  const [hits, setHits] = useState<Perfume[]>([])
  const [discoveryVersion, setDiscoveryVersion] = useState(0)
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [scent, setScent] = useState<Scent>('none')
  const [results, setResults] = useState<Result[] | null>(null)
  const [saving, setSaving] = useState(false)
  const downloadConfirmation = useRef<HTMLDialogElement>(null)
  const [saveError, setSaveError] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [ready, setReady] = useState<boolean | null>(null)
  const [preferences, setPreferences] = useState(() => location.hash === '#preferences')
  const [modal, setModal] = useState<'scent' | 'results' | null>(null)
  const dialog = useRef<HTMLDialogElement>(null)
  const dialogTitle = useRef<HTMLHeadingElement>(null)
  const recommendation = useRef<AbortController | null>(null)

  useEffect(() => {
    function navigate() {
      setPreferences(location.hash === '#preferences')
      setModal(null)
      recommendation.current?.abort()
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', navigate)
    return () => {
      window.removeEventListener('hashchange', navigate)
      recommendation.current?.abort()
    }
  }, [])

  useEffect(() => {
    const element = dialog.current
    if (!element) return
    if (modal) {
      if (!element.open) element.showModal()
      element.scrollTop = 0
      dialogTitle.current?.focus()
    } else if (element.open) {
      element.close()
    }
  }, [modal, preferences])
  useEffect(() => {request<{recommendation_ready: boolean}>('/api/health').then(h => setReady(h.recommendation_ready)).catch(() => setReady(false))}, [])
  useEffect(() => {
    if (!preferences) return
    const controller = new AbortController()
    setSearching(true); setSearchError(''); setHits([]); setSuggestions([]); setSearchHint('')
    const timer = setTimeout(() => {
      request<{results: Perfume[]; suggestions?: Suggestion[]; hint?: string}>(query.trim() ? '/api/perfumes?mode=' + searchMode + '&q=' + encodeURIComponent(query.trim()) : '/api/perfumes/discover', {signal: controller.signal})
        .then(data => {if (!controller.signal.aborted) {setHits(data.results); setSuggestions(data.suggestions ?? []); setSearchHint(data.hint ? searchHints[data.hint] ?? 'Try a more specific search.' : '')}})
        .catch(() => {if (!controller.signal.aborted) setSearchError('Search is temporarily unavailable.')})
        .finally(() => {if (!controller.signal.aborted) setSearching(false)})
    }, query.trim() ? 220 : 0)
    return () => {clearTimeout(timer); controller.abort()}
  }, [preferences, query, searchMode, discoveryVersion])

  function dismissModal() {
    recommendation.current?.abort()
    setModal(null)
  }

  async function recommend() {
    const controller = new AbortController()
    recommendation.current = controller
    setBusy(true)
    setError('')
    setSaveError('')
    try {
      const data = await request<{results: Result[]}>('/api/recommend', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          ratings: selected.map(p => ({perfume_id: p.id, rating: p.rating})),
          required_scent: scent,
          top_k: 5,
        }),
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(20000)]),
      })
      if (controller.signal.aborted) return
      setResults(data.results)
      setReady(true)
      setModal('results')
    } catch (e) {
      if (!controller.signal.aborted) {
        setError(e instanceof Error && e.name === 'Error' ? e.message : 'Could not load recommendations. Please try again.')
      }
    } finally {
      if (recommendation.current === controller) {
        recommendation.current = null
        setBusy(false)
      }
    }
  }

  async function saveMatches() {
    if (!results?.length) return
    setSaving(true)
    setSaveError('')
    try {
      await downloadMatches(results)
    } catch {
      setSaveError('Could not save the image. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return <>
    <header className="site-nav">
      <a href="#" className="wordmark">SCENT MATCH<span>TEAM 12 / PERFUME CURATION</span></a>
    </header>
    <main>
      {!preferences ? (
        <section className="hero">
          <div className="hero-copy">
            <h1>Your taste.<br/>A new <em>signature.</em></h1>
            <p className="hero-description">Discover your next scent through the perfumes you already love.</p>
            <a className="primary-button" href="#preferences">Find your scent</a>
            <p className="hero-flow">Rate perfumes · Choose a scent family · Get your matches</p>
          </div>
        </section>
      ) : (
        <section className="preferences section-shell">
          <div className="section-title">
            <div>
              <p className="eyebrow">01 / YOUR PREFERENCES</p>
              <h2>Start with what<br/>you <em>know.</em></h2>
            </div>
          </div>
          {ready === false && <p className="notice" role="status">The recommendation service is unavailable. Please try again when it reconnects.</p>}
          <div className="preference-grid">
            <div className="search-pane">
              <div className="search-mode" role="group" aria-label="Search mode">
                <button type="button" aria-pressed={searchMode === 'name'} onClick={() => setSearchMode('name')}>Perfume / Brand</button>
                <button type="button" aria-pressed={searchMode === 'notes'} onClick={() => setSearchMode('notes')}>Perfume Notes</button>
              </div>
              <div className="search-input">
                <span aria-hidden="true">⌕</span>
                <input id="perfume-search" aria-label={searchMode === 'name' ? 'Search by perfume or brand' : 'Search by note or accord'}
                  maxLength={100} value={query} onChange={e => setQuery(e.target.value)}
                  placeholder={searchMode === 'name' ? 'Try Dior or Black Orchid…' : 'Try vanilla, rose, or bergamot…'} autoComplete="off"/>
              </div>
              <div className="search-results" role="region" aria-label="Perfume results" tabIndex={0} aria-live="polite" aria-busy={searching}>
                {searching && <p className="empty-small">Finding perfumes…</p>}
                {searchError && <p role="alert" className="error">{searchError} <button type="button" onClick={() => setDiscoveryVersion(v => v + 1)}>Try again</button></p>}
                {!query.trim() && <div className="discovery-heading">
                  <div><p>Explore some perfumes</p><small>Add the ones you know and give them a rating.</small></div>
                  <button type="button" disabled={searching} onClick={() => setDiscoveryVersion(v => v + 1)}>Show more perfumes</button>
                </div>}
                {!searching && !searchError && hits.length === 0 && suggestions.length === 0 && !searchHint && (
                  <p className="empty-small">{query.trim() ? 'No matches. Try another search.' : 'No perfumes to show. Try refreshing the list.'}</p>
                )}
                {searchHint && !searching && <p className="empty-small">{searchHint}</p>}
                {suggestions.length > 0 && !searching && <div className="suggestions">
                  <p>Did you mean one of these?</p>
                  {suggestions.map(s => <button type="button" key={s.query} onClick={() => setQuery(s.query)}>{display(s.label)}</button>)}
                </div>}
                {hits.map(p => {
                  const added = selected.some(s => s.id === p.id)
                  return <div className="search-hit" key={p.id}>
                    <div>
                      <small>{display(p.brand)}</small>
                      <h3>{display(p.name)}</h3>
                      <p>{p.accords.slice(0,3).join(' · ')}</p>
                      {!!p.matched_notes?.length && <p className="matched-meta">Matched note: {p.matched_notes.join(' · ')}</p>}
                      {!!p.matched_accords?.length && <p className="matched-meta">Matched accord: {p.matched_accords.join(' · ')}</p>}
                    </div>
                    <button type="button" aria-label={added ? undefined : `Add ${display(p.name)}`}
                      disabled={added || selected.length >= 50} onClick={() => setSelected(v => [...v, {...p, rating: 7}])}>
                      {added ? 'Added' : '+ Add'}
                    </button>
                  </div>
                })}
              </div>
            </div>
            <div className="selected-pane">
              <div className="selected-heading">
                <span className="field-label">YOUR SCENT WARDROBE</span>
                <span>{String(selected.length).padStart(2,'0')}</span>
              </div>
              {!selected.length && <div className="wardrobe-empty">
                <span aria-hidden="true">＋</span>
                <h3>Build your scent wardrobe</h3>
                <p>Add perfumes and rate them from 0 to 10.</p>
              </div>}
              {selected.map(p => <div className="selection" key={p.id}>
                <div className="selection-top">
                  <div><small>{display(p.brand)}</small><h3>{display(p.name)}</h3></div>
                  <button className="remove" type="button" aria-label={`Remove ${display(p.name)}`}
                    onClick={() => setSelected(v => v.filter(s => s.id !== p.id))}><CloseIcon/></button>
                </div>
                <div className="rating-row">
                  <input aria-label={`Rate ${display(p.name)}`} type="range" min="0" max="10" step="0.5" value={p.rating}
                    onChange={e => setSelected(v => v.map(s => s.id === p.id ? {...s, rating: Number(e.target.value)} : s))}/>
                  <output>{p.rating}<span> / 10</span></output>
                </div>
              </div>)}
              <div className="wardrobe-actions">
                <p className="rating-guidance">Choose perfumes you’ve used and rate them. One or two are enough to get started, but three or more give us a fuller picture of your taste.</p>
                <button type="button" className="primary-button" disabled={!selected.length || busy}
                  onClick={() => {setError(''); setModal('scent')}}>Choose a scent family</button>
              </div>
            </div>
          </div>
          <dialog ref={dialog} className={`match-dialog ${modal === 'results' ? 'results-dialog' : ''}`}
            aria-labelledby="match-dialog-title" onCancel={e => {e.preventDefault(); dismissModal()}}>
            <button type="button" className="dialog-close" aria-label="Close dialog" onClick={dismissModal}><CloseIcon/></button>
            {modal === 'scent' && <>
              <p className="eyebrow">02 / SCENT PREFERENCE</p>
              <h2 id="match-dialog-title" ref={dialogTitle} tabIndex={-1}>A direction, <em>if you wish.</em></h2>
              <fieldset disabled={busy} className="scent-options">
                <legend className="sr-only">Scent family</legend>
                {scentOptions.map(option => <label className={`scent-option ${scent === option.key ? 'active' : ''}`} key={option.key}>
                  <input type="radio" name="scent" value={option.key} checked={scent === option.key} onChange={() => setScent(option.key)}/>
                  <span className="radio-dot" aria-hidden="true"/>
                  <strong>{option.label}</strong><small>{option.desc}</small>
                </label>)}
              </fieldset>
              {error && <p className="error" role="alert">{error}</p>}
              <div className="recommend-action">
                <button type="button" className="primary-button" disabled={busy} onClick={recommend}>
                  {busy ? 'Finding your matches…' : 'Discover my matches'}
                </button>
              </div>
              <span className="sr-only" role="status">{busy ? 'Loading recommendations.' : ''}</span>
            </>}
            {modal === 'results' && results && <>
              <p className="eyebrow">03 / YOUR RECOMMENDATIONS</p>
              <div className="results-heading">
                <h2 id="match-dialog-title" ref={dialogTitle} tabIndex={-1}>Your scent <em>matches.</em></h2>
                {results.length > 0 && <button type="button" className="primary-button" disabled={saving}
                  onClick={() => downloadConfirmation.current?.showModal()}>
                  {saving ? 'Saving…' : 'Save image'}
                </button>}
              </div>
              {results.length === 0 ? <p className="empty-small">No matches for this scent family. Try a different one.</p> : (
                <div className="result-grid">
                  {results.map(r => <article className="result-card" key={r.id}>
                    <div className="card-identity"><p className="brand">{display(r.brand)}</p><h3>{display(r.name)}</h3></div>
                    <div className="tags">{r.accords.slice(0, 3).map(accord => <span key={accord}>{accord}</span>)}</div>
                    {r.accords[0] && <p className="card-accent">{r.accords[0]}</p>}
                    <div className="card-score">
                      <span>Match score</span>
                      <strong>{matchScore(r.score)}<small> / 10</small></strong>
                    </div>
                  </article>)}
                </div>
              )}
              {saveError && <p className="error" role="alert">{saveError}</p>}
              <div className="recommend-action">
                <button type="button" className="primary-button secondary-button" onClick={() => setModal('scent')}>Change scent family</button>
              </div>
            </>}
          </dialog>
          {modal === 'results' && <dialog ref={downloadConfirmation} className="match-dialog download-confirmation"
            aria-labelledby="download-confirmation-title">
            <h2 id="download-confirmation-title">Download your matches?</h2>
            <p>Would you like to download your recommendation results as an image?</p>
            <form method="dialog" className="recommend-action">
              <button className="primary-button secondary-button" autoFocus>No</button>
              <button type="button" className="primary-button" onClick={() => {
                downloadConfirmation.current?.close()
                void saveMatches()
              }}>Yes</button>
            </form>
          </dialog>}
        </section>
      )}
    </main>
  </>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
