# 제출용 소스 검증

2026-11-07, 별도 제출용 복사본에서 확인했습니다.

- 핵심 ML 합성 단위 테스트 19개 통과
- 설치·무결성·실행 관리 단위 테스트 27개 통과
- 검색 후보 탐색 테스트 5개 통과
- FastAPI TestClient: health·검색 200, none/woody/floral/rose/citrus/amber/vanilla의 합성 입력 추천 7조건 통과
- 추천은 조건별 5개, 입력 향수 제외, 조건 충족 확인
- 최소 모델 자산 5개 및 보호 소스 11개 해시 검사 PASS
- 추가 Python 소스 구문 검사 PASS, 검토 범위의 비밀키 패턴·개인 컴퓨터 절대경로 미발견

설치 관리 테스트 중 기존 factory 테스트는 확장 route 추가 전 구조를 가정해 import mock 오류가 발생했습니다. 실제 extension을 먼저 import하고 factory 위임과 두 확장 함수의 호출을 검증하도록 수정한 뒤 27개 모두 통과했습니다. 서비스 모델·보호 소스·자산은 변경하지 않았습니다.

기존 로컬 Python 의존성 환경에서 검사한 결과입니다. 새 PC 전체 설치·Windows·물리적 발표장 브라우저 동작을 이번 작업에서 새로 검증한 것은 아닙니다. 실제 데이터 재학습·튜닝·최종 Validation/Internal/External Test는 재실행하지 않았습니다.
