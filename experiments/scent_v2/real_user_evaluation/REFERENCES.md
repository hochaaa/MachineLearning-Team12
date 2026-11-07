# V2-21 reuse and references

2026-10-30. No new third-party algorithm source copied or external metadata fetched.

- Local Team12 V2-14 `real_user_dataset/storage.py`: Store auth/CSRF/role ledger/SQLite lock/CSV atomic writes. New root only; no original DB migrations.
- Local V2-14 `validation.py`, `catalog.py`, `app.py`, `static/style.css`: rating/.5/experience validators, literal catalog search, loopback HTTP/JSON/headers, responsive styling reused unchanged.
- Local `deployment/standalone_v1/runtime_loader.py:StandaloneService` and `deployment/final_v1/config.py:inspect_assets`: actual Frozen479 inference and pinned runtime integrity. Existing recommendation arithmetic and model files unchanged.
- V2-18 Scento snapshot commit `58da85556a4bb42a7d56279d66fbec4dbf42cc4a`, CC BY4.0, Scento — https://www.scento.com/perfume-database, https://github.com/Scento-com/perfume-dataset/tree/58da85556a4bb42a7d56279d66fbec4dbf42cc4a: only the extra legacy85 product-identity diagnosis reads the existing licensed snapshot. No new note projection or model scoring; source attribution/version/hashes retained. Original V2-17 manufacturer notes/accords/vectors unused.
- Python standard library sqlite3, secrets, hashlib, datetime, http.server, json, csv, pathlib, urllib, unittest/mock: new local storage/auth/deletion/testing infrastructure; no installation.
- User V2-21 operational decision: new collection retention2027-02-28, hash-only one-time deletion code, one data manager access. User's subsequent clarification: original12-person85-rating data keep its original project consent and is excluded from V2-21 retroactive retention/deletion. No team member identity invented.
- Local `vercel:verification` skill workflow used for UI→API→data→Frozen result checks; no Vercel deployment performed.
