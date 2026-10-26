# Synthetic catalog provenance

작성일2026-10-26. 이 자료는 `backend/generate_data.py`의 코드 상수와 random.Random(1612)만으로 새로 생성했다. 실행 입력 파일·외부 요청·실제 사용자·평점 데이터가 없다.10일반 향 계열마다8개, 총80개다. ID DEMO-001~080, 가상 브랜드 Imaginary Atelier 번호, 가상 이름 Invented 계열 Study 번호와 설명을 사용한다. notes/accords 조합 서명80개는 모두 다르다.

노트는 일반 도메인 어휘이며 원자료에서 추출한 사전이 아니다. Top/Middle/Base는 이 데모의 임의 분류로 실제 제품 특성이나 조향 품질 주장과 무관하다. season/occasion/intensity/longevity/price·이미지·실사용자 평점·ID·설명 리뷰는 포함하지 않는다. 노트/어코드 합성 조합이 실제 어느 제품과도 우연히 겹치지 않는다는 전세계 검증은 하지 않았으며, 원자료를 읽어 비교하지 않았다.

재현 명령은 프로젝트 루트에서 `python -B -m demo.backend.generate_data`다. 이 명령은 오직 Demo JSON을 덮어쓰므로 필요할 때만 실행한다. 서버와 설치는 이미 제공된 합성JSON만 사용한다. 생성 코드에 원CSV/런타임/외부 사이트 경로 및 기존 모델 import가 없으며 독립 source-only Clone에서 실행된다.

개인정보·원본 레코드/기존 모델 파라미터를 복제한 근거는 발견하지 않았다. 자체 생성 자료의 프로젝트 내 공유 준비 대상으로 분류하되, 공개 라이선스 선택·공유 Git 승인과 의존성 고지는 별도 절차다. Fragrantica/Atrafshan 파생 자산의 기존HOLD는 그대로 유지한다.
