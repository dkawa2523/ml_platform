# Models And Ensembles

Supported candidate models:

```text
linear
ridge
lasso
elasticnet
random_forest
extra_trees
gradient_boosting
lightgbm
xgboost
catboost
```

`lightgbm`, `xgboost`, and `catboost` are optional dependencies. Local slim
runs should use `Basic/model_suite=fast` or a custom `Model/candidates` list.

## Model Suites

| Suite | Candidates |
| --- | --- |
| `default` | all supported models |
| `fast` | non-optional models |
| `interpretable` | linear, ridge, lasso, elasticnet |
| `tree` | random_forest, extra_trees, gradient_boosting |
| `gbm` | lightgbm, xgboost, catboost |
| `custom` | values from `Model/candidates` |

## Quality Mode

`Basic/quality_mode` is not HPO. It applies bounded preset changes such as
estimator counts for tree/GBM candidates.

## Ensembles

Supported ensemble methods:

```text
mean_topk
weighted
median
```

Ensembles are compared in `evaluate_models` alongside single models.
