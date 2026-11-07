# V2-22 API 요약

- `Engine()`는 V2-21 FrozenEngine과 V2-18 승인18개 token을 고정IDF로 재사용한다. fit 없음.
- `recommend(support, mode, exclude)`의support는고유5개(raw0~10/.5점),exclude는알려진상품ID만. oldMFsupport만기존ridge에전달한다. 새itemfactor없음.
- `percentiles(scores)`는유한ID→score를내림차순정렬해동점의평균순위를[0,1]로변환한다. parameter/config 고정,모집단통계나정답학습아님.
- `search(query)`는기존V2-14token검색+화면전용브랜드alias. 제품identity매칭에는사용하지않는다.
- `Store(root,engine,policy,fixture)`는신규DB에서V2-21클래스재사용. 새schema의unique(user,model_version)으로모드별immutable세션을저장한다. state/token/csrf/feedback/delete/export/retention은상속한다.
- `recommend_mode(token,csrf,mode)`는원래pre평점에서hash Support5,기지상품제외,모드별snapshot·비교확률을기록한다. `analyses()`는모드별세션을독립인원으로세지않는다.
- `prepare --csv`는기존85의제품식별만별도표로출력한다. `licensed_match`의정확명/농도규칙을유지하며active497밖일치와사용가능일치를구분한다.
- HTTP `Handler`는V2-21host/origin/CSRF검증·동의·삭제·피드백route를재사용하고새mode/search/static만override한다. `Server(port,store)`는loopback only.
- NumPy/SQLite/hashlib/json/csv/pathlib/HTTPServer는기존의존성그대로. 테스트는실제모델+합성입력/임시DB이며학습·평가정답이아니다.

출처: 프로젝트V2-18/models.py, V2-21/engine.py·storage.py·app.py·static, V2-14검색/CSS, web/backend/advanced_search.py의기존brandalias. 새외부코드차용없음. 신규18특징은Scento(CC BY4.0), https://www.scento.com/perfume-database , commit58da85556a4bb42a7d56279d66fbec4dbf42cc4a;변경내용은기존Notes정규화·고정IDF투영그대로,새수집없음. 모델튜닝·재배포허가로확대해석하지않음.
