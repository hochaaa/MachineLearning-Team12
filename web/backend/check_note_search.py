"""Run note/search/API regressions, redirect earlier test evidence to this stage only."""
import json
import unittest
from unittest.mock import patch
from .adapter import ROOT
from . import test_search,test_advanced_search
from .test_api import ApiTests
from .test_note_search import NoteSearchTests
out=ROOT/'web/evidence/note-search'
legacy=out/'legacy';legacy.mkdir(exist_ok=True)
(legacy/'recommendations-before.json').write_bytes((out/'recommendations-before.json').read_bytes())
with patch.object(test_search,'OUT',legacy),patch.object(test_advanced_search,'OUT',legacy):
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (NoteSearchTests,test_advanced_search.AdvancedSearchTests,test_search.SearchTests,ApiTests))
    r=unittest.TextTestRunner(verbosity=2).run(suite)
summary={'tests':r.testsRun,'pass':r.testsRun-len(r.failures)-len(r.errors)-len(r.skipped),'fail':len(r.failures),'errors':len(r.errors),'not_supported':len(r.skipped),'skipped':[{'test':str(t),'reason':msg} for t,msg in r.skipped]}
(out/'test-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
raise SystemExit(0 if r.wasSuccessful() else 1)
