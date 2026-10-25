"""Attach actual evidence to every requirement; no final compliance claim."""
from pathlib import Path

pass_evidence={
'R01':'src/perfume/models.py; scripts/demo.py; outputs/demo.json',
'R02':'src/perfume/models.py; outputs/validation/metrics.csv (Content, model-based MF, Hybrid)',
'O01':'METHODS_EXPLAINED.md; outputs/validation/training_loss.json',
'O02':'MatrixFactorization implementation and explanation; no external implementation copied',
'R05':'Team12_Proposal_Perfume_Recommendation.docx §1, text verified',
'R06':'Team12_Proposal_Perfume_Recommendation.docx §2, text verified; counts are plans',
'R07':'Team12_Proposal_Perfume_Recommendation.docx §3, text verified',
'O03':'Team12_Proposal_Perfume_Recommendation.docx §4',
'R20':'src/perfume/*.py; tests/test_core.py',
'R21':'REFERENCES.md; original recommender implementation; nearby artifact API comment',
'R23':'outputs/figures/*.svg/*.png; outputs/validation/metrics.csv; outputs/tests.log',
'R28':'professor_spec.pdf p9; unchanged proposal; reports/drafts/Team12_Development_Report.docx',
'I02':'requirements.txt; configs/experiment.json; outputs/validation/run_metadata.json; outputs/tests.log',
'I03':'reports/ZERO_POLICY.md; outputs/validation/metrics.csv; METHODS_EXPLAINED.md',
'P01':'outputs/audit/summary.json; src/perfume/data.py; data/README.md',
'P11':'PROJECT_DECISIONS.md §8 user permission confirmation; REFERENCES.md independent evidence limits; no redistribution',
'P13':'outputs/audit/threshold_counts.csv; reports/ZERO_POLICY.md (both provisional zero scenarios)',
'P14':'outputs/validation/split_manifest.json; training_counts.csv; outputs/verification.json',
'P16':'src/perfume/models.py MatrixFactorization; outputs/validation/training_loss.json; synthetic tests',
'P18':'outputs/validation/knowledge_rules.csv; outputs/demo.json; season/price disabled',
'P19':'reports/STATUS.md; professor PDF pp2–9 and final proposal read; v3 ItemCF superseded by v4 MF',
'P20':'All original datasets exist; src/perfume; scripts/audit.py; tests/test_core.py (missing-data branch not applicable)'
}
blocked_evidence={
'R03':'outputs/audit/external_trained_factor_feasibility.csv; independent external accuracy NOT run pending final zero policy/freeze',
'R04':'Existing Word proposal content read; actual submission by Oct23 not verified',
'R08':'reports/drafts/Team12_Development_Review_v2.pptx objective; final deck pending test and team inputs',
'R09':'PPT draft and outputs/audit; final deck not approved',
'R10':'PPT draft; src/perfume/data.py; final matching review pending',
'R11':'PPT draft; real validation training; final policy not fixed',
'R12':'PPT draft; validation results only; internal/external test pending',
'R13':'reports/STATUS.md; draft notes on sparse MF; final team learning confirmation pending',
'R14':'PPT draft notes; team-confirmed redo reflection pending',
'R15':'TBD authentic individual learning; do not invent',
'R16':'TBD team-confirmed individual assignments',
'R17':'TBD team-confirmed contribution percentages',
'R18':'reports/STATUS.md architecture; draft PPT module flow; final review pending',
'R19':'Not a Git repository; verified Team12 GitHub URL absent; no push performed',
'R22':'METHODS_EXPLAINED.md; reports/API_REFERENCE.md; course scope/team explainability review pending',
'R24':'Source and reports/drafts Word material exist; final Word scope/test evidence pending',
'R25':'Partial outputs exist; Nov9 final package not complete',
'R26':'Exact team presentation slot TBD (Nov10 or Nov12)',
'R27':'10-slide draft speaker timing plan; no 10min rehearsal or Q&A verification',
'Q01':'Professor confirmation of final Word purpose/structure pending',
'I01':'reports/ZERO_POLICY.md; ID-only external feasibility; frozen external protocol not executed',
'V01':'data/README.md; restored FKs; actual external common-feature/OOV shift audit pending',
'V02':'Real hybrid validation implemented; final zero policy and independent test comparisons pending',
'V03':'Knowledge rules implemented/explained; team must confirm not taught in class',
'P02':'outputs/audit/zero_joint_distribution.json; adapter works but zero semantics/final policy unresolved',
'P03':'outputs/audit/atrafshan_matching.csv; conservative exact matches; semantic/manual collision review pending',
'P04':'Implemented all core methods; real validation/rule results; final zero policy/test pending',
'P05':'Persisted disjoint splits and ranking protocol; final internal test not run',
'P06':'Actual content and trained factor overlap measured; external support/held-out positive eligibility pending',
'P07':'Synthetic answer-isolation/fold-in tests PASS; real external harness not executed',
'P08':'v4 supersedes v3 ItemCF with MF; fold-in tested, actual external validity pending',
'P09':'Internal candidate/metric definitions fixed; external rating scale/candidates/final protocol pending',
'P10':'Parfumo auxiliary analysis not run; never substituted for personalized external evaluation',
'P12':'TBD team final choice and course-external method confirmation',
'P15':'outputs/validation/selection.json scenario-wise choices only; final zero policy BLOCKED',
'P17':'src/perfume/external.py; fixed-factor synthetic tests PASS; real external scoring pending'
}
path=Path('REQUIREMENTS_TRACEABILITY.md');lines=[]
for line in path.read_text().splitlines():
    cells=[c.strip() for c in line.split('|')]
    if len(cells)>3 and cells[1] in pass_evidence|blocked_evidence:
        key=cells[1];cells[-3]=pass_evidence.get(key,blocked_evidence.get(key));cells[-2]='PASS' if key in pass_evidence else 'BLOCKED'
        line='| '+' | '.join(cells[1:-1])+' |'
    lines.append(line)
lines.extend(['','**2026-10-22 execution audit:** PASS describes only the row criterion and cited local evidence. Draft deliverables and validation sensitivity do not establish final compliance. No internal/external test was run. Zero policy, final submission and authentic team inputs remain BLOCKED.'])
path.write_text('\n'.join(lines)+'\n')
