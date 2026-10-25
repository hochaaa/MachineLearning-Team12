"""Run this stage plus previous search regressions without overwriting old evidence."""
import json
import unittest
from unittest.mock import patch
from .adapter import ROOT
from . import test_search,test_advanced_search,test_note_search
from .test_api import ApiTests
from .test_brand_search import BrandSearchTests
out=ROOT/'web/evidence/brand-search';legacy=out/'legacy';legacy.mkdir(exist_ok=True)
(legacy/'recommendations-before.json').write_bytes((out/'recommendations-before.json').read_bytes())
(legacy/'exact-before.json').write_bytes((ROOT/'web/evidence/note-search/exact-before.json').read_bytes())
with patch.object(test_search,'OUT',legacy),patch.object(test_advanced_search,'OUT',legacy),patch.object(test_note_search,'OUT',legacy):
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (BrandSearchTests,test_note_search.NoteSearchTests,test_advanced_search.AdvancedSearchTests,test_search.SearchTests,ApiTests))
    r=unittest.TextTestRunner(verbosity=2).run(suite)
summary={'tests':r.testsRun,'pass':r.testsRun-len(r.failures)-len(r.errors)-len(r.skipped),'fail':len(r.failures),'errors':len(r.errors),'not_supported':len(r.skipped),'skipped':[{'test':str(t),'reason':msg} for t,msg in r.skipped]}
(out/'test-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
raise SystemExit(0 if r.wasSuccessful() else 1)
