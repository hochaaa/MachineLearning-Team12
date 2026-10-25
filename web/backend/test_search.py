"""STEP3-1 API search assertions against exact, existing catalog IDs (no training)."""
import json
from pathlib import Path
import unittest
from fastapi.testclient import TestClient
from .app import app, Rating
from .adapter import SCENTS, ROOT
from .search import CatalogSearch, normalize_search

ELIXIR='https://www.fragrantica.com/perfume/dior/sauvage-elixir-68415.html'
BLACK='https://www.fragrantica.com/perfume/tom-ford/black-orchid-1018.html'
PARFUM='https://www.fragrantica.com/perfume/tom-ford/black-orchid-parfum-62199.html'
HOMME='https://www.fragrantica.com/perfume/dior/dior-homme-2020-58714.html'
BLEU='https://www.fragrantica.com/perfume/chanel/bleu-de-chanel-parfum-49912.html'
OUT=ROOT/'web/evidence/search-stage31'
CASES=[
 ('brand_full','Dior Sauvage Elixir',ELIXIR),('name','Sauvage Elixir',ELIXIR),
 ('brand_partial','dior sauvage',ELIXIR),('brand_in_name','dior homme 2020',HOMME),
 ('tom_ford','Tom Ford Black Orchid',BLACK),('black','Black Orchid',BLACK),
 ('black_parfum','Black Orchid Parfum',PARFUM),('bleu','Bleu de Chanel Parfum',BLEU),
 ('case','DIOR SAUVAGE ELIXIR',ELIXIR),('spaces','dior   sauvage   elixir',ELIXIR),
 ('hyphens','dior-sauvage-elixir',ELIXIR),('trailing','Sauvage Elixir ',ELIXIR),
 ('reverse','sauvage dior',ELIXIR),('token_subset','tom ford orchid',BLACK),
 ('reverse_name','orchid black',BLACK),('reverse_brand','bleu chanel',BLEU),
 ('empty','',None),('whitespace','    ',None),('unknown_brand','zzzzNonexistentBrand',None),
 ('unknown_perfume','zzzzNonexistentPerfume',None),('punctuation_only','!@#$% --',None),
 ('long','a'*101,'422'),('one_char','a','many'),
 ('unicode_width','ＤＩＯＲ ＳＡＵＶＡＧＥ ＥＬＩＸＩＲ',ELIXIR),
 ('unicode_accent','Díor Sauvagé Élixir',ELIXIR),('unicode_korean','없는향수',None),
 ('punctuation','Dior / Sauvage, Elixir!',ELIXIR),('token_subset_elixir','dior elixir',ELIXIR)
]

class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app);cls.client.__enter__();cls.s=app.state.service;cls.observed=[]
    @classmethod
    def tearDownClass(cls):
        OUT.mkdir(exist_ok=True)
        (OUT/'search-cases.json').write_text(json.dumps(cls.observed,ensure_ascii=False,indent=2))
        cls.client.__exit__(None,None,None)
    def check_case(self,key,query,expected):
        response=self.client.get('/api/perfumes',params={'q':query})
        record={'case':key,'query':query,'expected':expected,'http_status':response.status_code,'status':'FAIL'}
        try:
            if expected=='422':
                self.assertEqual(response.status_code,422)
                record['returned_ids']=[]
            else:
                self.assertEqual(response.status_code,200)
                results=response.json()['results'];ids=[r['id'] for r in results]
                record['returned_ids']=ids;record['returned_names']=[r['name'] for r in results]
                self.assertLessEqual(len(ids),10);self.assertEqual(len(ids),len(set(ids)))
                self.assertTrue(set(ids)<=self.s.allowed)
                self.assertEqual(ids,[r['id'] for r in self.client.get('/api/perfumes',params={'q':query}).json()['results']])
                if expected is None: self.assertEqual(ids,[])
                elif expected=='many':
                    self.assertGreater(len(self.s.search_index.ranked(query,limit=479)),10)
                    self.assertEqual(len(ids),10)
                elif expected not in self.s.allowed:
                    record['status']='NOT SUPPORTED';self.skipTest('Expected item absent from frozen 479')
                else: self.assertEqual(ids[0],expected)
            record['status']='PASS'
        finally: self.observed.append(record)
    def test_identical_target_and_distinct_versions(self):
        a=self.s.search('Dior Sauvage Elixir')[0]['id'];b=self.s.search('Sauvage Elixir')[0]['id']
        self.assertEqual(a,b);self.assertNotEqual(BLACK,PARFUM)
        self.assertEqual([r['id'] for r in self.s.search('Black Orchid')],[BLACK,PARFUM])
    def test_stateless_selected_perfume_search(self):
        before=self.s.search('Sauvage Elixir')
        self.client.post('/api/recommend',json={'ratings':[{'perfume_id':ELIXIR,'rating':9}]})
        self.assertEqual(before,self.s.search('Sauvage Elixir'))
    def test_regression_before_after(self):
        support=json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())
        ratings=[Rating(perfume_id=i,rating=r*10) for i,r in support]
        after={c:self.s.recommend(ratings,c) for c in SCENTS}
        before=json.loads((OUT/'recommendations-before.json').read_text())
        self.assertEqual(before,after)
        (OUT/'recommendations-after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2))
    def test_full_ranking_then_limit(self):
        # Exact target deliberately occurs after >10 weaker candidates.
        catalog={f'weak{i}':{'name':f'rose extra {i}','brand':'brand'} for i in range(15)}
        catalog['exact']={'name':'rose','brand':'brand'}
        index=CatalogSearch(list(catalog),catalog)
        self.assertEqual(index.ranked('rose')[0],'exact');self.assertEqual(len(index.ranked('rose')),10)
        self.assertEqual(index.ranked('rose'),CatalogSearch(list(reversed(catalog)),catalog).ranked('rose'))
    def test_display_dedup_only(self):
        catalog={'x':{'name':'Dior Homme','brand':'Dior'}}
        candidates=['x','x'];index=CatalogSearch(candidates,catalog)
        self.assertEqual(index.ranked('dior homme'),['x']);self.assertEqual(candidates,['x','x'])
        self.assertEqual(index.entries[0][3],'dior homme')
    def test_normalization_and_no_or_match(self):
        self.assertEqual(normalize_search('  DÍOR--ＳＡＵＶＡＧＥ / ELIXIR '),'dior sauvage elixir')
        self.assertEqual(self.s.search('dior zzzznonexistent'),[])

for key,query,expected in CASES:
    def method(self,key=key,query=query,expected=expected):self.check_case(key,query,expected)
    setattr(SearchTests,'test_query_'+key,method)

if __name__=='__main__':unittest.main(verbosity=2)
