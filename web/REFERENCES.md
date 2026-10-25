# 웹 구현 참고 및 출처

확인일 2026-10-22. 외부 예제 소스 전체를 복사하지 않고 아래 공개 API를 사용하여 자체 작성했다. 기존 루트 REFERENCES.md를 덮어쓰지 않았다.

| 출처 | 범위 | 권리/구분 |
|---|---|---|
| 프로젝트 `scripts/demo_frozen.py`, `src/perfume/models.py`, `src/perfume/frozen.py` | adapter 호출 순서 및 직접 재사용 함수 | 기존 Team12 코드, 원본 변경 없음 |
| [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/) / Sebastián Ramírez 및 contributors | CORSMiddleware 사용 | FastAPI MIT; 인접 주석 포함 |
| [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/) | 시작 시 모델1회 로딩 | FastAPI MIT |
| [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/) | field/model validator, 숫자 검증 | Pydantic MIT |
| [React](https://react.dev/reference/react) / Meta 및 contributors | 컴포넌트와 hooks | React MIT |
| [Vite](https://vite.dev/guide/) / Vite contributors | dev/build/env | Vite MIT |
| [Tailwind Vite](https://tailwindcss.com/docs/installation/using-vite) / Tailwind Labs | Tailwind4 plugin | Tailwind CSS MIT |
| [TypeScript](https://www.typescriptlang.org/docs/) / Microsoft | 정적 타입 | Apache-2.0 |
| [Uvicorn](https://www.uvicorn.org/settings/) / contributors | ASGI 실행 | BSD-3-Clause |
| [HTTPX](https://www.python-httpx.org/) / Encode | TestClient HTTP 의존성 | BSD-3-Clause |

배포 가격·제한 출처는 `reports/WEB_DEPLOYMENT_GUIDE.md`에 별도 기재한다. 데이터 로컬 사용 허용을 공개 재배포 권리로 해석하지 않았다.
