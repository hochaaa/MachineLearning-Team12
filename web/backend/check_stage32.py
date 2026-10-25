"""Run search/API regressions without modifying earlier evidence directories."""
import json
import unittest
from unittest.mock import patch
from .adapter import ROOT
from . import test_search
from .test_advanced_search import AdvancedSearchTests
from .test_api import ApiTests

out=ROOT/'web/evidence/search-stage32'
legacy=out/'legacy-search';legacy.mkdir(exist_ok=True)
(legacy/'recommendations-before.json').write_bytes((out/'recommendations-before.json').read_bytes())
with patch.object(test_search,'OUT',legacy):
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (AdvancedSearchTests,test_search.SearchTests,ApiTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
summary={'tests':result.testsRun,'pass':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
         'fail':len(result.failures),'error':len(result.errors),'not_supported':len(result.skipped),
         'skipped':[{'test':str(t),'reason':r} for t,r in result.skipped]}
(out/'test-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
