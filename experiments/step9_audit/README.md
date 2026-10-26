# STEP9 감사 소스와 실행 기록

새 학습·튜닝·기존 Validation/Test 재평가를 수행하지 않는 로컬 감사다. 기존 V1/V2/V3 소스는 수정하지 않았다. 필수 보고서4개는 reports/SCENT_MATCH_FINAL_PROJECT_REPORT.md, SCENT_MATCH_PRESENTATION_OUTLINE.md, PROJECT_REPRODUCIBILITY_GUIDE.md, STEP9_FINAL_AUDIT.md다. 이번 단계 source는 직접 작성했으며 외부 구현 복사/차용은 없다. 기존 팀 FrozenService/FastAPI app만 import 재사용했다.

## 최종 상태와 재실행 주의

서비스 기능은 정상이고 Frozen V1 Hybrid 유지다. 그러나 기존 검색 unittest가 web/evidence의 합성 JSON9개를 같은 내용으로 다시 써 timestamp가 갱신됐다. 기존648개 SHA 변경0, 메타데이터670개 중9개 변경이다. strict no-change는 FAIL이며 byte integrity PASS와 구분한다. 원FAIL·실패로그를 보존하고 timestamp를 복원하지 않았다. 기능 테스트 추가 실행은 중단했다. 기존 검색 테스트를 그대로 다시 실행하지 않는다. 후속에는 기존 테스트 OUT을 새 폴더로 patch하는 격리 runner가 먼저 필요하다.

service_checks의 exact 입력순서 JSON 비교도 FAIL을 보존했다. 별도 order_diagnostic에서 추천ID/순서/기타필드 동일, 점수 최대차이2.22e-16, 수치오차1e-12 이내를 확인했다. 코어 점수나 모델을 고치지 않았다. 실패를 PASS로 덮어쓰지 않는다.

## 모듈·함수·파라미터

- integrity.py: sha(path)는 파일 byte SHA256, frozen()은 원 manifest·19개 검증이다. snapshot()은 기존source/private outputs의 hash와 raw/split의 size/mtime, Git상태를 수집한다. save(name,obj)는 새 STEP9 JSON을 배타적으로 생성한다. main()의 인자 before/after는 비교 시점이며 after는 timestamp-only 변경도 FAIL_METADATA_ONLY로 기록한다. 임의 해시 기준 갱신·파일 복원·Git 변경은 하지 않는다.
- service_checks.py: check(name,ok,detail)는 테스트 판정 수집, live(path,body=None,port=8000)는 proxy 없는 loopback HTTP, summarize(values)는 시간의 횟수/평균/최대/중앙값이다. main()은 공개제품에 만든 평점을 주어 정상6×4조건·예외·반복·inference불변을 검증한다. ratings는 임의 점수이고 실사용자 기록이 아니다. mock은 이 프로세스의 객체/함수만 임시 교체하며 파일을 지우지 않는다. 18009 측정 프로세스는 직접 시작한 것만 종료한다. 기존 서버는 종료하지 않는다. 출력 최초 FAIL receipt를 보존해 재실행시 배타적 생성이 거절된다.
- order_diagnostic.py: support는 공개제품+합성점수, without_scores(d)는 비교용으로 score만 제외한 응답 복사다. 모델 파일은 변경하지 않고 점수 최대차이와 ID순서를 기록한다. tolerance=1e-12는 수치동등성 검사이며 기존 exact검사 결과를 교체하지 않는다.
- evidence.py: load(p)/rows(p)는 명시한 aggregate JSON/CSV만 읽는다. save(n,v)는 새증거 생성이다. main()은 저장12행·STEP5선택정책/ridge·STEP8집계·F설정·58fit을 대조한다. 평균은 기존 fold 집계의 산술평균이며 held-out으로 지표를 다시 산출하지 않는다. credential regex는 휴리스틱이고 값은 출력하지 않는다. 원본·개별 평가 결과는 공개검사 후보에 넣지 않았다. 실제 기존 V2 이름과 선택ridge1을 필터하는 초기 구현오류를 고쳤고 실패로그도 보존했다.
- write_documents.py: load(name)는 새 STEP9 JSON, write(name,text)는 신규 MD 배타적 생성, metrics_table(split)은 저장집계 표의 형식화, main()은4문서 생성이다. 최종 무결성 metadata9개 발견 이후의 경고·정정은 새문서에만 추가했다. 현 최종문서가 기준이며 초기 생성기의 문구만으로 무변경 PASS라고 읽지 않는다.

외부 API 참고: Python 표준 pathlib/json/csv/hashlib/statistics/subprocess/resource/unittest.mock/urllib/importlib.metadata와 NumPy의 배열·finite 비교를 사용했다. 공식문서는 https://docs.python.org/3/library/ 와 https://numpy.org/doc/stable/reference/ 이며 이번에 네트워크조회하지 않았다. FastAPI TestClient와 기존 app 계약은 web/METHODS_EXPLAINED.md 및 REFERENCES.md를 따른다. subprocess 인자는 위 루프백 서버/읽기전용Git/Node버전뿐이며 외부업로드는 없다. SHA256은 무결성 식별이지 개인정보 익명화나 별도 서명 증명은 아니다.

실제 명령·환경·모델별 자산 준비는 신규 PROJECT_REPRODUCIBILITY_GUIDE.md에 있다. 새환경 설치/오프라인차단/실기기·프로젝터·전체 접근성·부하검증은 미실시다. 모델·평점·mapping·logs·outputs 및 기존report는 Git에서 제외한다. Git staging/commit/push를 수행하지 않았다.
