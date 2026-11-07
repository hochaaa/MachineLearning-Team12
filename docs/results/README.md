# 저장된 평가 결과

모든 표는 기존 저장 결과를 복사했으며 학습·튜닝·최종 평가를 재실행하지 않았습니다.

- final_metrics.csv: Frozen V1의 Validation/Internal/External 집계. NDCG@10. 정확도 평균 분모는 각각 긍정 정답 보유 137/136/26명입니다.
- structured_comparison.csv: 후반 개발 CV의 NDCG@5 비교. 최종 NDCG@10과 직접 비교하지 않습니다.
- reserved_comparison.csv: 과거 평가 이력이 있는 Reserved 25명 중 긍정 23명의 재검증. 새로운 독립 Test가 아닙니다.
- sample_components.csv: 합성 입력에 대한 실제 저장 Top5 점수 구성. 예측 평점이나 확률이 아닙니다.

기존 출처: outputs/improvement/frozen_results.csv, outputs/scent_v2/accuracy_root_cause/model_comparison.csv, outputs/scent_v2/final_validation/final_model_comparison.csv, outputs/final_submission/execution_results/sample_components.csv. 원본 데이터와 사용자별 평점·ID는 공개하지 않습니다. 실험 소스의 일부 실행·사후 검사에는 공개하지 않은 기존 로컬 데이터·모델이 필요합니다. 전체 테스트를 무조건 실행하거나 최종 Test를 재실행하지 마세요.
