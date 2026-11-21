# Segmentation benchmark — failure report

317 annotated objects, 314 scored predictions, 63 tiles of 1024 px over 1 slide(s). TP 306 / FP 8 / FN 11. Brackets are 95% intervals (2000 bootstrap replicates over tiles).

**Read this first**

- Confidence intervals describe spatial sampling variability WITHIN the scored slides. They do not describe generalisation across animals, sections, stain batches or scanners: with fewer than 5 slides the between-slide variance is not estimable and no between-slide standard error is reported.
- HUK1_COR_1_human_val is held-out blocks of the training section, and most of its objects are curated model output (selected, not corrected) rather than hand-drawn. See the by-source breakdown; the hand-drawn subset is the one that is independent of the model's own boundary bias.

## Pooled metrics

| metric | estimate [95% CI] |
|---|---|
| PQ | 0.887 [0.851, 0.914] |
| SQ | 0.914 [0.900, 0.927] |
| DQ | 0.970 [0.944, 0.988] |
| recall | 0.965 [0.933, 0.989] |
| precision | 0.975 [0.947, 0.992] |
| dice_per_gt | 0.920 [0.884, 0.948] |
| iou_per_gt | 0.883 [0.844, 0.914] |
| dice_matched | 0.953 [0.944, 0.961] |
| iou_matched | 0.914 [0.900, 0.927] |
| hd95_um_mean | 5.775 [4.349, 8.315] |
| hd95_um_median | 2.500 [2.434, 3.000] |
| hd95_px_mean | 11.551 [8.697, 16.629] |
| assd_um_mean | 1.378 [1.133, 1.802] |
| split_rate | 0.006 [0.000, 0.017] |
| merge_rate | 0.032 [0.000, 0.070] |
| fg_dice_px | 0.969 [0.958, 0.977] |
| fg_iou_px | 0.940 [0.920, 0.955] |
| dice_px[tubule] | 0.957 [0.940, 0.967] |
| dice_px[glomerulus] | 0.988 [0.986, 0.991] |

HD95 and ASSD are over true positives only; read them next to recall. `dice_per_gt` counts each missed object as 0, `dice_matched` does not.

## Per slide

| slide | n GT | PQ | recall | dice_per_gt | dice_matched | hd95_um_mean | merge_rate |
|---|---|---|---|---|---|---|---|
| HUK1_COR_1_human_val | 317 | 0.887 [0.851, 0.914] | 0.965 [0.933, 0.989] | 0.920 [0.884, 0.948] | 0.953 [0.944, 0.961] | 5.775 [4.349, 8.315] | 0.032 [0.000, 0.070] |

1 slide(s) scored: between-slide standard error is not estimable; per-slide point estimates are shown instead.

## By ground-truth class

| group | n GT | recall | dice_per_gt | hd95_um_mean | split_rate | merge_rate |
|---|---|---|---|---|---|---|
| tubule | 292 | 0.962 [0.924, 0.988] | 0.914 [0.871, 0.944] | 4.905 [3.531, 7.143] | 0.007 [0.000, 0.019] | 0.034 [0.000, 0.077] |
| glomerulus | 25 | 1.000 [1.000, 1.000] | 0.985 [0.980, 0.989] | 15.555 [9.240, 22.906] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

## By annotation source

| group | n GT | recall | dice_per_gt | hd95_um_mean | split_rate | merge_rate |
|---|---|---|---|---|---|---|
| curated | 272 | 0.971 [0.933, 0.996] | 0.928 [0.888, 0.958] | 5.359 [3.994, 8.015] | 0.004 [0.000, 0.012] | 0.029 [0.000, 0.072] |
| hand | 45 | 0.933 [0.898, 1.000] | 0.869 [0.824, 0.969] | 8.390 [3.743, 14.790] | 0.022 [0.000, 0.071] | 0.044 [0.000, 0.143] |

## Failure types (annotated objects)

| type | n | share |
|---|---|---|
| ok | 286 | 90.2% |
| leak | 13 | 4.1% |
| merge | 10 | 3.2% |
| poor_overlap | 4 | 1.3% |
| split | 2 | 0.6% |
| miss | 2 | 0.6% |

`merge` and `split` take precedence over the detection outcome; `miss` is an unmatched object whose best overlap is IoU < 0.10; `leak` is a matched object with more than 5% of the prediction beyond the 5 px ring.

## Worst tiles by Dice (lowest `dice_per_gt`, tiles with ≥ 3 objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| HUK1_COR_1_human_val | 8320 | 13440 | 9 | 7/1/2 | 0.734 | 13.57 | 50.03 | 0 | 0 | 0.889 |
| HUK1_COR_1_human_val | 10368 | 13440 | 6 | 5/0/1 | 0.806 | 3.29 | 4.47 | 0 | 0 | 0.966 |
| HUK1_COR_1_human_val | 8320 | 14464 | 26 | 23/1/3 | 0.816 | 9.87 | 52.61 | 4 | 0 | 0.950 |
| HUK1_COR_1_human_val | 24704 | 4224 | 12 | 11/2/1 | 0.818 | 15.97 | 68.46 | 2 | 1 | 0.961 |
| HUK1_COR_1_human_val | 9344 | 12416 | 18 | 16/2/2 | 0.822 | 6.89 | 27.73 | 0 | 0 | 0.894 |
| HUK1_COR_1_human_val | 11392 | 15488 | 30 | 28/0/2 | 0.888 | 5.84 | 63.04 | 4 | 0 | 0.976 |
| HUK1_COR_1_human_val | 9344 | 15488 | 31 | 31/1/0 | 0.954 | 3.37 | 24.02 | 0 | 1 | 0.977 |
| HUK1_COR_1_human_val | 11392 | 14464 | 46 | 46/0/0 | 0.955 | 3.45 | 41.56 | 0 | 0 | 0.971 |
| HUK1_COR_1_human_val | 10368 | 14464 | 25 | 25/0/0 | 0.956 | 3.77 | 19.14 | 0 | 0 | 0.968 |
| HUK1_COR_1_human_val | 9344 | 14464 | 31 | 31/0/0 | 0.958 | 2.90 | 10.71 | 0 | 0 | 0.970 |
| HUK1_COR_1_human_val | 18560 | 1152 | 8 | 8/0/0 | 0.962 | 3.39 | 7.16 | 0 | 0 | 0.970 |
| HUK1_COR_1_human_val | 8320 | 15488 | 5 | 5/0/0 | 0.963 | 2.29 | 3.20 | 0 | 0 | 0.969 |
| HUK1_COR_1_human_val | 10368 | 15488 | 33 | 33/0/0 | 0.966 | 2.35 | 3.91 | 0 | 0 | 0.973 |
| HUK1_COR_1_human_val | 11392 | 13440 | 6 | 6/0/0 | 0.966 | 2.17 | 3.20 | 0 | 0 | 0.967 |
| HUK1_COR_1_human_val | 9344 | 13440 | 9 | 9/0/0 | 0.968 | 3.54 | 5.70 | 0 | 0 | 0.979 |
| HUK1_COR_1_human_val | 25728 | 4224 | 3 | 3/0/0 | 0.986 | 16.97 | 34.29 | 0 | 0 | 0.987 |
| HUK1_COR_1_human_val | 24704 | 6272 | 3 | 3/0/0 | 0.992 | 13.17 | 35.57 | 0 | 0 | 0.993 |

## Worst tiles by HD95 (highest mean, tiles with ≥ 3 matched objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| HUK1_COR_1_human_val | 25728 | 4224 | 3 | 3/0/0 | 0.986 | 16.97 | 34.29 | 0 | 0 | 0.987 |
| HUK1_COR_1_human_val | 24704 | 4224 | 12 | 11/2/1 | 0.818 | 15.97 | 68.46 | 2 | 1 | 0.961 |
| HUK1_COR_1_human_val | 8320 | 13440 | 9 | 7/1/2 | 0.734 | 13.57 | 50.03 | 0 | 0 | 0.889 |
| HUK1_COR_1_human_val | 24704 | 6272 | 3 | 3/0/0 | 0.992 | 13.17 | 35.57 | 0 | 0 | 0.993 |
| HUK1_COR_1_human_val | 8320 | 14464 | 26 | 23/1/3 | 0.816 | 9.87 | 52.61 | 4 | 0 | 0.950 |
| HUK1_COR_1_human_val | 9344 | 12416 | 18 | 16/2/2 | 0.822 | 6.89 | 27.73 | 0 | 0 | 0.894 |
| HUK1_COR_1_human_val | 11392 | 15488 | 30 | 28/0/2 | 0.888 | 5.84 | 63.04 | 4 | 0 | 0.976 |
| HUK1_COR_1_human_val | 10368 | 14464 | 25 | 25/0/0 | 0.956 | 3.77 | 19.14 | 0 | 0 | 0.968 |
| HUK1_COR_1_human_val | 9344 | 13440 | 9 | 9/0/0 | 0.968 | 3.54 | 5.70 | 0 | 0 | 0.979 |
| HUK1_COR_1_human_val | 11392 | 14464 | 46 | 46/0/0 | 0.955 | 3.45 | 41.56 | 0 | 0 | 0.971 |
| HUK1_COR_1_human_val | 18560 | 1152 | 8 | 8/0/0 | 0.962 | 3.39 | 7.16 | 0 | 0 | 0.970 |
| HUK1_COR_1_human_val | 9344 | 15488 | 31 | 31/1/0 | 0.954 | 3.37 | 24.02 | 0 | 1 | 0.977 |
| HUK1_COR_1_human_val | 10368 | 13440 | 6 | 5/0/1 | 0.806 | 3.29 | 4.47 | 0 | 0 | 0.966 |
| HUK1_COR_1_human_val | 9344 | 14464 | 31 | 31/0/0 | 0.958 | 2.90 | 10.71 | 0 | 0 | 0.970 |
| HUK1_COR_1_human_val | 10368 | 15488 | 33 | 33/0/0 | 0.966 | 2.35 | 3.91 | 0 | 0 | 0.973 |
| HUK1_COR_1_human_val | 8320 | 15488 | 5 | 5/0/0 | 0.963 | 2.29 | 3.20 | 0 | 0 | 0.969 |
| HUK1_COR_1_human_val | 11392 | 13440 | 6 | 6/0/0 | 0.966 | 2.17 | 3.20 | 0 | 0 | 0.967 |

17 of 63 tiles have ≥ 3 annotated objects and are ranked. Coordinates are the tile's top-left corner in working pixels.

## Worst matched objects by HD95

| slide | cx | cy | class | status | failure | Dice | HD95 µm | pred→GT px | GT→pred px | leak | area ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HUK1_COR_1_human_val | 25484 | 5031 | tubule | TP | merge | 0.672 | 68.46 | 136.9 | 20.2 | 0.460 | 1.95 |
| HUK1_COR_1_human_val | 11743 | 16067 | tubule | TP | merge | 0.681 | 63.04 | 126.1 | 45.4 | 0.457 | 1.90 |
| HUK1_COR_1_human_val | 25313 | 4975 | tubule | TP | split | 0.671 | 54.61 | 30.1 | 109.2 | 0.020 | 0.59 |
| HUK1_COR_1_human_val | 8505 | 14593 | tubule | TP | merge | 0.737 | 52.61 | 105.2 | 36.1 | 0.369 | 1.67 |
| HUK1_COR_1_human_val | 9278 | 14263 | tubule | TP | ok | 0.961 | 50.03 | 1.4 | 100.1 | 0.000 | 0.96 |
| HUK1_COR_1_human_val | 18819 | 10786 | glomerulus | TP | ok | 0.993 | 47.74 | 95.5 | 3.0 | 0.000 | 1.00 |
| HUK1_COR_1_human_val | 19413 | 2442 | glomerulus | TP | ok | 0.992 | 44.86 | 89.7 | 3.6 | 0.000 | 1.01 |
| HUK1_COR_1_human_val | 16692 | 10588 | glomerulus | TP | ok | 0.990 | 43.28 | 86.6 | 9.0 | 0.000 | 1.00 |
| HUK1_COR_1_human_val | 17444 | 10124 | glomerulus | TP | ok | 0.986 | 42.38 | 84.8 | 9.3 | 0.001 | 1.01 |
| HUK1_COR_1_human_val | 11654 | 15231 | tubule | TP | leak | 0.820 | 41.56 | 83.1 | 22.0 | 0.273 | 1.42 |
| HUK1_COR_1_human_val | 8759 | 14385 | tubule | TP | leak | 0.905 | 37.81 | 75.6 | 19.0 | 0.130 | 1.17 |
| HUK1_COR_1_human_val | 25449 | 6744 | glomerulus | TP | ok | 0.992 | 35.57 | 71.1 | 4.0 | 0.001 | 1.01 |
| HUK1_COR_1_human_val | 26689 | 4364 | glomerulus | TP | ok | 0.994 | 34.29 | 68.6 | 3.0 | 0.000 | 1.00 |
| HUK1_COR_1_human_val | 18183 | 8713 | glomerulus | TP | ok | 0.986 | 33.23 | 66.5 | 3.2 | 0.006 | 1.03 |
| HUK1_COR_1_human_val | 19879 | 9693 | glomerulus | TP | leak | 0.947 | 30.87 | 61.7 | 40.0 | 0.073 | 1.10 |
| HUK1_COR_1_human_val | 9828 | 12820 | tubule | TP | leak | 0.881 | 27.73 | 55.5 | 21.8 | 0.148 | 1.24 |
| HUK1_COR_1_human_val | 9593 | 15799 | tubule | TP | split | 0.686 | 24.02 | 28.7 | 48.0 | 0.000 | 0.53 |
| HUK1_COR_1_human_val | 9048 | 14548 | tubule | TP | merge | 0.800 | 23.57 | 47.1 | 19.9 | 0.284 | 1.50 |
| HUK1_COR_1_human_val | 8388 | 14542 | tubule | TP | ok | 0.799 | 23.56 | 47.1 | 38.9 | 0.000 | 0.67 |
| HUK1_COR_1_human_val | 9006 | 15363 | tubule | TP | leak | 0.823 | 22.19 | 44.4 | 38.1 | 0.214 | 1.41 |

## Worst matched objects by leak fraction

| slide | cx | cy | class | status | failure | Dice | HD95 µm | pred→GT px | GT→pred px | leak | area ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HUK1_COR_1_human_val | 25484 | 5031 | tubule | TP | merge | 0.672 | 68.46 | 136.9 | 20.2 | 0.460 | 1.95 |
| HUK1_COR_1_human_val | 11743 | 16067 | tubule | TP | merge | 0.681 | 63.04 | 126.1 | 45.4 | 0.457 | 1.90 |
| HUK1_COR_1_human_val | 8505 | 14593 | tubule | TP | merge | 0.737 | 52.61 | 105.2 | 36.1 | 0.369 | 1.67 |
| HUK1_COR_1_human_val | 12077 | 16094 | tubule | TP | merge | 0.775 | 19.10 | 38.2 | 11.0 | 0.311 | 1.53 |
| HUK1_COR_1_human_val | 9048 | 14548 | tubule | TP | merge | 0.800 | 23.57 | 47.1 | 19.9 | 0.284 | 1.50 |
| HUK1_COR_1_human_val | 11654 | 15231 | tubule | TP | leak | 0.820 | 41.56 | 83.1 | 22.0 | 0.273 | 1.42 |
| HUK1_COR_1_human_val | 9006 | 15363 | tubule | TP | leak | 0.823 | 22.19 | 44.4 | 38.1 | 0.214 | 1.41 |
| HUK1_COR_1_human_val | 9828 | 12820 | tubule | TP | leak | 0.881 | 27.73 | 55.5 | 21.8 | 0.148 | 1.24 |
| HUK1_COR_1_human_val | 9590 | 15069 | tubule | TP | leak | 0.846 | 10.71 | 21.4 | 19.7 | 0.141 | 1.17 |
| HUK1_COR_1_human_val | 9687 | 16114 | tubule | TP | leak | 0.812 | 8.67 | 17.0 | 17.3 | 0.132 | 1.21 |
| HUK1_COR_1_human_val | 8759 | 14385 | tubule | TP | leak | 0.905 | 37.81 | 75.6 | 19.0 | 0.130 | 1.17 |
| HUK1_COR_1_human_val | 11172 | 15348 | tubule | TP | leak | 0.886 | 9.19 | 18.4 | 17.8 | 0.109 | 1.25 |
| HUK1_COR_1_human_val | 9609 | 15733 | tubule | TP | leak | 0.867 | 5.66 | 11.3 | 10.1 | 0.084 | 1.25 |
| HUK1_COR_1_human_val | 11607 | 16110 | tubule | TP | leak | 0.922 | 12.26 | 24.5 | 12.3 | 0.077 | 1.13 |
| HUK1_COR_1_human_val | 10593 | 15112 | tubule | TP | leak | 0.877 | 9.19 | 18.4 | 7.3 | 0.077 | 1.00 |
| HUK1_COR_1_human_val | 24894 | 4727 | tubule | TP | leak | 0.890 | 6.71 | 13.4 | 13.0 | 0.076 | 1.24 |
| HUK1_COR_1_human_val | 19879 | 9693 | glomerulus | TP | leak | 0.947 | 30.87 | 61.7 | 40.0 | 0.073 | 1.10 |
| HUK1_COR_1_human_val | 9409 | 16122 | tubule | TP | leak | 0.948 | 13.46 | 26.9 | 8.0 | 0.052 | 1.07 |
| HUK1_COR_1_human_val | 25136 | 4523 | tubule | TP | ok | 0.934 | 6.50 | 13.0 | 11.3 | 0.044 | 1.14 |
| HUK1_COR_1_human_val | 12156 | 15179 | tubule | TP | ok | 0.717 | 3.99 | 8.0 | 3.6 | 0.044 | 1.79 |

## Unmatched annotated objects (11; largest first)

| slide | cx | cy | class | failure | area px | best IoU |
|---|---|---|---|---|---|---|
| HUK1_COR_1_human_val | 9946 | 13096 | tubule | poor_overlap | 42770 | 0.220 |
| HUK1_COR_1_human_val | 11874 | 16090 | tubule | merge | 24724 | 0.455 |
| HUK1_COR_1_human_val | 10459 | 14268 | tubule | miss | 14268 | 0.000 |
| HUK1_COR_1_human_val | 8636 | 14562 | tubule | merge | 12807 | 0.325 |
| HUK1_COR_1_human_val | 25423 | 4906 | tubule | merge | 12135 | 0.435 |
| HUK1_COR_1_human_val | 8397 | 14258 | tubule | poor_overlap | 11061 | 0.238 |
| HUK1_COR_1_human_val | 8515 | 14189 | tubule | miss | 8992 | 0.000 |
| HUK1_COR_1_human_val | 9787 | 12658 | tubule | poor_overlap | 6225 | 0.334 |
| HUK1_COR_1_human_val | 12142 | 16109 | tubule | merge | 6078 | 0.308 |
| HUK1_COR_1_human_val | 9122 | 14566 | tubule | merge | 3640 | 0.143 |
| HUK1_COR_1_human_val | 8917 | 15223 | tubule | poor_overlap | 2195 | 0.376 |

## Edge cases

### Boundary leakage

| quantity | value |
|---|---|
| n_matched | 306 |
| leak_frac_mean | 0.014 |
| leak_frac_gt_0.05_rate | 0.059 |
| over_reach_asymmetry_px_mean | 2.842 |
| over_reach_asymmetry_px_median | 0.000 |
| area_ratio_median | 1.015 |
| area_ratio_mean | 1.028 |
| pred_solidity_lt_0.85_rate | 0.042 |
| gt_solidity_lt_0.85_rate | 0.038 |
| pred_px_on_trusted_background_frac | 0.035 |

### Small and disconnected components

| quantity | value |
|---|---|
| predictions inside the rectangles (not edge-cut) | 1719 |
|   below their class min_area floor | 0 |
|   with more than one connected component | 0 |
|   mean stray area share among those | 0.000 |
| false positives | 8 |
|   fragments on an annotated object | 6 |
|   on trusted background | 2 |
|   area px, quartiles | [2663.5, 4031.5, 6948.0] |

### By ground-truth size

| quartile | area px | n | recall | dice_per_gt | HD95 µm | merge |
|---|---|---|---|---|---|---|
| 1 | 217–6540 | 79 | 0.949 | 0.896 | 3.22 | 0.025 |
| 2 | 6540–10850 | 79 | 0.987 | 0.948 | 3.69 | 0.000 |
| 3 | 10850–17961 | 79 | 0.949 | 0.905 | 5.20 | 0.063 |
| 4 | 17961–162769 | 80 | 0.975 | 0.930 | 10.87 | 0.037 |

### Stain intensity (observational)

Observational only: staining intensity is confounded with anatomy (medulla stains differently from cortex), so an association here is not evidence of stain sensitivity on its own. The controlled test is --stain-drift.

| pair | Spearman ρ | p | n tiles |
|---|---|---|---|
| h_od,dice_per_gt | -0.120 | 0.646 | 17 |
| h_od,hd95_um_mean | -0.034 | 0.896 | 17 |
| e_od,dice_per_gt | 0.409 | 0.103 | 17 |
| e_od,hd95_um_mean | 0.100 | 0.701 | 17 |

| h_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.004 | 6 | 0.899 | 0.934 | 4.86 |
| 2 | 0.005 | 5 | 0.912 | 0.947 | 3.62 |
| 3 | 0.006 | 6 | 0.823 | 0.851 | 7.39 |

| e_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.018 | 6 | 0.871 | 0.910 | 4.81 |
| 2 | 0.020 | 5 | 0.851 | 0.884 | 6.84 |
| 3 | 0.023 | 6 | 0.918 | 0.944 | 4.23 |

### Stain drift (controlled perturbation)

Synthetic perturbation of the haematoxylin / eosin optical densities of held-out windows, re-inferred window-locally. Training augmentation draws each scale from U(0.9, 1.1); larger steps are outside it. The 'roundtrip' level applies the colour-space conversion with both scales at 1.0 and is the reference for the scaled levels: the conversion alone perturbs pixels. This measures sensitivity to stain STRENGTH on these sections; it is not evidence about other stains, protocols or scanners. The baseline differs slightly from the headline numbers because it is a window-local re-inference, not the slide-wide map.

| level | H× | E× | PQ | recall | dice_per_gt | HD95 µm | merge | n pred | PQ vs unperturbed | tissue |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 1.0 | 1.0 | 0.870 | 0.941 | 0.890 | 6.69 | 0.037 | 306 | 1.000 | 0.898 |
| roundtrip | 1.0 | 1.0 | 0.861 | 0.932 | 0.881 | 6.63 | 0.043 | 306 | 0.931 | 0.899 |
| both-0.3 | 0.7 | 0.7 | 0.851 | 0.925 | 0.873 | 7.11 | 0.043 | 306 | 0.925 | 0.842 |
| both-0.2 | 0.8 | 0.8 | 0.856 | 0.929 | 0.877 | 6.93 | 0.043 | 306 | 0.932 | 0.871 |
| both-0.1 | 0.9 | 0.9 | 0.860 | 0.932 | 0.880 | 6.72 | 0.043 | 306 | 0.935 | 0.886 |
| both+0.1 | 1.1 | 1.1 | 0.861 | 0.932 | 0.881 | 6.58 | 0.043 | 306 | 0.929 | 0.905 |
| both+0.2 | 1.2 | 1.2 | 0.861 | 0.932 | 0.881 | 6.55 | 0.043 | 306 | 0.928 | 0.909 |
| both+0.3 | 1.3 | 1.3 | 0.863 | 0.932 | 0.881 | 6.58 | 0.043 | 304 | 0.926 | 0.913 |
| H-0.3 | 0.7 | 1.0 | 0.871 | 0.941 | 0.891 | 7.12 | 0.043 | 306 | 0.894 | 0.895 |
| H+0.3 | 1.3 | 1.0 | 0.844 | 0.910 | 0.861 | 6.52 | 0.031 | 304 | 0.914 | 0.901 |
| E-0.3 | 1.0 | 0.7 | 0.844 | 0.913 | 0.862 | 6.66 | 0.031 | 303 | 0.883 | 0.849 |
| E+0.3 | 1.0 | 1.3 | 0.866 | 0.932 | 0.883 | 7.11 | 0.050 | 304 | 0.899 | 0.911 |
