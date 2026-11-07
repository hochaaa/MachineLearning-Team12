# V2-2: score structure diagnosis, zero fits

Only existing V2-1 INNER Qs, corresponding inner train/support/answers, catalog and
fixed479 candidates are replayed. No old validation/internal/external/outer test
answers, Frozen weights, parameter selection, calibration, deployment or installs.
Reference lambda remains .01. Other lambdas and unclipped/excluded results are
diagnostics, never selected policies. Existing V1/V2-0/V2-1 stay read-only.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -W error -m unittest discover -s experiments/scent_v2/score_diagnostics/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -W error -m experiments.scent_v2.score_diagnostics.run
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -W error -m experiments.scent_v2.score_diagnostics.supplement
```

The runner refuses existing output. Audit hook restricts reads/writes, profile hook
rejects all model fit calls. Source feature vectors are transformed from saved IDF,
not refitted. All three lambdas share each unchanged Q. Baseline scores/IDs must
match V2-1 before further diagnostic summaries. Labels enter only post-score metrics.

Outputs under ignored outputs/scent_v2/score_diagnostics include local PRIVATE
candidate arrays/mappings, context records and aggregate tables. Do not upload/share.
150 contexts per lambda contain75 users twice; user macro averages cluster contexts.
Pooled candidates, context means and user distribution means have different meanings.
Each main score's own_top5 uses its own ranking; contribution own_top5 aliases the
Hybrid Top5. hybrid_top5 always uses the common actual Hybrid list. Missing values
are excluded with counts; constant correlations remain undefined, never zero-filled.
Spearman uses average ranks for ties. Top20 is actual Hybrid Top20, not label-derived.

Clipping denominators are finite raw MF candidates; counts are candidate-context
occurrences plus distinct IDs/users. Tie count means adjacent equal-score pairs in
the ranking, not internal Python sort comparison operations. Fallback-type classes
can overlap; support-partial/none are context-wide attributes, not item properties.
No-fallback excludes all unavailable component cases; currently no missing Content
is observed, but synthetic tests cover it. No-positive users are separate from NDCG0.

Top5 enrichment=(group Top5 share)/(group candidate share); upper-decile membership
uses >= quantile(.9), so ties can exceed10%. Personal concentration is repeated
context Top5 item slot concentration/HHI, not within-list duplicates (none allowed).
Raw and fallback-excluded counterfactuals do not compute/select accuracy improvements.
Bootstrap user20k/seed12 is exploratory, no multiplicity correction or causal claim.

Unfamiliar functions/parameters and interpretation are in METHODS_EXPLAINED.md.
