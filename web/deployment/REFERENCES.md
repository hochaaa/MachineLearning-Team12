# STEP3-3 참고 문헌 및 차용 범위

확인일: 2026-10-23. 신규 production/검사 코드는 자체 작성했다. 기존 팀의 loader/Fold-in/Hybrid/Knowledge를 호출하며 그 원본은 변경하지 않았다. 외부 예제 구현을 복사하지 않았다. 아래는 공식 API·운영 정책 확인 자료이며 문서의 일반 제공이 데이터 재배포 허가를 뜻하지 않는다. 프로젝트 자체 공개 코드 라이선스는 팀 확인 대상이다. dependency의 라이선스는 기존 web/REFERENCES.md와 각 배포 패키지 라이선스를 유지·별도 검토한다.

| 자료 / 주체 | 사용 범위 | 라이선스·차용 |
|---|---|---|
| [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/) / FastAPI | exact origin/CORSMiddleware API | API 사용, 구현 코드 복사 없음; 라이브러리 배포 시 해당 패키지 license 유지 |
| [FastAPI async](https://fastapi.tiangolo.com/async/) / FastAPI | 동기 endpoint thread 실행 설명 | 문서 참고, 복사 없음 |
| [ASGI HTTP specification](https://asgi.readthedocs.io/en/latest/specs/www.html) / ASGI project | scope/receive/send 및 streamed more_body 규약 | 규약 인터페이스 사용, middleware 자체 작성 |
| [CPython audit hooks](https://docs.python.org/3.12/library/sys.html#sys.addaudithook) / Python Software Foundation | open 이벤트 관찰 | 표준 API 사용, 예제 차용 없음 |
| [Vite env](https://vite.dev/guide/env-and-mode) / Vite | public build-time VITE 변수 설명 | 문서 참고, 복사 없음 |
| [Vercel Vite](https://vercel.com/docs/frameworks/frontend/vite) / Vercel | Root/Build/Output/SPA 설정 | 서비스 문서 참고, 실행 안 함 |
| [Render FastAPI](https://render.com/docs/deploy-fastapi), [Python](https://render.com/docs/python-version), [pricing](https://render.com/pricing), [free](https://render.com/docs/free), [disks](https://render.com/docs/disks), [image](https://render.com/docs/deploying-an-image), [env](https://render.com/docs/configure-environment-variables) / Render | hosting 비교·향후 start/private image 설계 | 정책 참고, 계정/업로드/배포 없음 |
| [Railway plans](https://docs.railway.com/pricing/plans), [pricing](https://railway.com/pricing), [FastAPI](https://docs.railway.com/guides/fastapi), [Railpack Python](https://github.com/railwayapp/railpack/blob/main/docs/src/content/docs/languages/python.md), [network](https://docs.railway.com/networking/public-networking), [serverless](https://docs.railway.com/deployments/serverless) / Railway | hosting/버전/절전 비교 | 정책 참고, 코드 차용 없음 |
| [Railway security notice](https://blog.railway.com/p/security-disclosure-wednesday-october-21st), [status](https://status.railway.com/) / Railway | 10월21일 공지와 10월23일 후속 상태 | 짧은 요약과 링크만, 프로젝트 영향 추정하지 않음 |
| [Fly FastAPI](https://docs.fly.io/python/frameworks/fastapi), [pricing](https://docs.fly.io/about/pricing), [trial](https://docs.fly.io/about/free-trial), [secrets](https://docs.fly.io/apps/secrets), [autostop](https://docs.fly.io/launch/autostop-autostart) / Fly.io | hosting/container·요금·파일·절전 비교 | 정책 참고, 계정/결제/배포 없음 |

이전 데이터 출처·이용권한 조사는 root REFERENCES.md 및 기존 배포 보고서를 그대로 유지한다. 공식 문서/저장소 라이선스만으로 원 사이트/가명 사용자의 개인정보 처리와 파생 모델의 제3자 호스팅 권리를 확정하지 않았다. 현재 권리 상태 NEEDS VERIFICATION이다.
