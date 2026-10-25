"""Registered Korean-brand prefixes/typos only; actual catalog and frozen inference."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from .app import app,Rating
from .adapter import ROOT,SCENTS
from .test_search import BLACK,PARFUM,ELIXIR
from .search import normalize_search
OUT=ROOT/'web/evidence/brand-search'
CASES=[]
def add(key,q,kind,value=None):CASES.append((key,q,kind,value))
for n,q in enumerate(['톰포','톰 포','톰포드','톰 포드','톰 포 드']):add('tom_'+str(n),q,'brand','tom-ford')
for n,q in enumerate(['입생로','입생로랑','입 생 로']):add('ysl_'+str(n),q,'brand','yves-saint-laurent')
for n,(q,b) in enumerate([('디올','dior'),('샤넬','chanel'),('크리드','creed')]):add('exact_'+str(n),q,'brand',b)
for n,q in enumerate(['톰포 Black Orchid','톰포 black orchid','톰 포 Black Orchid']):add('mixed_'+str(n),q,'id',BLACK)
add('mixed_libre','입생로 Libre','libre');add('mixed_dior','디올 Sauvage Elixir','id',ELIXIR)
for n,(q,target) in enumerate([('톰포두','톰포드'),('입생로랄','입생로랑'),('톰포두 Black Orchid','톰포드 Black Orchid'),('톰 포두 Black Orchid','톰포드 Black Orchid')]):add('typo_'+str(n),q,'suggestion',target)
for n,q in enumerate(['Tom Ford','TomFord','tomfordblackorchid','Tom Ford Black Orchid','톰포드 Black Orchid','Dior Sauvage Elixir','Savage Elixir']):add('legacy_'+str(n),q,'legacy')
for n,q in enumerate(['톰','입','없는브랜드','zzzzNoBrand','미등록별칭','시','!@#$%','','   ','톰푸','qxzzvzz']):add('exception_'+str(n),q,'empty')
add('untranslated','톰포 블랙','hint');add('unknown_product','톰포 NotARealPerfume','hint')
add('long','a'*101,'reject')

class BrandSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app);cls.client.__enter__();cls.s=app.state.service;cls.rows=[]
        cls.legacy=json.loads((OUT/'name-before.json').read_text())
        cls.libre=next(i for i in cls.s.candidates if cls.s.catalog[i]['name']=='libre' and cls.s.catalog[i]['brand']=='yves-saint-laurent')
    @classmethod
    def tearDownClass(cls):
        (OUT/'brand-cases.json').write_text(json.dumps(cls.rows,ensure_ascii=False,indent=2));cls.client.__exit__(None,None,None)
    def check(self,key,q,kind,value):
        response=self.client.get('/api/perfumes',params={'q':q,'mode':'name'})
        record={'case':key,'query':q,'kind':kind,'expected':value,'http_status':response.status_code,'status':'FAIL'}
        try:
            if kind=='reject':self.assertEqual(response.status_code,422)
            else:
                self.assertEqual(response.status_code,200);data=response.json();rows=data['results'];ids=[r['id'] for r in rows]
                record.update({'ids':ids,'names':[r['name'] for r in rows],'brands':[r['brand'] for r in rows],'suggestions':data['suggestions'],'hint':data.get('hint'),'source':data['match_source']})
                self.assertLessEqual(len(ids),10);self.assertEqual(len(ids),len(set(ids)));self.assertTrue(set(ids)<=self.s.allowed)
                self.assertEqual(data['query'],q)
                self.assertEqual(data,self.client.get('/api/perfumes',params={'q':q,'mode':'name'}).json())
                if kind=='brand':self.assertTrue(rows);self.assertTrue(all(r['brand']==value for r in rows));self.assertEqual(data['suggestions'],[])
                elif kind=='id':self.assertEqual(ids[0],value);self.assertEqual(data['suggestions'],[])
                elif kind=='libre':self.assertEqual(ids[0],self.libre)
                elif kind=='legacy':
                    # The original golden set stores normalized catalog vocabulary.
                    # For capitalized English queries only the echoed query differs.
                    if q in self.legacy:expected=self.legacy[q]
                    elif normalize_search(q) in self.legacy:expected={**self.legacy[normalize_search(q)],'query':q}
                    else:
                        # Original STEP3-2 evidence predates this change and records
                        # typo-query suggestions absent from the catalog vocabulary.
                        old=json.loads((ROOT/'web/evidence/search-stage32/advanced-cases.json').read_text())
                        captured=next(r for r in old if r['query']==q)
                        self.assertEqual(captured['returned_ids'],[])
                        expected={'query':q,'resolved_query':normalize_search(q),'search_mode':'name',
                                  'match_source':captured['match_source'],'suggestions':captured['suggestions'],'results':[]}
                    self.assertEqual(data,expected)
                elif kind=='empty':self.assertEqual(ids,[]);self.assertEqual(data['suggestions'],[])
                elif kind=='hint':self.assertEqual(ids,[]);self.assertEqual(data['suggestions'],[]);self.assertTrue(data['hint'])
                elif kind=='suggestion':
                    self.assertEqual(ids,[]);self.assertEqual(data['suggestions'][0]['query'],value);self.assertLessEqual(len(data['suggestions']),3)
                    follow=self.client.get('/api/perfumes',params={'q':value,'mode':'name'}).json()
                    self.assertTrue(follow['results']);self.assertEqual(follow['suggestions'],[])
                    if 'Orchid' in q:self.assertEqual([r['id'] for r in follow['results']],[BLACK,PARFUM])
            record['status']='PASS'
        finally:self.rows.append(record)
    def test_existing_name_responses_unchanged(self):
        for q,expected in self.legacy.items():
            with self.subTest(q=q):self.assertEqual(self.s.search_response(q),expected)
        (OUT/'name-regression.json').write_text(json.dumps({'queries':len(self.legacy),'all_complete_responses_identical':True},indent=2))
    def test_existing_note_responses_unchanged(self):
        before=json.loads((OUT/'notes-before.json').read_text())
        for q,expected in before.items():
            with self.subTest(q=q):self.assertEqual(self.s.search_response(q,'notes'),expected)
        (OUT/'note-regression.json').write_text(json.dumps({'queries':len(before),'all_complete_responses_identical':True},indent=2))
    def test_ambiguity_requires_explicit_choice(self):
        # Controlled future-collision simulation with existing labels/brands only.
        with patch.object(self.s.search_index,'brand_prefix_candidates',return_value=[('tom ford','톰포드',''),('yves saint laurent','입생로랑','')]):
            r=self.s.search_response('톰포');self.assertEqual(r['results'],[])
            self.assertEqual([s['query'] for s in r['suggestions']],['톰포드','입생로랑']);self.assertTrue(r['hint'])
    def test_no_duplicate_brand_from_spaced_aliases(self):
        options=self.s.search_index.brand_prefix_candidates('톰 포 Black Orchid')
        self.assertEqual(options,[('tom ford','톰포드','Black Orchid')])
    def test_exact_alias_precedes_new_fallback(self):
        with patch.object(self.s.search_index,'brand_prefix_candidates',side_effect=AssertionError('fallback should not run')):
            r=self.s.search_response('톰포드 Black Orchid');self.assertEqual(r['results'][0]['id'],BLACK)
    def test_exact_korean_brand_keeps_existing_english_typo(self):
        response=self.s.search_response('톰포드 Black Orhid')
        self.assertEqual(response['results'],[])
        self.assertEqual(response['suggestions'][0]['query'],'tom ford black orchid')
        self.assertNotIn('hint',response)
    def test_synthetic_recommendation_json_identical(self):
        ratings=[Rating(perfume_id=i,rating=r*10) for i,r in json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())]
        after={c:self.s.recommend(ratings,c) for c in SCENTS}
        self.assertEqual(json.loads((OUT/'recommendations-before.json').read_text()),after)
        for r in after.values():
            scores=[x['score'] for x in r['results']];self.assertEqual(scores,sorted(scores,reverse=True))
        (OUT/'recommendations-after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2))

for key,q,kind,value in CASES:
    def method(self,key=key,q=q,kind=kind,value=value):self.check(key,q,kind,value)
    setattr(BrandSearchTests,'test_query_'+key,method)

if __name__=='__main__':unittest.main(verbosity=2)
