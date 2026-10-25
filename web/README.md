# SCENT MATCH · 로컬 웹 MVP

실행은 프로젝트 루트에서 서로 다른 터미널로 진행합니다.

```sh
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B -m uvicorn web.backend.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

```sh
npm --prefix web/frontend run dev
```

http://127.0.0.1:5173/ 접속. 설치·재현·배포 제한은 `reports/WEB_DEPLOYMENT_GUIDE.md`, 구현·검증은 `reports/WEB_MVP_IMPLEMENTATION.md` 참조.

모델 학습/평가를 하지 않습니다. 기존 freeze·후보479·alpha.25·규칙을 그대로 사용합니다. 검색과 support 입력을 고정 후보479개로 제한합니다. 평점은 메모리 요청만 사용하며 DB·계정·영구저장 기능이 없습니다.

`web/backend/.venv`, `web/frontend/node_modules`, `dist`, 전체 데이터/모델/학습 이력은 공개 저장소에 올리지 마세요. frontend 코드와 backend 모델 자산을 구분해야 합니다. 이 작업에서는 배포·commit/push를 하지 않았습니다.
