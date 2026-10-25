# Supplementary implementation provenance

2026-10-23. All new algorithm code here was written directly for this project; no third-party implementation was copied/adapted. There is no borrowed implementation license claim. Existing project dependencies/adapters/metrics are reused unchanged. This stage made no network requests; the following established documentation addresses identify dependencies/concepts, **not freshly visited sources or dataset re-use grants**.

- Python Software Foundation, Python standard library: https://docs.python.org/3/library/ — csv/json/pathlib/hashlib, collections, difflib, html, unittest, ast, inspect, time/sys. PSF license. `difflib.SequenceMatcher` is called as a dependency, not copied.
- NumPy contributors, NumPy reference: https://numpy.org/doc/stable/reference/ — arrays, RNG, linalg.norm/eigh, pairwise distance algebra and vectorized means. Installed NumPy2.3.5, BSD-3-Clause. No source copied.
- Project `src/perfume/data.py`: normalize/identity/fragrantica/laure_catalog reused with original code intact. Project `src/perfume/evaluation.py::evaluate` reused for new kNN only; original metric denominator/relevance rules preserved.
- Existing project `REFERENCES.md`, `data/README.md`: Fragrantica Kaggle / Atrafshan SentimentDrivenCommunityDetection / animalcrossingparty Basenotes / mexwell Parfumo provenance and permission limitations. User explicitly authorized local classroom analysis. No redistribution/hosting grant inferred.
- Local `Team12_Proposal_Perfume_Recommendation.docx`, professor_spec.pdf p2–9, STEP4-1 reports: scope/requirements and historical evidence. No performance target invented.

Mathematical definitions implemented directly: Jaccard intersection/union; overlap-only cosine damped n/(n+5); similarity-weighted neighbor ratings with explicit popularity fallback; Euclidean Lloyd assignments/centroid means with D² seeding; sample silhouette (b−a)/max(a,b); PCA covariance eigenvectors. Methods and parameter choices are explained in the adjacent METHODS_EXPLAINED.md, not attributed to an uninspected external tutorial. kNN recommendations remain exploratory validation-only and fuzzy ratios never certify identity.
