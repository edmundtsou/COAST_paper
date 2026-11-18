# Segmentation benchmark — failure report

138 annotated objects, 135 scored predictions, 15 tiles of 1024 px over 1 slide(s). TP 134 / FP 1 / FN 4. Brackets are 95% intervals (2000 bootstrap replicates over tiles).

**Read this first**

- Confidence intervals describe spatial sampling variability WITHIN the scored slides. They do not describe generalisation across animals, sections, stain batches or scanners: with fewer than 5 slides the between-slide variance is not estimable and no between-slide standard error is reported.

## Pooled metrics

| metric | estimate [95% CI] |
|---|---|
| PQ | 0.882 [0.849, 0.899] |
| SQ | 0.898 [0.883, 0.906] |
| DQ | 0.982 [0.953, 0.996] |
| recall | 0.971 [0.932, 0.993] |
| precision | 0.993 [0.967, 1.000] |
| dice_per_gt | 0.918 [0.878, 0.941] |
| iou_per_gt | 0.872 [0.830, 0.895] |
| dice_matched | 0.945 [0.936, 0.950] |
| iou_matched | 0.898 [0.883, 0.906] |
| hd95_um_mean | 7.152 [5.365, 9.456] |
| hd95_um_median | 3.536 [3.102, 4.201] |
| hd95_px_mean | 14.305 [10.729, 18.912] |
| assd_um_mean | 1.847 [1.582, 2.206] |
| split_rate | 0.000 [0.000, 0.000] |
| merge_rate | 0.014 [0.000, 0.055] |
| fg_dice_px | 0.966 [0.962, 0.968] |
| fg_iou_px | 0.934 [0.927, 0.938] |
| dice_px[tubule] | 0.957 [0.951, 0.960] |
| dice_px[glomerulus] | 0.982 [0.979, 0.984] |

HD95 and ASSD are over true positives only; read them next to recall. `dice_per_gt` counts each missed object as 0, `dice_matched` does not.

## Per slide

| slide | n GT | PQ | recall | dice_per_gt | dice_matched | hd95_um_mean | merge_rate |
|---|---|---|---|---|---|---|---|
| HUK1_MED_1_test | 138 | 0.882 [0.849, 0.899] | 0.971 [0.932, 0.993] | 0.918 [0.878, 0.941] | 0.945 [0.936, 0.950] | 7.152 [5.365, 9.456] | 0.014 [0.000, 0.055] |

1 slide(s) scored: between-slide standard error is not estimable; per-slide point estimates are shown instead.

## By ground-truth class

| group | n GT | recall | dice_per_gt | hd95_um_mean | split_rate | merge_rate |
|---|---|---|---|---|---|---|
| tubule | 130 | 0.969 [0.927, 0.993] | 0.915 [0.871, 0.940] | 5.934 [4.520, 8.187] | 0.000 [0.000, 0.000] | 0.015 [0.000, 0.058] |
| glomerulus | 8 | 1.000 [1.000, 1.000] | 0.965 [0.951, 0.976] | 26.341 [11.860, 41.831] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

## Failure types (annotated objects)

| type | n | share |
|---|---|---|
| ok | 121 | 87.7% |
| leak | 12 | 8.7% |
| miss | 2 | 1.4% |
| merge | 2 | 1.4% |
| poor_overlap | 1 | 0.7% |

`merge` and `split` take precedence over the detection outcome; `miss` is an unmatched object whose best overlap is IoU < 0.10; `leak` is a matched object with more than 5% of the prediction beyond the 5 px ring.

## Worst tiles by Dice (lowest `dice_per_gt`, tiles with ≥ 3 objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| HUK1_MED_1_test | 11477 | 7283 | 5 | 4/1/1 | 0.759 | 4.57 | 8.58 | 0 | 0 | 0.953 |
| HUK1_MED_1_test | 10453 | 8307 | 10 | 9/0/1 | 0.819 | 11.02 | 41.67 | 2 | 0 | 0.952 |
| HUK1_MED_1_test | 8405 | 6259 | 11 | 10/0/1 | 0.868 | 4.56 | 10.39 | 0 | 0 | 0.970 |
| HUK1_MED_1_test | 11477 | 8307 | 13 | 12/0/1 | 0.874 | 11.99 | 75.46 | 0 | 0 | 0.971 |
| HUK1_MED_1_test | 9429 | 8307 | 5 | 5/0/0 | 0.920 | 14.48 | 53.41 | 0 | 0 | 0.952 |
| HUK1_MED_1_test | 9429 | 7283 | 14 | 14/0/0 | 0.941 | 8.92 | 60.96 | 0 | 0 | 0.970 |
| HUK1_MED_1_test | 9429 | 6259 | 9 | 9/0/0 | 0.942 | 5.96 | 17.66 | 0 | 0 | 0.966 |
| HUK1_MED_1_test | 10453 | 6259 | 19 | 19/0/0 | 0.944 | 9.00 | 45.85 | 0 | 0 | 0.967 |
| HUK1_MED_1_test | 8405 | 8307 | 4 | 4/0/0 | 0.945 | 5.95 | 9.68 | 0 | 0 | 0.963 |
| HUK1_MED_1_test | 10453 | 7283 | 39 | 39/0/0 | 0.952 | 4.34 | 21.10 | 0 | 0 | 0.965 |
| HUK1_MED_1_test | 11477 | 6259 | 4 | 4/0/0 | 0.960 | 5.09 | 9.36 | 0 | 0 | 0.964 |
| HUK1_MED_1_test | 8405 | 7283 | 3 | 3/0/0 | 0.961 | 3.35 | 4.50 | 0 | 0 | 0.966 |

## Worst tiles by HD95 (highest mean, tiles with ≥ 3 matched objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| HUK1_MED_1_test | 9429 | 8307 | 5 | 5/0/0 | 0.920 | 14.48 | 53.41 | 0 | 0 | 0.952 |
| HUK1_MED_1_test | 11477 | 8307 | 13 | 12/0/1 | 0.874 | 11.99 | 75.46 | 0 | 0 | 0.971 |
| HUK1_MED_1_test | 10453 | 8307 | 10 | 9/0/1 | 0.819 | 11.02 | 41.67 | 2 | 0 | 0.952 |
| HUK1_MED_1_test | 10453 | 6259 | 19 | 19/0/0 | 0.944 | 9.00 | 45.85 | 0 | 0 | 0.967 |
| HUK1_MED_1_test | 9429 | 7283 | 14 | 14/0/0 | 0.941 | 8.92 | 60.96 | 0 | 0 | 0.970 |
| HUK1_MED_1_test | 9429 | 6259 | 9 | 9/0/0 | 0.942 | 5.96 | 17.66 | 0 | 0 | 0.966 |
| HUK1_MED_1_test | 8405 | 8307 | 4 | 4/0/0 | 0.945 | 5.95 | 9.68 | 0 | 0 | 0.963 |
| HUK1_MED_1_test | 11477 | 6259 | 4 | 4/0/0 | 0.960 | 5.09 | 9.36 | 0 | 0 | 0.964 |
| HUK1_MED_1_test | 11477 | 7283 | 5 | 4/1/1 | 0.759 | 4.57 | 8.58 | 0 | 0 | 0.953 |
| HUK1_MED_1_test | 8405 | 6259 | 11 | 10/0/1 | 0.868 | 4.56 | 10.39 | 0 | 0 | 0.970 |
| HUK1_MED_1_test | 10453 | 7283 | 39 | 39/0/0 | 0.952 | 4.34 | 21.10 | 0 | 0 | 0.965 |
| HUK1_MED_1_test | 8405 | 7283 | 3 | 3/0/0 | 0.961 | 3.35 | 4.50 | 0 | 0 | 0.966 |

12 of 15 tiles have ≥ 3 annotated objects and are ranked. Coordinates are the tile's top-left corner in working pixels.

## Worst matched objects by HD95

| slide | cx | cy | class | status | failure | Dice | HD95 µm | pred→GT px | GT→pred px | leak | area ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HUK1_MED_1_test | 11723 | 8422 | tubule | TP | leak | 0.837 | 75.46 | 150.9 | 20.2 | 0.219 | 1.29 |
| HUK1_MED_1_test | 10078 | 7574 | glomerulus | TP | leak | 0.905 | 60.96 | 121.9 | 28.0 | 0.144 | 1.20 |
| HUK1_MED_1_test | 9433 | 8356 | glomerulus | TP | leak | 0.956 | 53.41 | 106.8 | 19.9 | 0.051 | 1.08 |
| HUK1_MED_1_test | 11327 | 6585 | glomerulus | TP | ok | 0.977 | 45.85 | 91.7 | 13.9 | 0.013 | 1.03 |
| HUK1_MED_1_test | 11243 | 8363 | tubule | TP | leak | 0.795 | 41.67 | 83.3 | 14.1 | 0.267 | 1.47 |
| HUK1_MED_1_test | 10955 | 8361 | tubule | TP | merge | 0.760 | 36.87 | 73.7 | 4.0 | 0.350 | 1.57 |
| HUK1_MED_1_test | 11815 | 8795 | tubule | TP | leak | 0.930 | 26.76 | 53.5 | 19.9 | 0.086 | 1.13 |
| HUK1_MED_1_test | 10967 | 6910 | tubule | TP | leak | 0.919 | 23.00 | 46.0 | 11.1 | 0.089 | 1.16 |
| HUK1_MED_1_test | 11219 | 8014 | glomerulus | TP | ok | 0.974 | 21.10 | 42.2 | 11.0 | 0.014 | 1.04 |
| HUK1_MED_1_test | 9791 | 7125 | tubule | TP | leak | 0.913 | 17.66 | 35.3 | 14.1 | 0.112 | 1.17 |
| HUK1_MED_1_test | 11049 | 6776 | tubule | TP | ok | 0.968 | 17.20 | 34.4 | 6.0 | 0.001 | 0.98 |
| HUK1_MED_1_test | 9695 | 7891 | tubule | TP | ok | 0.729 | 17.06 | 34.1 | 25.1 | 0.002 | 0.63 |
| HUK1_MED_1_test | 11217 | 7695 | tubule | TP | ok | 0.954 | 13.84 | 27.7 | 8.0 | 0.031 | 1.08 |
| HUK1_MED_1_test | 10584 | 7555 | tubule | TP | leak | 0.864 | 13.82 | 27.6 | 20.0 | 0.145 | 1.30 |
| HUK1_MED_1_test | 12159 | 8597 | glomerulus | TP | ok | 0.976 | 12.53 | 25.1 | 13.0 | 0.016 | 1.04 |
| HUK1_MED_1_test | 10581 | 7269 | tubule | TP | ok | 0.945 | 12.02 | 24.0 | 5.8 | 0.037 | 1.08 |
| HUK1_MED_1_test | 11191 | 7058 | tubule | TP | ok | 0.940 | 11.66 | 19.6 | 23.3 | 0.001 | 0.93 |
| HUK1_MED_1_test | 10986 | 7638 | tubule | TP | ok | 0.948 | 11.64 | 23.3 | 10.0 | 0.038 | 1.10 |
| HUK1_MED_1_test | 9970 | 7866 | tubule | TP | ok | 0.961 | 10.65 | 21.3 | 14.1 | 0.033 | 1.06 |
| HUK1_MED_1_test | 9321 | 6890 | tubule | TP | ok | 0.942 | 10.39 | 20.8 | 10.0 | 0.038 | 1.05 |

## Worst matched objects by leak fraction

| slide | cx | cy | class | status | failure | Dice | HD95 µm | pred→GT px | GT→pred px | leak | area ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HUK1_MED_1_test | 10955 | 8361 | tubule | TP | merge | 0.760 | 36.87 | 73.7 | 4.0 | 0.350 | 1.57 |
| HUK1_MED_1_test | 11243 | 8363 | tubule | TP | leak | 0.795 | 41.67 | 83.3 | 14.1 | 0.267 | 1.47 |
| HUK1_MED_1_test | 11723 | 8422 | tubule | TP | leak | 0.837 | 75.46 | 150.9 | 20.2 | 0.219 | 1.29 |
| HUK1_MED_1_test | 10584 | 7555 | tubule | TP | leak | 0.864 | 13.82 | 27.6 | 20.0 | 0.145 | 1.30 |
| HUK1_MED_1_test | 10078 | 7574 | glomerulus | TP | leak | 0.905 | 60.96 | 121.9 | 28.0 | 0.144 | 1.20 |
| HUK1_MED_1_test | 11473 | 7365 | tubule | TP | leak | 0.844 | 9.12 | 18.2 | 17.5 | 0.139 | 1.37 |
| HUK1_MED_1_test | 9791 | 7125 | tubule | TP | leak | 0.913 | 17.66 | 35.3 | 14.1 | 0.112 | 1.17 |
| HUK1_MED_1_test | 10312 | 7083 | tubule | TP | leak | 0.887 | 7.87 | 15.7 | 15.6 | 0.091 | 1.25 |
| HUK1_MED_1_test | 10967 | 6910 | tubule | TP | leak | 0.919 | 23.00 | 46.0 | 11.1 | 0.089 | 1.16 |
| HUK1_MED_1_test | 11815 | 8795 | tubule | TP | leak | 0.930 | 26.76 | 53.5 | 19.9 | 0.086 | 1.13 |
| HUK1_MED_1_test | 11396 | 7200 | tubule | TP | leak | 0.866 | 6.36 | 12.7 | 11.2 | 0.075 | 1.29 |
| HUK1_MED_1_test | 10506 | 7216 | tubule | TP | leak | 0.893 | 8.00 | 16.0 | 13.1 | 0.071 | 1.20 |
| HUK1_MED_1_test | 9433 | 8356 | glomerulus | TP | leak | 0.956 | 53.41 | 106.8 | 19.9 | 0.051 | 1.08 |
| HUK1_MED_1_test | 10866 | 7528 | tubule | TP | ok | 0.920 | 8.23 | 16.5 | 13.4 | 0.049 | 1.12 |
| HUK1_MED_1_test | 10767 | 8135 | tubule | TP | ok | 0.896 | 5.15 | 10.3 | 9.6 | 0.045 | 1.16 |
| HUK1_MED_1_test | 9195 | 8572 | tubule | TP | ok | 0.931 | 9.68 | 19.4 | 12.7 | 0.044 | 1.14 |
| HUK1_MED_1_test | 10964 | 7936 | tubule | TP | ok | 0.930 | 6.39 | 12.8 | 12.2 | 0.040 | 1.15 |
| HUK1_MED_1_test | 10986 | 7638 | tubule | TP | ok | 0.948 | 11.64 | 23.3 | 10.0 | 0.038 | 1.10 |
| HUK1_MED_1_test | 9321 | 6890 | tubule | TP | ok | 0.942 | 10.39 | 20.8 | 10.0 | 0.038 | 1.05 |
| HUK1_MED_1_test | 11518 | 7938 | tubule | TP | ok | 0.941 | 8.58 | 17.2 | 12.1 | 0.038 | 1.10 |

## Unmatched annotated objects (4; largest first)

| slide | cx | cy | class | failure | area px | best IoU |
|---|---|---|---|---|---|---|
| HUK1_MED_1_test | 8635 | 6939 | tubule | miss | 18623 | 0.000 |
| HUK1_MED_1_test | 12419 | 8809 | tubule | miss | 16731 | 0.000 |
| HUK1_MED_1_test | 11535 | 8204 | tubule | poor_overlap | 13310 | 0.478 |
| HUK1_MED_1_test | 11019 | 8417 | tubule | merge | 5076 | 0.335 |

## Edge cases

### Boundary leakage

| quantity | value |
|---|---|
| n_matched | 134 |
| leak_frac_mean | 0.022 |
| leak_frac_gt_0.05_rate | 0.097 |
| over_reach_asymmetry_px_mean | 6.133 |
| over_reach_asymmetry_px_median | 0.181 |
| area_ratio_median | 1.049 |
| area_ratio_mean | 1.065 |
| pred_solidity_lt_0.85_rate | 0.045 |
| gt_solidity_lt_0.85_rate | 0.022 |
| pred_px_on_trusted_background_frac | 0.051 |

### Small and disconnected components

| quantity | value |
|---|---|
| predictions inside the rectangles (not edge-cut) | 496 |
|   below their class min_area floor | 0 |
|   with more than one connected component | 0 |
|   mean stray area share among those | 0.000 |
| false positives | 1 |
|   fragments on an annotated object | 0 |
|   on trusted background | 1 |
|   area px, quartiles | [27564.0, 27564.0, 27564.0] |

### By ground-truth size

| quartile | area px | n | recall | dice_per_gt | HD95 µm | merge |
|---|---|---|---|---|---|---|
| 1 | 3432–8603 | 35 | 0.971 | 0.911 | 3.34 | 0.029 |
| 2 | 8603–13305 | 34 | 1.000 | 0.947 | 4.57 | 0.029 |
| 3 | 13305–23894 | 34 | 0.912 | 0.856 | 6.73 | 0.000 |
| 4 | 23894–165409 | 35 | 1.000 | 0.955 | 13.73 | 0.000 |

### Stain intensity (observational)

Observational only: staining intensity is confounded with anatomy (medulla stains differently from cortex), so an association here is not evidence of stain sensitivity on its own. The controlled test is --stain-drift.

| pair | Spearman ρ | p | n tiles |
|---|---|---|---|
| h_od,dice_per_gt | 0.007 | 0.983 | 12 |
| h_od,hd95_um_mean | -0.196 | 0.542 | 12 |
| e_od,dice_per_gt | -0.308 | 0.331 | 12 |
| e_od,hd95_um_mean | 0.308 | 0.331 | 12 |

| h_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.003 | 4 | 0.851 | 0.876 | 8.60 |
| 2 | 0.004 | 4 | 0.899 | 0.946 | 6.48 |
| 3 | 0.004 | 4 | 0.865 | 0.889 | 7.77 |

| e_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.019 | 4 | 0.889 | 0.918 | 6.59 |
| 2 | 0.020 | 4 | 0.890 | 0.931 | 6.49 |
| 3 | 0.021 | 4 | 0.845 | 0.874 | 10.20 |
