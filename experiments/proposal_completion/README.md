# Proposal completion: isolated post-freeze supplements

기존 동결 ML/웹/CLI/정답/원본 데이터/보고서를 변경하지 않는다. 설치·다운로드·네트워크 불필요. 기존 `web/backend/.venv` Python3.12.14 + NumPy2.3.5 사용. `src`에서 normalize/identity/fragrantica와 metric 정의만 import한다. MF.fit/score/fold_in은 호출하지 않는다. 새 kNN만 validation 평가, 군집화는 metadata-only이다.

프로젝트 루트에서 각각 실행:

```sh
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/proposal_completion/parfumo_crosscheck.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/proposal_completion/knn_baselines.py
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 web/backend/.venv/bin/python -B experiments/proposal_completion/kmeans_analysis.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/proposal_completion/fuzzy_match_audit.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/proposal_completion/supplementary_metrics.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B -m unittest discover -s experiments/proposal_completion/tests -v
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/proposal_completion/build_reports.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/proposal_completion/integrity.py after
```

명령은 `outputs/proposal_completion/`의 **이번 단계 새 결과만** 다시 쓴다. 최상위 기존 `outputs/final`, `validation`, `improvement`에 쓰는 기능은 없다. `integrity.py before`는 최초 baseline 생성에 이미 사용했고 기존 baseline 덮어쓰기를 거부한다. 이후 재현에서도 `after`로 현재 파일 불변성을 확인한다. 결과가 저장되어 있으므로 최종 발표 준비에 불필요한 재실행을 요구하지 않는다.

주요 설정:

- Parfumo: 기존 brand/name normalize exact, 양쪽unique, explicit version/year충돌 제외; synonym 없음, both-nonempty Jaccard. 농도 미확인 연결은 불확실성 유지.
- kNN: train330/538/1805, val168(긍정137), pool479, overlap-only cosine, min_common2, shrink5, neighbor5/10/20, fallback=train log popularity. 기존 평가 사용자에 대한 탐색, new-user 실제 성능 N/A. Test 정답 읽지 않음.
- K-means: 전체24063개, top5 accord 84차원 multi-hot, k3/4/5/6/8, seed12(+초기화run1/2), n_init3/max_iter100/tol1e-5, silhouette fixed800. 모델 변경 아님.
- Fuzzy: 기존exact 승인은 제외, same-brand only, difflib phrase/token-sort max, .72/.94, gap .08, version/year/tie guards. 실제 수동검증0/반영0.
- Supplementary: 기존 Mean/errors/CSR 복사; zero 의미 유지; 개발후보season/price가용성만 감사.

`*_run.json`에 명령·시간·Python/NumPy·seed·입력 해시, `before_sha256.json`/`integrity_after.json`에 원본 보존 근거가 있다. 일부 최초 metadata hash는 실행 후 추가되었으며 각 JSON에 표시했다. 최종 코드 전체 hash는 `provenance.json`에 별도 기록한다. `development_initial/`은 이 단계 개발 중 첫 결과 보존이며 최종 지표는 최상위CSV만 인용한다.

새 결과에는 aggregate·공개 상품명만 저장한다. train/val user ID와 개별 평점은 메모리에서만 사용한다. outputs/sources에도 원본 개인 평점·대형 모델을 복제하지 않는다. 파일명/해시 목록은 원본 데이터 내용이 아니다. 보고서7개는 `reports/PROPOSAL_COMPLETION_SUMMARY.md`에서 연결된다. 기존 교수 요구사항·원본 제안서나 과거 보고서의 상태를 소급 변경하지 않는다.

패키지/출처와 새 함수·클래스·메서드 파라미터는 이 디렉터리 `METHODS_EXPLAINED.md`, `REFERENCES.md`를 참고한다. Git/서버/배포 기능은 없다.

## 최종 정리 시 무결성 예외

2026-10-25 전체baseline검사에서 Finder메타데이터2개와기존demo.log의변경을발견해exit1로중단했다. protected19/manifest/데이터/평가/소스는불변. 원인UNKNOWN, 복원/새baseline/재실험안함. 현재stage보고서는reports/PROPOSAL_COMPLETION_FINALIZATION.md와integrity_classification.json을최종근거로한다. 위실행명령은재현참고이며이후자동재실행하지않았다.
