# V2-17 근거 및 코드 출처

공식 제조사 제품/컬렉션/이용조건 URL은 `outputs/scent_v2/perfume_catalog_expansion/source_registry.csv`와 각CSV의source_url/checked_date에 있다. 표가인용하는것은짧은제품/노트/구성Accord사실필드이며브랜드사진·리뷰·마케팅원문을전재하지않았다. 이용권한이확보되었다는문서가아니다.

코드는직접작성했고다음프로젝트코드만읽기전용으로재사용했다.

- `src/perfume/data.py::normalize/fragrantica/identity`: 원래정규화·메타데이터읽기·정확키비교. 변경없음.
- `src/perfume/models.py::Content.fit`: 새학습이아닌기존binaryTF/IDF/L2투영식의출처. 같은식의독립transform함수에인접주석기재.
- `deployment/final_v1/config.py::assets_path/inspect_assets`: 읽기전용runtime무결성검사. 원본Q는새로학습하거나load해추론하지않았다.
- `outputs/scent_v2/real_rating_retraining/REPORT.md`, `perfume_matching_report.csv`, `MODEL_IMPROVEMENT_NARRATIVE.md`: 이전단계맥락. 원본점수는조사자료로사용하지않았다.
- Python 표준API 설명: https://docs.python.org/3/library/csv.html ; https://docs.python.org/3/library/json.html ; https://docs.python.org/3/library/hashlib.html ; https://docs.python.org/3/library/unittest.html . 외부예제코드를복사하지않았다.

일부공식페이지는지역·SKU별노트표기가달라서차이를기록했다. 동일원본평가병과현재사이트배치를자동동일시하지않는다. SourceRegistry의terms_review는조사상확인일뿐ML이용허가가아니다. Fragrantica/Parfumo 등의새DB크롤링이나개인평점전송은없다.
