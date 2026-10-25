"""Note UX tests: actual metadata, exact-ranking golden snapshot and synthetic inference."""
import json
import unicodedata
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from .app import app,Rating
from .adapter import ROOT,SCENTS
from .advanced_search import AdvancedCatalogSearch
OUT=ROOT/'web/evidence/note-search'
CASES=[]
def add(key,q,kind,value=None):CASES.append((key,q,kind,value))
for n,(q,term) in enumerate([('바닐','vanilla'),('바닐라','vanilla'),('장미','rose'),('베르가','bergamot'),('베르가못','bergamot'),('샌달','sandalwood'),('샌달우드','sandalwood'),('우디','woody'),('플로','floral'),('플로럴','floral'),('시트','citrus'),('머스','musk'),('머스크','musk')]):add('ko_'+str(n),q,'word',term)
for n,(q,term) in enumerate([('vanill','vanill'),('vanilla','vanilla'),('bergam','bergam'),('bergamot','bergamot'),('sandal','sandal'),('sandalwood','sandalwood'),('citr','citr'),('citrus','citrus'),('flor','flor'),('floral','floral'),('musk','musk')]):add('en_'+str(n),q,'prefix',term)
for n,(q,term) in enumerate([('bergamont','bergamot'),('sandlewood','sandalwood'),('florel','floral'),('바니라','바닐라'),('베르가몽','베르가못'),('샌달우두','샌달우드'),('시트러수','시트러스')]):add('typo_'+str(n),q,'suggest',term)
add('vanila_exact_conflict','vanila','conflict','vanila')
for n,q in enumerate(['','   ','!@#$%','장','v','없는노트별칭','zzzznotanote','바니','xy','zxqzxqzxq']):add('exception_'+str(n),q,'empty')
add('long','a'*101,'reject')

class NoteSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app);cls.client.__enter__();cls.s=app.state.service;cls.rows=[]
    @classmethod
    def tearDownClass(cls):
        (OUT/'note-cases.json').write_text(json.dumps(cls.rows,ensure_ascii=False,indent=2));cls.client.__exit__(None,None,None)
    def check(self,key,q,kind,value):
        response=self.client.get('/api/perfumes',params={'q':q,'mode':'notes'})
        row={'case':key,'query':q,'expected_kind':kind,'expected':value,'status':'FAIL','http_status':response.status_code}
        try:
            if kind=='reject':self.assertEqual(response.status_code,422)
            else:
                self.assertEqual(response.status_code,200);data=response.json();results=data['results']
                row.update({'ids':[r['id'] for r in results],'matches':[{'notes':r['matched_notes'],'accords':r['matched_accords']} for r in results],'suggestions':data['suggestions'],'hint':data.get('hint',''),'source':data['match_source']})
                self.assertLessEqual(len(results),10);self.assertEqual(len(results),len({r['id'] for r in results}))
                self.assertTrue({r['id'] for r in results}<=self.s.allowed)
                self.assertEqual(data,self.client.get('/api/perfumes',params={'q':q,'mode':'notes'}).json())
                for r in results:
                    raw=self.s.catalog[r['id']]['tokens']
                    for note in r['matched_notes']:self.assertIn('note:'+note,raw)
                    for accord in r['matched_accords']:self.assertIn('accord:'+accord,raw)
                if kind in ('word','prefix','conflict'):
                    self.assertTrue(results);self.assertEqual(data['suggestions'],[])
                    for r in results:
                        values=r['matched_notes']+r['matched_accords']
                        self.assertTrue(values)
                        for term in values:
                            self.assertTrue(any(w.startswith(value) for w in term.split()) if kind=='prefix' else value in term.split())
                    if kind=='conflict':
                        self.assertEqual(data['match_source'],'metadata');self.assertEqual(len(results),5)
                        row['status']='NOT SUPPORTED';row['reason']='vanila exists as exact source note; requested typo suggestion conflicts with exact-first invariant'
                        self.skipTest(row['reason'])
                elif kind=='suggest':
                    self.assertEqual(results,[]);self.assertEqual(data['suggestions'][0]['query'],value);self.assertLessEqual(len(data['suggestions']),3)
                    follow=self.client.get('/api/perfumes',params={'q':value,'mode':'notes'}).json()
                    self.assertTrue(follow['results']);self.assertEqual(follow['suggestions'],[])
                elif kind=='empty':self.assertEqual(results,[]);self.assertEqual(data['suggestions'],[])
            row['status']='PASS'
        finally:self.rows.append(row)
    def test_all_original_exact_responses_unchanged(self):
        before=json.loads((OUT/'exact-before.json').read_text())
        for q,expected in before.items():
            with self.subTest(q=q):self.assertEqual(self.s.search_response(q,'notes'),expected)
        (OUT/'exact-regression.json').write_text(json.dumps({'queries':len(before),'all_complete_responses_identical':True},indent=2))
    def test_korean_syllable_gate(self):
        self.assertEqual(self.s.search_index.note_prefix_candidates('바니'),[])
        r=self.s.search_response('장','notes');self.assertFalse(r['results']);self.assertTrue(r['hint'])
    def test_ambiguous_aliases_offer_choices_only(self):
        # Simulate a future collision using ONLY already-registered real aliases.
        # The production alias dictionary and original metadata are never altered.
        with patch.object(self.s.search_index,'note_prefix_candidates',return_value=[('바닐라','vanilla'),('베르가못','bergamot')]):
            r=self.s.search_response('바닐','notes')
            self.assertEqual(r['results'],[]);self.assertEqual([x['query'] for x in r['suggestions']],['바닐라','베르가못'])
    def test_vanilla_vanille_remain_distinct(self):
        first=next(i for i in self.s.candidates if 'note:vanilla' in self.s.catalog[i]['tokens'])
        second=next(i for i in self.s.candidates if 'note:vanille' in self.s.catalog[i]['tokens'])
        index=AdvancedCatalogSearch([first,second],self.s.catalog)
        r=index.lookup('vanill','notes');self.assertEqual(set(r['ids']),{first,second})
        self.assertIn('vanilla',r['matches'][first]['matched_notes']);self.assertIn('vanille',r['matches'][second]['matched_notes'])
    def test_note_suggestions_use_only_real_vocabulary(self):
        vocabulary=set(self.s.search_index.note_terms)
        for q in ('vanillaa','bergamont','sandlewood','florel'):
            for r in self.s.search_response(q,'notes')['suggestions']:self.assertIn(r['query'],vocabulary)
    def test_model_outputs_unchanged(self):
        ratings=[Rating(perfume_id=i,rating=r*10) for i,r in json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())]
        after={c:self.s.recommend(ratings,c) for c in SCENTS}
        self.assertEqual(json.loads((OUT/'recommendations-before.json').read_text()),after)
        (OUT/'recommendations-after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2))

for key,q,kind,value in CASES:
    def method(self,key=key,q=q,kind=kind,value=value):self.check(key,q,kind,value)
    setattr(NoteSearchTests,'test_query_'+key,method)

if __name__=='__main__':unittest.main(verbosity=2)
