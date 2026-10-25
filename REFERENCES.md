# Sources and code provenance

Access date: 2026-10-22. No third-party implementation source was copied/adapted into the recommender; algorithms were implemented directly for this project. Mathematical concepts and library dependencies still require references. If later code is adapted, cite its author, exact URL, license and scope beside the code and here.

| Source | Author / permission observation | Use |
|---|---|---|
| professor_spec.pdf, pp2–9 | Ok-Ran Jeong, Fall 2026 | Written requirements, local original verified with pypdf |
| Team12_Proposal_Perfume_Recommendation.docx | Team 12 supplied by user | Planned design, not measurement evidence |
| https://github.com/Kalashi-Saed-Collaborations/SentimentDrivenCommunityDetection | Kamand Kalashi, Sajjad Saed, Babak Teimourpour. README says academic/noncommercial datasets and MIT project license, both recorded | Atrafshan dataset provenance, no implementation copied; 0 semantics not documented in inspected README |
| https://github.com/Kalashi-Saed-Collaborations/SentimentDrivenCommunityDetection/blob/main/LICENSE | Copyright 2025 Kalashi-Saed-Collaborations, MIT | License observation, no inference that all upstream site permissions are granted |
| https://doi.org/10.1007/s41109-025-00757-0 | Kalashi, Saed, Teimourpour, Applied Network Science 11, article 13 (2026), published Dec 7 2025 | Original data collection and rating/sentiment description, not proof of zero semantics |
| https://www.kaggle.com/datasets/olgagmiufana1/fragrantica-com-fragrance-dataset | olgagmiufana1; page opened but content/license unavailable to web tool | Fragrantica provenance, local rights confirmed by user |
| https://github.com/animalcrossingparty/perfume | animalcrossingparty, project README inspected; no dataset license independently established | Laure/Basenotes provenance, not Team 12 GitHub URL |
| https://www.kaggle.com/datasets/mexwell/parfumo-fragrance-dataset | mexwell; page opened but content/license unavailable to web tool | Parfumo source address corroborated by page title; exact local file lineage not independently verified |
| https://numpy.org/doc/ | NumPy contributors, BSD-3-Clause | Dependency for arrays, RNG, ridge solve; no code copied |
| https://docs.python.org/3/library/ | Python Software Foundation, PSF license | Standard library, no code copied |
| https://www.reportlab.com/docs/reportlab-userguide.pdf | ReportLab contributors, dependency license to retain with distribution | Measured bar charts, no external plot data |
| https://sharp.pixelplumbing.com/ | Lovell Fuller and contributors, Apache-2.0 | SVG rasterization only |

Original site terms: Fragrantica terms fetch failed; attempted Basenotes terms URL failed; attempted Parfumo terms URL returned 404; Atrafshan homepage opened but usage terms not established. These failures are evidence limits, not legal conclusions. User explicitly confirmed use permission for all four datasets on 2026-10-22. Local analysis/training proceeded on that confirmation. Raw data redistribution and public upload remain unauthorized and unperformed.

Original professor PDF was extracted with pypdf, proposal text with standard-library OOXML extraction. Word report generation uses python-docx 1.2.0 and runtime renderer; presentation generation uses bundled @oai/artifact-tool if generated. No fabricated references, GitHub URLs or individual team contributions.

Artifact authoring API pattern: OpenAI bundled presentations skill `artifact_tool_docs/API_QUICK_START.md` and `references/finalization.md`, accessed 2026-10-22. Scope: editable slide/chart creation and validation in `scripts/build_deck.mjs` only. The algorithm implementation contains no borrowed recommender code. Library usage documentation is not a dataset license grant.

Follow-up 2026-10-22: biased MF and mean-centered/liked profiles are original implementations documented in METHODS_EXPLAINED.md; no copied third-party model code. Attempts to inspect animalcrossingparty/perfume backend/collection code via web and GitHub connector failed (cache miss / transport closed). Consequently, external 0..9 scale mapping is explicitly an ordinal evaluation assumption, not a verified equivalence of rating semantics or a quote from source code. No private raw dataset was transmitted in those read-only source lookups.
