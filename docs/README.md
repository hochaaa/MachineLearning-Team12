# 문서 안내

현재 시작점은 [루트 README](../README.md)다. 설치·실행 상세는 [Frozen V1 런타임](../deployment/final_v1/README.md), 로더 수식/API는 [standalone 설명](../deployment/standalone_v1/METHODS_EXPLAINED.md)을 읽는다.

## 머신러닝 근거

- [설계 결정](../PROJECT_DECISIONS.md), [요구사항 추적](../REQUIREMENTS_TRACEABILITY.md), [알고리즘 설명](../METHODS_EXPLAINED.md), [출처](../REFERENCES.md), [데이터 계약](../data/README.md)
- [V2](../experiments/development_v2/README.md), [V3](../experiments/development_v3/README.md): 실제 비교 실험 코드·설명. 현재 웹 모델과 분리한다.
- [합성 학습 예제](../experiments/synthetic_demo/README.md): 원본 모델을 대체하는 서비스가 아니다. 과거 `demo/`에서 이동했다.
- 로컬 `reports/`와 `outputs/`에는 MODEL_IMPROVEMENT.md, FINAL_EVALUATION_AUDIT.md, frozen_results.csv 및 V2/V3 결과 등 제출·평가 증거를 보존했다. 비공개 자료이므로 GitHub 링크로 존재를 보장하지 않는다.

## 왜 일부 문서를 루트에 유지하나요?

AGENTS.md와 기존 연구/감사 스크립트가 METHODS_EXPLAINED.md, PROJECT_DECISIONS.md, REQUIREMENTS_TRACEABILITY.md, REFERENCES.md를 루트에서 참조한다. 경로 호환성과 실험 이력을 위해 유지했다. RUNTIME_MANIFEST.json 역시 과거 감사 도구가 참조하는 목록이며 현재5개 자산의 manifest와 다르다.

[STEP10 가이드](archive/TEAM_SETUP_GUIDE.md)는 당시 상태를 보존한 역사 자료다. 현재 실행에 적용하지 않는다. 중복 TEAM_RUN_GUIDE와 옛 ZIP용 README_START_HERE는 루트 README로 대체했다. web/demo·web/deployment 및 tools/team_setup은 연구·감사 코드에서 참조하므로 보존하며 새 실행 절차로 안내하지 않는다. 기존 역사 보고서의 옛 경로는 해당 단계 당시 위치를 의미한다.
