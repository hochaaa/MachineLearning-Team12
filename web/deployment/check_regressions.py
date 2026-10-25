"""Reuse existing search/API tests, redirecting all output to NEW evidence only."""
from contextlib import ExitStack
import json
import unittest
from unittest.mock import patch
from web.backend.adapter import ROOT
from web.backend import test_search, test_advanced_search, test_note_search, test_brand_search
from web.backend.test_api import ApiTests


def main():
    """No fits, no evaluation datasets; compare old golden responses and synthetic inference."""
    out = ROOT/'web/evidence/safe-deployment/regression'
    out.mkdir(parents=True, exist_ok=True)
    for name in ('name-before.json', 'notes-before.json', 'recommendations-before.json'):
        (out/name).write_bytes((ROOT/'web/evidence/brand-search'/name).read_bytes())
    (out/'exact-before.json').write_bytes((ROOT/'web/evidence/note-search/exact-before.json').read_bytes())
    modules = (test_search, test_advanced_search, test_note_search, test_brand_search)
    with ExitStack() as stack:
        for module in modules: stack.enter_context(patch.object(module, 'OUT', out))
        classes = (test_brand_search.BrandSearchTests, test_note_search.NoteSearchTests,
                   test_advanced_search.AdvancedSearchTests, test_search.SearchTests, ApiTests)
        result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in classes))
    summary = {'tests':result.testsRun, 'pass':result.testsRun-len(result.errors)-len(result.failures)-len(result.skipped),
               'fail':len(result.failures), 'errors':len(result.errors), 'not_supported':len(result.skipped),
               'skipped':[{'test':str(t), 'reason':msg} for t,msg in result.skipped]}
    (out/'test-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__': raise SystemExit(main())
