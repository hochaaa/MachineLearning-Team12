# V2-16 근거 및 재사용

코드는 직접 작성했다. 외부데이터/외부소스다운로드/차용알고리즘 구현 없음. 사용자의 실제 경험·동의 확인은 대화상 사용자 진술이며 개별 서면 동의서를 생성한 것이 아니다.

- 기존Content/MF/Hybrid: `src/perfume/models.py`, `src/perfume/improvements.py`, 수정하지 않음.
- 경계 parser 재사용: `experiments/scent_v2/synthetic_data/boundary.py`, 함수 import만, 합성 generator 미호출.
- 집계 재사용: `experiments/scent_v2/external_real_data/quality_report.py`, 기존 strictTrain만 집계, 변경 없음.
- 합성 지표 검사: `experiments/scent_v2/evaluate.py`; 실제 held-out 자료 사용 없음.
- 역사적 표: `outputs/scent_v2/*/REPORT.md`, `accuracy.csv`, `inner_accuracy_pooled.csv`, `inner_results.csv`, `model_comparison.csv`, `summary.json`, `selection_locked.json`의 집계/채택 기록. 신규 문서의 experiment_history.csv는 원문 경로/정책/phase를 함께 기록한다.
- 원본CSV: 사용자 제공 `scent-ratings.csv`; 원본해시·집계는 data_validation.json. 라이선스/개인평점 재배포 허가를 만들지 않았다.
- Python API: https://docs.python.org/3/library/csv.html ; https://docs.python.org/3/library/hashlib.html ; https://docs.python.org/3/library/hmac.html ; https://docs.python.org/3/library/statistics.html ; https://docs.python.org/3/library/unittest.mock.html . 표준API 사용이며 문서 코드를 복사하지 않았다.

새 웹자료나상품Notes를찾아외부로개인평점을보낸적없다. 이번작업에는웹외부전송이없으므로새상업데이터권한을추정할필요가없다.
