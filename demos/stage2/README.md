# STEP 2 발표 전용 합성 입력

두 JSON의 향수 URL은 현재 로컬 Fragrantica 카탈로그의 공개 상품 메타데이터에서 선택했다. 평점은 **실제 사용자의 평가가 아닌 별도로 정한 합성 예시**다. Atrafshan 개인 이력이나 Validation/Internal Test/Basenotes 정답에서 복사하지 않았다. 향수 이름/브랜드는 기존 메타데이터 표기를 그대로 사용한다.

- `synthetic_woody.json`: Sauvage Elixir .9, Bleu de Chanel Parfum .8, Black Orchid .2
- `synthetic_floral.json`: La Vie Est Belle .9, Jour d'Hermes .8, Black Orchid Parfum .85

모든 입력은 `[Fragrantica URL, 0..1 숫자]` 행의 JSON 배열이다. 이름 검색은 지원하지 않는다. 추천 후보479개와 학습된 MF factor가 있는 상품을 골랐지만 평점을 모델 성능이나 정답에 맞춰 고르지 않았다. 발표 예시의 변경은 모델 튜닝이나 평가가 아니다.

`data/demo_support.json`은 예전 개발 train에서 만든 입력이므로 공개 시연에 사용하지 않는다. `outputs/final/external_support.json` 역시 평가에 사용한 실제 사용자 기록이므로 사용하지 않는다. Validation/Internal Test/외부 held-out 파일도 시연에 사용하지 않는다.

실행은 `reports/DEMO_GUIDE.md`를 따른다. 기존 모델/후보/결합식을 그대로 쓰며 CLI 표시만 `scripts/presentation_demo.py`가 담당한다. 성능 표나 재평가 명령을 발표 중 실행하지 않는다.
