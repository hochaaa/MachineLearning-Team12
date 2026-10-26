# Demo references and provenance

확인일 2026-10-26. 외부 구현 코드의 복사/번역/적응은 하지 않았다. 수식과 데모 코드는 신규 작성했다. 사용자 허용 범위의 내부 UI 흐름·입력 계약은 기존 `web/frontend/src/main.tsx`, `web/backend/app.py`, STEP15 설계를 참고했으며 해당 파일들은 수정하지 않았다. 원본 메타데이터·브랜드 alias·이미지·벡터는 재사용하지 않았다.

- Python Software Foundation, [math 공식 문서](https://docs.python.org/3/library/math.html): log/sqrt/isfinite API 설명 확인. 실제 실행 Python3.12.0이며 웹 latest 문서와 버전은 다를 수 있다. Python stdlib 사용(PSF license); 외부 소스 코드 복사 없음.
- FastAPI 공식 [CORS](https://fastapi.tiangolo.com/tutorial/cors/): middleware 옵션 확인. FastAPI(MIT), Starlette(BSD-3-Clause), Uvicorn(BSD-3-Clause), Pydantic(MIT), HTTPX(BSD-3-Clause)를 패키지로 사용; 버전은requirements-lock.txt. 예제 코드를 복사하지 않고 독립 app 작성.
- React 공식 [useEffect](https://react.dev/reference/react/useEffect): effect/cleanup API 확인. React/React DOM(MIT)를 npm 의존성으로 사용.
- Vite 공식 [guide](https://vite.dev/guide/): dev/build 도구 설명 확인. 실제 설치Vite7.2.2이며 현재 웹문서의 최신 버전과 구분. Vite(MIT), TypeScript(Apache-2.0), React type packages(MIT). 실제 배포 시 설치 패키지의 LICENSE/NOTICE를 유지한다.

의존성 패키지 전체는 pip/npm lock에 기록한다. 이 문서는 제3자 데이터 라이선스가 아니다. 신규 자체 합성 자료의 생성 출처는 DATA_PROVENANCE.md이며, 프로젝트 자체 코드·자료에 적용할 공개 라이선스는 팀 확인 전 TBD다. 교수님의 수업 외 기법 인정 여부도 별도 확인한다.
