# V2-24 accuracy experiment

Only new code/output directories. No UI/service/data/Frozen modification, no installs/network/Git actions.

One fixed user split of original Train:255 training users/895ratings;50 developer users;25 final users. Both evaluation cohorts excluded from developer MF/IDF; only after developer selection the50 developer users are added to final training, keeping all25 final users excluded. Final labels sealed until selection+final fits. Every model uses the same five hash-chosen Support, candidate479-minusSupport, relevance≥.7, ID tie rule and positive-user macro NDCG@5/Recall/HR. Out-of-catalog positives remain denominator misses. Unknown ratings are not declared dislikes.

“Frozen baseline” means the same architecture/hyperparameters with user-exclusion retraining, not reuse of the original whole-Train weights. V22/V23 formulas are benchmarked with the SAME train-only IDF/features/MF on common479. This is a common-candidate adaptation, not a full497 deployment score. The source population was previously studied; this final is independent by user assignment within V24, not pristine external confirmation.

Implemented improvements: liked-excess and centered signed Content profiles, fixed/adaptive Content/MF weight, candidate-score midrank normalization with raw-unclipped MF to remove clipping ties, limited factors/reg comparison. No label-fitted scaler. Developer-poor MF settings are pruned. Pure MF is a prespecified diagnostic, not a selection candidate; this is reported explicitly even though its developer NDCG is higher. No changes after final.

Actual4 MF fits:3 developer configs,1 final shared baseline/selected fit. Content fit2. See experiment_config.json/selection.json/final_fit_complete.json and execution.log. Final selected baseline; best_model.npz is that developer-selected final-trained artifact, not a newly proven improved model. Contains item factors/IDF/features/popularity only, no P/user mapping/history.

Commands from project root with existing environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/accuracy_optimization/tests -p test_accuracy.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.accuracy_optimization.run
# Post-run evidence tests; no fits/evaluation replay.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/accuracy_optimization/tests -v
# Inference only: support.json contains five {"product_id":"...","rating":7.5} records.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.accuracy_optimization.predict --model outputs/scent_v2/accuracy_optimization/best_model.npz --support "$LOCAL_SUPPORT_JSON"
```

Completed run refuses overwrite/retry. Never delete its config/final marker and silently repeat final evaluation. Future experiments need separate planned outputs and an untouched assessment dataset. Source data/private output is not a public Git reproduction bundle.
