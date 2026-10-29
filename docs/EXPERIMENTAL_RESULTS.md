# Experimental results

The repository contains a small illustrative 60-pair CSV, not a verified
real-student benchmark. A resource-safe run completed the lexical method with
36 training, 12 validation, and 12 test pairs:

| Method | Validation threshold | Precision | Recall | F1 | Accuracy | Specificity | Balanced accuracy | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Lexical TF-IDF | 0.5 | 0.80 | 0.67 | 0.73 | 0.75 | 0.83 | 0.75 | 5 | 1 | 2 | 4 |

Semantic evaluation was intentionally skipped in this validation run to avoid
downloading large model weights. The application reports semantic evaluation
as unavailable and keeps lexical results. To reproduce the full benchmark
when network and model resources are acceptable, run:

```powershell
python src\evaluate_models.py
```

The command writes ignored files under `docs/evaluation/`, including
`metrics.csv`, `scored_pairs.csv`, and misclassification reports. These
numbers are not production accuracy: labels are starter annotations and the
test split is small.
