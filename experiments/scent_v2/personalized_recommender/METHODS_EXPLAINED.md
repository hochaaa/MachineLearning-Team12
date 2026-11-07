# V2-23 짧은 구현 설명

- `preferences(vectors,support,candidates)`: 기존L2unit sparse특징을그대로사용,고유5입력raw0~10/.5검증,선호/비선호그룹의mean(weight*cosine)을독립계산한다. 기존Content를가산하지않는다. `cosine(a,b)`는기존unit벡터내적이다.
- `rerank(values,vectors,k=5,diversity=True)`:top30내에서greedy λ*relevance−(1−λ)*maxcos. 매선택bestRemaining−.05이상후보만선택해선호손실을제한한다. 동점ID순,최소k후보검증,같은item재선택없음.
- `Engine.recommend(support,mode,exclude)`:기존세모드는부모V2-22호출후설명만추가;새2variant는signedContent/MMR. `explain(item,support,parts,trace)`는실제overlap token·유사도와실제감점만문구화한다. LLM없음.
- `Store.recommend_mode(token,csrf,mode)`:새variant만별도version으로세션저장하고나머지는V2-22상속. cookie/CSRF/동의/역할/삭제/CSV/retention재사용,새root만접근한다. 임계값/다양성변경시version변경필수.
- HTTPHandler/Server는V2-22보안/검색/피드백/CSS를상속하고새정적UI·모드목록·개인화호출만override한다. port는loopback,fixture는임시DB.
- 새외부코드차용없음. MMR형태의내적중복penalty는요청명세에따라직접구현. 기존V2-18특징은Scento(CC BY4.0), https://www.scento.com/perfume-database , commit58da85556a4bb42a7d56279d66fbec4dbf42cc4a를그대로사용하며새metadata수집없음. Python json/math/hashlib/SQLite 및기존벡터/동결모델모듈재사용,새패키지없음.
