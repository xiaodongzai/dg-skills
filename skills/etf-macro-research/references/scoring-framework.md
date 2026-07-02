# Scoring Framework

## Module weights (default)

- macro_regime: 0.30
- cross_asset: 0.20
- industry_prosperity: 0.30
- earnings_quality: 0.20

## Example mapping

- 75-100: Strong positive
- 55-74: Mild positive
- 45-54: Neutral/transition
- 25-44: Mild negative
- 0-24: Strong negative

## Confidence

Confidence = coverage_score * consistency_score

- coverage_score: available metrics / required metrics
- consistency_score: penalty if module signals conflict
