"""Search-only integration tests and synthetic inference regression; never train/evaluate."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from .app import app, Rating
from .adapter import ROOT,SCENTS
from .advanced_search import build_brand_aliases
from .test_search import ELIXIR,BLACK,PARFUM,BLEU
OUT=ROOT/'web/evidence/search-stage32'
# (label, raw query, mode, expectation kind, expected value)
CASES=[]
def add(label,query,kind,value=None,mode='name'):CASES.append((label,query,mode,kind,value))
for n,q in enumerate(['Tom Ford','TomFord','tomford','TOMFORD']):add(f'compact_brand_{n}',q,'brand','tom-ford')
for n,q in enumerate(['TomFord Black Orchid','tomford black orchid','tomfordblackorchid','Tom Ford Black Orchid','톰포드 Black Orchid']):add(f'compact_product_{n}',q,'id',BLACK)
add('missing_maison','MaisonMargiela','absent_brand','maison-margiela')
add('ysl_compact','YvesSaintLaurent','brand','yves-saint-laurent')
for n,(q,correct,target) in enumerate([('Savage Elixir','sauvage elixir',ELIXIR),('Dior Savage Elixir','dior sauvage elixir',ELIXIR),('Black Orhid','black orchid',BLACK),('Tom Frod','tom ford',BLACK)]):add(f'typo_{n}',q,'suggestion',(correct,target))
add('bleu_exact','Bleu de Chanel','id',BLEU)
for n,(q,target) in enumerate([('톰포드',BLACK),('디올 Sauvage Elixir',ELIXIR),('샤넬 Bleu de Chanel',BLEU),('크리드 Aventus','https://www.fragrantica.com/perfume/creed/aventus-9828.html')]):add(f'korean_{n}',q,'contains',target)
add('ysl_korean','입생로랑','brand','yves-saint-laurent')
for n,(q,term) in enumerate([('vanilla','vanilla'),('rose','rose'),('bergamot','bergamot'),('sandalwood','sandalwood'),('바닐라','vanilla'),('장미','rose'),('베르가못','bergamot'),('우디','woody'),('샌달우드','sandalwood'),('플로럴','floral'),('시트러스','citrus'),('머스크','musk')]):add(f'notes_{n}',q,'metadata',term,'notes')
for n,(q,target) in enumerate([('Dior Sauvage Elixir',ELIXIR),('Sauvage Elixir',ELIXIR),('dior-sauvage-elixir',ELIXIR),('sauvage dior',ELIXIR),('Black Orchid',BLACK),('Black Orchid Parfum',PARFUM),('Bleu de Chanel Parfum',BLEU)]):add(f'regression_{n}',q,'id',target)
for n,q in enumerate(['','   ','!@#$%^','zzzzNonexistentBrand','zzzzNonexistentPerfume','틀린브랜드별칭','qxjzzwwvvqq']):add(f'empty_{n}',q,'empty')
add('long','a'*101,'reject');add('broad','a','ten');add('short_no_fuzzy','xz','empty')
for q in ['조말론','바이레도','딥티크','르라보']:add('missing_'+q,q,'absent_alias')

class AdvancedSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app);cls.client.__enter__();cls.service=app.state.service;cls.rows=[]
    @classmethod
    def tearDownClass(cls):
        (OUT/'advanced-cases.json').write_text(json.dumps(cls.rows,ensure_ascii=False,indent=2))
        cls.client.__exit__(None,None,None)
    def check(self,label,q,mode,kind,value):
        response=self.client.get('/api/perfumes',params={'q':q,'mode':mode})
        row={'case':label,'query':q,'mode':mode,'kind':kind,'status':'FAIL','http_status':response.status_code}
        try:
            if kind=='reject':self.assertEqual(response.status_code,422)
            else:
                self.assertEqual(response.status_code,200);data=response.json();rows=data['results'];ids=[r['id'] for r in rows]
                row.update({'returned_ids':ids,'names':[r['name'] for r in rows],'suggestions':data['suggestions'],'match_source':data['match_source']})
                self.assertLessEqual(len(ids),10);self.assertEqual(len(ids),len(set(ids)));self.assertTrue(set(ids)<=self.service.allowed)
                self.assertEqual(data,self.client.get('/api/perfumes',params={'q':q,'mode':mode}).json())
                if kind in ('absent_brand','absent_alias'):
                    self.assertEqual(ids,[]);self.assertEqual(data['suggestions'],[])
                    row['status']='NOT SUPPORTED';self.skipTest('Requested brand/alias is absent from frozen479')
                elif kind=='id':self.assertEqual(ids[0],value);self.assertEqual(data['suggestions'],[])
                elif kind=='contains':self.assertIn(value,ids);self.assertEqual(data['suggestions'],[])
                elif kind=='brand':self.assertTrue(rows);self.assertTrue(all(r['brand']==value for r in rows))
                elif kind=='suggestion':
                    self.assertEqual(ids,[]);self.assertEqual(data['suggestions'][0]['query'],value[0])
                    self.assertLessEqual(len(data['suggestions']),3)
                    follow=self.client.get('/api/perfumes',params={'q':value[0]}).json()
                    self.assertIn(value[1],[r['id'] for r in follow['results']]);self.assertEqual(follow['suggestions'],[])
                elif kind=='metadata':
                    self.assertTrue(rows);self.assertEqual(data['suggestions'],[])
                    for r in rows:
                        self.assertTrue(r['matched_notes'] or r['matched_accords'])
                        tokens=set(self.service.catalog[r['id']]['tokens'])
                        for note in r['matched_notes']:self.assertIn('note:'+note,tokens);self.assertIn(value,note.split())
                        for accord in r['matched_accords']:self.assertIn('accord:'+accord,tokens);self.assertIn(value,accord.split())
                    row['matched']=[{'id':r['id'],'notes':r['matched_notes'],'accords':r['matched_accords']} for r in rows]
                elif kind=='empty':self.assertEqual(ids,[]);self.assertEqual(data['suggestions'],[])
                elif kind=='ten':self.assertEqual(len(ids),10)
            row['status']='PASS'
        finally:self.rows.append(row)
    def test_alias_collision(self):
        with self.assertRaises(ValueError):build_brand_aliases({'tom ford','dior'},{'tom ford':['충돌'],'dior':['충돌']})
        self.assertNotIn('없는브랜드',build_brand_aliases({'dior'},{'not real':['없는브랜드']}))
    def test_no_automatic_fuzzy_ids_and_exact_priority(self):
        self.assertEqual(self.client.get('/api/perfumes',params={'q':'Black Orhid'}).json()['results'],[])
        exact=self.client.get('/api/perfumes',params={'q':'Black Orchid Parfum'}).json()
        self.assertEqual(exact['results'][0]['id'],PARFUM);self.assertEqual(exact['suggestions'],[])
    def test_note_mode_is_not_recommendation_rule(self):
        ratings=[{'perfume_id':i,'rating':r*10} for i,r in json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())]
        before=self.client.post('/api/recommend',json={'ratings':ratings,'required_scent':'none'}).json()
        self.client.get('/api/perfumes',params={'q':'vanilla','mode':'notes'})
        after=self.client.post('/api/recommend',json={'ratings':ratings,'required_scent':'none'}).json()
        self.assertEqual(before,after);self.assertEqual(after['required_scent'],'none')
    def test_before_after(self):
        ratings=[Rating(perfume_id=i,rating=r*10) for i,r in json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())]
        after={c:self.service.recommend(ratings,c) for c in SCENTS}
        self.assertEqual(json.loads((OUT/'recommendations-before.json').read_text()),after)
        for result in after.values():
            scores=[r['score'] for r in result['results']];self.assertEqual(scores,sorted(scores,reverse=True))
        (OUT/'recommendations-after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2))
    def test_invalid_mode(self):self.assertEqual(self.client.get('/api/perfumes?mode=anything&q=rose').status_code,422)

for label,q,mode,kind,value in CASES:
    def method(self,label=label,q=q,mode=mode,kind=kind,value=value):self.check(label,q,mode,kind,value)
    setattr(AdvancedSearchTests,'test_query_'+label,method)

if __name__=='__main__':unittest.main(verbosity=2)
