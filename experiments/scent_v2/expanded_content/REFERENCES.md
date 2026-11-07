# References and reuse

Accessed 2026-10-30. Implementation is project-local, with no external algorithm source copied.

- Scento, https://github.com/Scento-com/perfume-dataset/tree/58da85556a4bb42a7d56279d66fbec4dbf42cc4a — independently licensed metadata, CC BY 4.0. Attribution: Scento — https://www.scento.com/perfume-database. Changes: subset selection, literal note normalization, frozen-IDF projection. Files and SHA256: output `licensed_source/provenance.json`. Descriptions, popularity, family and seasons not used. No claim of endorsement.
- Creative Commons, https://creativecommons.org/licenses/by/4.0/legalcode.en — license scope/attribution review, no implementation copied.
- Existing project `src/perfume/models.py`, `src/perfume/metrics.py`, `experiments/scent_v2/recommend.py` — Content profile/cosine, ranking and metric conventions reused for regression. Original files unchanged; not third-party borrowed code.
- Existing project V2-16 `real_rating_retraining/audit.py` and V2-17 `perfume_catalog_expansion/build.py` — original CSV parsing and product-only inventory helpers. V2-17 note/vector payloads never loaded.
- Python standard library `argparse`, `ast`, `csv`, `hashlib`, `json`, `pathlib`, `statistics`, `unittest`, `unittest.mock` — command-line/data/hash/test infrastructure; no new installation.
