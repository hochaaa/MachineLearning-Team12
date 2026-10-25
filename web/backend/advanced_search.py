"""Optional search layers over STEP3-1 literal ranking; metadata and model stay intact."""
from difflib import SequenceMatcher
import re
import unicodedata
from .search import CatalogSearch, normalize_search

# User-provided common spellings, restricted to brands observed in frozen479.
# No translation service, purchased alias list or copied implementation.
BRAND_ALIASES = {
    'tom ford': ['톰포드', '톰 포드'], 'dior': ['디올'], 'chanel': ['샤넬'],
    'yves saint laurent': ['입생로랑', '입 생 로랑'], 'creed': ['크리드'],
}
NOTE_ALIASES = {'바닐라':'vanilla', '장미':'rose', '베르가못':'bergamot',
                '샌달우드':'sandalwood', '우디':'woody', '플로럴':'floral',
                '시트러스':'citrus', '머스크':'musk'}


def build_brand_aliases(brands, configured=None):
    """brands: normalized actual brand set; configured: canonical->[aliases] mapping.

    Add compact brand spellings and configured aliases only for present brands.
    Reject conflicting normalized aliases rather than guessing. Returns alias->brand.
    """
    configured = BRAND_ALIASES if configured is None else configured
    aliases = {}
    for brand in sorted(brands):
        for alias in [brand, brand.replace(' ', ''), *configured.get(brand, [])]:
            alias = normalize_search(alias)
            if alias in aliases and aliases[alias] != brand:
                raise ValueError('Conflicting search brand aliases')
            aliases[alias] = brand
    return aliases


class AdvancedCatalogSearch(CatalogSearch):
    """Extend base ranking with compact/alias lookup, cautious suggestions, note mode.

    candidates/catalog have the original CatalogSearch contract. IDs remain URLs.
    The inherited ranked() implementation and its ranking are unchanged.
    """
    def __init__(self, candidates, catalog):
        super().__init__(candidates, catalog)
        self.brands = frozenset(e[1] for e in self.entries)
        self.brand_aliases = build_brand_aliases(self.brands)
        # Derived only from existing aliases; compact Korean whitespace variants are
        # grouped per actual brand so 톰포드/톰 포드 do not look like two brands.
        self.korean_brand_forms = {}
        for alias, brand in self.brand_aliases.items():
            label = unicodedata.normalize('NFC', alias).replace(' ', '')
            if re.fullmatch(r'[가-힣]+', label):
                self.korean_brand_forms.setdefault(label, set()).add(brand)
        self.tokens_by_id = {i: tuple(catalog[i]['tokens']) for i, *_ in self.entries}
        vocabulary = {t.split(':', 1)[1] for ts in self.tokens_by_id.values() for t in ts}
        self.note_terms = tuple(sorted(vocabulary))
        self.note_aliases = {normalize_search(k):v for k,v in NOTE_ALIASES.items() if v in vocabulary}
        # Suggestions are real names/full names/brands, not fabricated perfume records.
        self.suggestion_terms = sorted({term for _, b, n, f, _ in self.entries for term in (b, n, f)})

    def resolve_brand(self, query):
        """query: normalized string; replace whole alias phrases, longest first."""
        for alias, brand in sorted(self.brand_aliases.items(), key=lambda p:(-len(p[0]),p[0])):
            if alias == brand: continue
            pattern = r'(?<!\w)' + re.escape(alias) + r'(?!\w)'
            query = re.sub(pattern, brand, query)
        return query

    def compact_ranked(self, query, limit=10):
        """Fuse spaces for lookup only; minimum3 chars; whole phrase/prefix/substring.

        Existing literal results always precede this fallback; no OR token expansion.
        """
        compact = query.replace(' ', '')
        if len(compact) < 3: return []
        matches = []
        for item, brand, name, full, _ in self.entries:
            b,n,f = (s.replace(' ', '') for s in (brand,name,full))
            tier = 0 if compact in (n,f) else 1 if f.startswith(compact) or n.startswith(compact) else 2 if compact in f else None
            if tier is not None:
                matches.append(((tier,len(full.split()),brand,name,item),item))
        return [i for _,i in sorted(matches)[:limit]]

    @staticmethod
    def similar_terms(query, vocabulary, cutoff=.86):
        """Shared SequenceMatcher scorer; normalized query/terms, cutoff, max3 results.

        Caller applies language/length gates. Values must come from actual vocabulary.
        Length-gap gate and deterministic tie order preserve existing name suggestions.
        """
        scored = []
        for term in vocabulary:
            if abs(len(term)-len(query)) > max(3, len(query)//4): continue
            score = SequenceMatcher(None, query, term, autojunk=False).ratio()
            if score >= cutoff: scored.append((-score, len(term), term))
        return [{'query':term,'label':term,'similarity':round(-score,4)}
                for score,_,term in sorted(scored)[:3]]

    def suggestions(self, query):
        """Unchanged name policy: ASCII>=5 chars, ratio>=.86, max3, no auto results."""
        if len(query.replace(' ', '')) < 5 or not re.fullmatch(r'[a-z0-9 ]+',query): return []
        return self.similar_terms(query, self.suggestion_terms)

    @staticmethod
    def korean_brand_parts(query):
        """Leading Korean fragments (longest first) plus unchanged product suffix.

        query may be raw UI text. NFC counts syllables, not decomposed Jamo. Spaces
        are ignored ONLY in the leading Korean brand fragment; suffix is not translated.
        Punctuation normalization reuses normalize_search for each leading token.
        """
        words=' '.join(unicodedata.normalize('NFC',query).split()).split()
        leading=[]
        for word in words:
            clean=unicodedata.normalize('NFC',normalize_search(word)).replace(' ','')
            if not re.fullmatch(r'[가-힣]+',clean):break
            leading.append(clean)
        return [(''.join(leading[:n]),' '.join(words[n:])) for n in range(len(leading),0,-1)
                if len(''.join(leading[:n]))>=2]

    def brand_prefix_candidates(self, query):
        """Return (actual brand, registered compact Korean label, product suffix).

        Minimum2 syllables; deduplicate aliases of the same brand. Longest matching
        Korean fragment wins, but multiple actual brands remain explicit choices.
        """
        for fragment,suffix in self.korean_brand_parts(query):
            matched={}
            for label,brands in sorted(self.korean_brand_forms.items()):
                if label.startswith(fragment):
                    for brand in sorted(brands):matched.setdefault(brand,label)
            if matched:return [(b,label,suffix) for b,label in sorted(matched.items())]
        return []

    def korean_brand_suggestions(self, query):
        """Brand-only typo correction, optionally retaining a product suffix verbatim.

        NFC>=3 syllables, existing alias Jamo similarity>=.85, max3, no auto results.
        Product suffix is never corrected/translated. Mixed suggestions are returned
        only if the resolved brand+suffix really finds a frozen479 item.
        """
        for fragment,suffix in self.korean_brand_parts(query):
            if len(fragment)<3:continue
            normalized={normalize_search(label):label for label in self.korean_brand_forms}
            proposed=self.similar_terms(normalize_search(fragment),normalized,.85)
            results=[]
            for candidate in proposed:
                label=normalized[candidate['query']]
                brands=self.korean_brand_forms[label]
                # A compact alias shared by actual brands is not a safe typo target.
                if len(brands)!=1:continue
                brand=next(iter(brands))
                if suffix and not self.ranked(normalize_search(brand+' '+suffix)):continue
                corrected=label+(' '+suffix if suffix else '')
                results.append({**candidate,'query':corrected,'label':corrected})
            if results:return results[:3]
        return []

    def korean_brand_response(self, original, response):
        """Search-only fallback after all existing literal/compact/exact-alias matches.

        original preserves the product suffix in suggestions. Ambiguity is explicit;
        no Korean perfume-name dictionary or arbitrary brand inference is introduced.
        """
        options=self.brand_prefix_candidates(original)
        if len(options)>1:
            return {**response,'suggestions':[{'query':label+(' '+tail if tail else ''),
                    'label':label+(' '+tail if tail else ''),'similarity':None}
                    for _,label,tail in options[:3]],
                    'hint':'여러 브랜드 접두어와 일치합니다. 브랜드를 선택해 주세요.'}
        if len(options)==1:
            brand,label,suffix=options[0]
            resolved=normalize_search(brand+' '+suffix)
            ids=self.ranked(resolved)
            if ids:return {**response,'ids':ids,'resolved_query':resolved,'match_source':'brand_prefix'}
            hint='브랜드는 찾았지만 해당 향수는 479개 후보군에서 찾지 못했습니다. 향수명을 확인해 주세요.'
            if re.search(r'[가-힣]',unicodedata.normalize('NFC',suffix)):
                hint='브랜드는 찾았지만 한국어 향수명 번역은 지원하지 않습니다. 향수명을 원문으로 입력해 주세요.'
            return {**response,'resolved_query':resolved,'hint':hint}
        proposed=self.korean_brand_suggestions(original)
        if proposed:return {**response,'suggestions':proposed}
        # English typo suggestions retain their previous implementation and order.
        if re.search(r'[가-힣]',unicodedata.normalize('NFC',original)):
            return {**response,'hint':'등록된 한국어 브랜드의 두 음절 이상을 입력해 주세요. 오타 제안은 세 음절부터 지원합니다.'}
        return response

    def note_prefix_candidates(self, query):
        """Return (registered Korean label, actual term) prefix matches.

        query is normalized but composed to NFC for *syllable* prefix/length checks.
        바니 must not match 바닐라 via a shared initial Jamo sequence. Minimum2 syllables.
        """
        composed = unicodedata.normalize('NFC', query)
        if not re.fullmatch(r'[가-힣]{2,}', composed): return []
        return sorted((unicodedata.normalize('NFC', alias), value)
                      for alias,value in self.note_aliases.items()
                      if unicodedata.normalize('NFC', alias).startswith(composed))

    def note_prefix_lookup(self, query):
        """English word prefixes only (each>=3 ASCII letters); preserve actual values.

        AND prefixes within a token; note matches before accord, then brand/name/URL.
        Called only after original whole-word lookup returned zero results.
        """
        words=query.split()
        if not words or not all(re.fullmatch(r'[a-z]{3,}', w) for w in words): return [],{}
        found=[]
        for item,brand,name,_,_ in self.entries:
            notes=[];accords=[]
            for token in self.tokens_by_id[item]:
                kind,value=token.split(':',1)
                available=normalize_search(value).split()
                if all(any(w.startswith(prefix) for w in available) for prefix in words):
                    if kind=='note': notes.append(value)
                    elif kind=='accord': accords.append(value)
            if notes or accords:
                found.append(((0 if notes else 1,brand,name,item),item,
                              {'matched_notes':notes,'matched_accords':accords}))
        found.sort()
        return [i for _,i,_ in found[:10]],{i:fields for _,i,fields in found[:10]}

    def note_suggestions(self, query):
        """English>=5 letters cutoff.82; registered Korean aliases>=3 syllables cutoff.87.

        Korean compares normalized Jamo for one-character variation, but gates length
        on NFC syllables. Return clickable original alias labels, never auto-correct IDs.
        """
        composed=unicodedata.normalize('NFC',query)
        if re.fullmatch(r'[가-힣]{3,}',composed):
            result=self.similar_terms(query, self.note_aliases, .87)
            return [{**r,'query':unicodedata.normalize('NFC',r['query']),
                     'label':unicodedata.normalize('NFC',r['label'])} for r in result]
        if re.fullmatch(r'[a-z ]+',query) and len(query.replace(' ',''))>=5:
            return self.similar_terms(query, self.note_terms, .82)
        return []

    def note_response(self, query, response):
        """Keep exact/whole-word rankings intact, then prefixes, then suggestions.

        response is search-only wrapper. Ambiguous alias prefixes yield choices only.
        Single-character/short typos receive a hint, without new aliases or model rules.
        """
        ids,fields,resolved=self.note_lookup(query)
        if ids:
            return {**response,'ids':ids,'matches':fields,'resolved_query':resolved,'match_source':'metadata'}
        aliases=self.note_prefix_candidates(query)
        if len(aliases)==1:
            label,term=aliases[0]
            ids,fields,resolved=self.note_lookup(term)
            return {**response,'ids':ids,'matches':fields,'resolved_query':resolved,'match_source':'note_alias_prefix'}
        if len(aliases)>1:
            return {**response,'suggestions':[{'query':label,'label':label,'similarity':None} for label,_ in aliases[:3]],
                    'hint':'여러 노트 별칭과 일치합니다. 검색어를 선택해 주세요.'}
        ids,fields=self.note_prefix_lookup(query)
        if ids:return {**response,'ids':ids,'matches':fields,'match_source':'note_prefix'}
        proposed=self.note_suggestions(query)
        if proposed:return {**response,'suggestions':proposed}
        composed=unicodedata.normalize('NFC',query)
        hint=''
        if re.fullmatch(r'[가-힣]',composed): hint='한국어 노트는 두 글자 이상 입력해 주세요.'
        elif re.fullmatch(r'[가-힣]{2}',composed): hint='일치하는 노트 별칭이 없습니다. 오타 제안은 세 글자부터 지원합니다.'
        elif re.fullmatch(r'[a-z]{1,2}',query): hint='영어 노트는 세 글자 이상 입력해 주세요.'
        return {**response,'hint':hint} if hint else response

    def note_lookup(self, query):
        """query: normalized note/accord text; AND whole words within each token.

        Literal stored note/accord values are returned separately as matched_* fields.
        Exact note, phrase note, exact accord, phrase accord order; deterministic ties.
        No filter state or recommendation arguments are changed by this search.
        """
        resolved = self.note_aliases.get(query,query)
        terms = frozenset(resolved.split())
        matches = []
        if not terms: return [],{},resolved
        for item,brand,name,full,_ in self.entries:
            notes=[];accords=[];tiers=[]
            for token in self.tokens_by_id[item]:
                kind,value = token.split(':',1)
                if terms <= set(normalize_search(value).split()):
                    if kind == 'note': notes.append(value);tiers.append(0 if value==resolved else 1)
                    elif kind == 'accord': accords.append(value);tiers.append(2 if value==resolved else 3)
            if tiers:
                matches.append(((min(tiers),brand,name,item),item,{'matched_notes':notes,'matched_accords':accords}))
        matches.sort()
        return [i for _,i,_ in matches[:10]], {i:fields for _,i,fields in matches[:10]}, resolved

    def lookup(self, query, mode='name'):
        """query: raw UI text; mode: name/notes. Return IDs plus search-only metadata.

        Priority: unchanged literal ranking, compact fallback, brand alias ranking,
        then suggestions only. Never fill an existing exact result list with fuzzy hits.
        """
        original=query
        query=normalize_search(query)
        response={'ids':[],'suggestions':[],'query':original,'resolved_query':query,
                  'search_mode':mode,'match_source':'none','matches':{}}
        if not query:return response
        if mode=='notes':
            return self.note_response(query, response)
        if mode!='name':raise ValueError('Unknown search mode')
        ids=self.ranked(query)
        if ids:return {**response,'ids':ids,'match_source':'literal'}
        ids=self.compact_ranked(query)
        if ids:return {**response,'ids':ids,'match_source':'compact'}
        resolved=self.resolve_brand(query)
        ids=self.ranked(resolved) if resolved!=query else []
        if ids:return {**response,'ids':ids,'resolved_query':resolved,'match_source':'brand_alias'}
        # Preserve existing English typo suggestions after an exact Korean alias
        # (e.g. 톰포드 Black Orhid), before new Korean-brand fallback layers.
        existing=self.suggestions(resolved)
        if existing:return {**response,'suggestions':existing}
        korean=self.korean_brand_response(original, response)
        if korean != response:return korean
        return {**response,'suggestions':self.suggestions(resolved)}
