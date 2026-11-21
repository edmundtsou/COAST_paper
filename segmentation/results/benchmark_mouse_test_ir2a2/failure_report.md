# Segmentation benchmark — failure report

205 annotated objects, 191 scored predictions, 21 tiles of 1024 px over 1 slide(s). TP 183 / FP 8 / FN 22. Brackets are 95% intervals (2000 bootstrap replicates over tiles).

**Read this first**

- Confidence intervals describe spatial sampling variability WITHIN the scored slides. They do not describe generalisation across animals, sections, stain batches or scanners: with fewer than 5 slides the between-slide variance is not estimable and no between-slide standard error is reported.

## Pooled metrics

| metric | estimate [95% CI] |
|---|---|
| PQ | 0.803 [0.759, 0.838] |
| SQ | 0.868 [0.852, 0.886] |
| DQ | 0.924 [0.883, 0.951] |
| recall | 0.893 [0.837, 0.932] |
| precision | 0.958 [0.929, 0.980] |
| dice_per_gt | 0.827 [0.770, 0.869] |
| iou_per_gt | 0.775 [0.718, 0.819] |
| dice_matched | 0.927 [0.917, 0.937] |
| iou_matched | 0.868 [0.852, 0.886] |
| hd95_um_mean | 4.767 [3.747, 6.520] |
| hd95_um_median | 2.203 [2.203, 2.787] |
| hd95_px_mean | 10.818 [8.503, 14.795] |
| assd_um_mean | 1.223 [1.044, 1.522] |
| split_rate | 0.005 [0.000, 0.017] |
| merge_rate | 0.088 [0.051, 0.144] |
| fg_dice_px | 0.945 [0.926, 0.957] |
| fg_iou_px | 0.896 [0.862, 0.918] |
| dice_px[tubule_proximal] | 0.945 [0.919, 0.960] |
| dice_px[tubule_distal] | 0.927 [0.782, 0.936] |
| dice_px[tubule_collecting] | 0.910 [0.791, 0.937] |
| dice_px[glomerulus] | 0.965 [0.959, 0.971] |

HD95 and ASSD are over true positives only; read them next to recall. `dice_per_gt` counts each missed object as 0, `dice_matched` does not.

## Per slide

| slide | n GT | PQ | recall | dice_per_gt | dice_matched | hd95_um_mean | merge_rate |
|---|---|---|---|---|---|---|---|
| IR_2A2_test_casts | 205 | 0.803 [0.759, 0.838] | 0.893 [0.837, 0.932] | 0.827 [0.770, 0.869] | 0.927 [0.917, 0.937] | 4.767 [3.747, 6.520] | 0.088 [0.051, 0.144] |

1 slide(s) scored: between-slide standard error is not estimable; per-slide point estimates are shown instead.

## By ground-truth class

| group | n GT | recall | dice_per_gt | hd95_um_mean | split_rate | merge_rate |
|---|---|---|---|---|---|---|
| tubule_proximal | 124 | 0.911 [0.843, 0.975] | 0.852 [0.781, 0.921] | 4.372 [3.159, 6.388] | 0.008 [0.000, 0.027] | 0.048 [0.000, 0.114] |
| tubule_distal | 19 | 0.895 [0.833, 1.000] | 0.806 [0.749, 0.948] | 6.925 [2.332, 8.986] | 0.000 [0.000, 0.000] | 0.211 [0.000, 0.333] |
| tubule_collecting | 53 | 0.830 [0.625, 1.000] | 0.753 [0.579, 0.973] | 5.261 [0.881, 11.800] | 0.000 [0.000, 0.000] | 0.151 [0.000, 0.375] |
| glomerulus | 9 | 1.000 [1.000, 1.000] | 0.962 [0.956, 0.970] | 3.242 [1.901, 4.833] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

## By annotation source

| group | n GT | recall | dice_per_gt | hd95_um_mean | split_rate | merge_rate |
|---|---|---|---|---|---|---|
| cast | 54 | 0.889 [0.842, 1.000] | 0.822 [0.779, 0.933] | 3.421 [3.398, 4.340] | 0.000 [0.000, 0.000] | 0.037 [0.000, 0.053] |
| intact | 151 | 0.894 [0.821, 0.939] | 0.829 [0.751, 0.877] | 5.246 [3.916, 7.262] | 0.007 [0.000, 0.019] | 0.106 [0.053, 0.176] |

## Failure types (annotated objects)

| type | n | share |
|---|---|---|
| ok | 158 | 77.1% |
| leak | 20 | 9.8% |
| merge | 18 | 8.8% |
| miss | 7 | 3.4% |
| split | 1 | 0.5% |
| poor_overlap | 1 | 0.5% |

`merge` and `split` take precedence over the detection outcome; `miss` is an unmatched object whose best overlap is IoU < 0.10; `leak` is a matched object with more than 5% of the prediction beyond the 5 px ring.

## Worst tiles by Dice (lowest `dice_per_gt`, tiles with ≥ 3 objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| IR_2A2_test_casts | 11342 | 8792 | 8 | 5/1/3 | 0.579 | 3.03 | 5.58 | 3 | 0 | 0.938 |
| IR_2A2_test_casts | 9294 | 12888 | 3 | 2/0/1 | 0.639 | 2.27 | 2.79 | 0 | 0 | 0.956 |
| IR_2A2_test_casts | 7246 | 12888 | 10 | 8/1/2 | 0.732 | 7.69 | 29.27 | 2 | 0 | 0.957 |
| IR_2A2_test_casts | 10318 | 8792 | 9 | 8/1/1 | 0.778 | 11.80 | 33.18 | 1 | 0 | 0.935 |
| IR_2A2_test_casts | 9294 | 10840 | 38 | 32/1/6 | 0.779 | 3.40 | 15.37 | 2 | 0 | 0.897 |
| IR_2A2_test_casts | 9294 | 9816 | 50 | 45/2/5 | 0.826 | 3.83 | 26.50 | 4 | 0 | 0.929 |
| IR_2A2_test_casts | 8270 | 12888 | 13 | 12/0/1 | 0.877 | 5.15 | 22.02 | 2 | 0 | 0.966 |
| IR_2A2_test_casts | 7246 | 11864 | 38 | 36/0/2 | 0.891 | 3.75 | 31.80 | 4 | 0 | 0.958 |
| IR_2A2_test_casts | 8270 | 11864 | 30 | 29/2/1 | 0.895 | 6.99 | 40.26 | 0 | 1 | 0.957 |
| IR_2A2_test_casts | 9294 | 11864 | 4 | 4/0/0 | 0.965 | 2.78 | 6.72 | 0 | 0 | 0.965 |

## Worst tiles by HD95 (highest mean, tiles with ≥ 3 matched objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| IR_2A2_test_casts | 10318 | 8792 | 9 | 8/1/1 | 0.778 | 11.80 | 33.18 | 1 | 0 | 0.935 |
| IR_2A2_test_casts | 7246 | 12888 | 10 | 8/1/2 | 0.732 | 7.69 | 29.27 | 2 | 0 | 0.957 |
| IR_2A2_test_casts | 8270 | 11864 | 30 | 29/2/1 | 0.895 | 6.99 | 40.26 | 0 | 1 | 0.957 |
| IR_2A2_test_casts | 8270 | 12888 | 13 | 12/0/1 | 0.877 | 5.15 | 22.02 | 2 | 0 | 0.966 |
| IR_2A2_test_casts | 9294 | 9816 | 50 | 45/2/5 | 0.826 | 3.83 | 26.50 | 4 | 0 | 0.929 |
| IR_2A2_test_casts | 7246 | 11864 | 38 | 36/0/2 | 0.891 | 3.75 | 31.80 | 4 | 0 | 0.958 |
| IR_2A2_test_casts | 9294 | 10840 | 38 | 32/1/6 | 0.779 | 3.40 | 15.37 | 2 | 0 | 0.897 |
| IR_2A2_test_casts | 11342 | 8792 | 8 | 5/1/3 | 0.579 | 3.03 | 5.58 | 3 | 0 | 0.938 |
| IR_2A2_test_casts | 9294 | 11864 | 4 | 4/0/0 | 0.965 | 2.78 | 6.72 | 0 | 0 | 0.965 |

10 of 21 tiles have ≥ 3 annotated objects and are ranked. Coordinates are the tile's top-left corner in working pixels.

## Worst matched objects by HD95

| slide | cx | cy | class | status | failure | Dice | HD95 µm | pred→GT px | GT→pred px | leak | area ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IR_2A2_test_casts | 8799 | 12520 | tubule_proximal | TP | leak | 0.748 | 40.26 | 91.4 | 18.0 | 0.368 | 1.61 |
| IR_2A2_test_casts | 9188 | 12615 | tubule_proximal | TP | leak | 0.691 | 35.05 | 79.5 | 23.4 | 0.427 | 1.81 |
| IR_2A2_test_casts | 11247 | 9194 | tubule_collecting | TP | leak | 0.704 | 33.18 | 75.3 | 9.1 | 0.396 | 1.63 |
| IR_2A2_test_casts | 8090 | 12350 | tubule_distal | TP | merge | 0.731 | 31.80 | 72.2 | 10.2 | 0.329 | 1.55 |
| IR_2A2_test_casts | 10973 | 9258 | tubule_collecting | TP | leak | 0.827 | 30.51 | 69.2 | 6.2 | 0.216 | 1.39 |
| IR_2A2_test_casts | 7531 | 12948 | tubule_proximal | TP | merge | 0.677 | 29.27 | 66.4 | 20.8 | 0.427 | 1.78 |
| IR_2A2_test_casts | 9160 | 12738 | tubule_proximal | TP | leak | 0.765 | 27.06 | 61.4 | 7.1 | 0.335 | 1.58 |
| IR_2A2_test_casts | 10100 | 10389 | tubule_collecting | TP | leak | 0.765 | 26.50 | 60.1 | 8.3 | 0.286 | 1.59 |
| IR_2A2_test_casts | 8313 | 12234 | tubule_distal | TP | leak | 0.818 | 24.24 | 55.0 | 23.5 | 0.235 | 1.38 |
| IR_2A2_test_casts | 9197 | 13076 | tubule_proximal | TP | merge | 0.885 | 22.02 | 29.7 | 50.0 | 0.158 | 1.18 |
| IR_2A2_test_casts | 9961 | 10323 | tubule_collecting | TP | leak | 0.695 | 20.47 | 46.5 | 10.9 | 0.369 | 1.79 |
| IR_2A2_test_casts | 8167 | 12409 | tubule_distal | TP | merge | 0.765 | 19.04 | 43.2 | 13.7 | 0.310 | 1.47 |
| IR_2A2_test_casts | 10005 | 10777 | tubule_proximal | TP | leak | 0.701 | 18.93 | 43.0 | 5.7 | 0.386 | 1.61 |
| IR_2A2_test_casts | 7999 | 12335 | tubule_proximal | TP | leak | 0.865 | 16.33 | 37.0 | 19.7 | 0.171 | 1.29 |
| IR_2A2_test_casts | 9522 | 10883 | tubule_proximal | TP | leak | 0.732 | 15.37 | 34.9 | 8.2 | 0.232 | 1.43 |
| IR_2A2_test_casts | 7443 | 13115 | tubule_proximal | TP | ok | 0.927 | 15.16 | 16.0 | 34.4 | 0.001 | 0.94 |
| IR_2A2_test_casts | 8928 | 13146 | tubule_proximal | TP | leak | 0.896 | 15.02 | 34.1 | 9.7 | 0.101 | 1.16 |
| IR_2A2_test_casts | 9389 | 10966 | tubule_proximal | TP | merge | 0.853 | 14.19 | 32.2 | 9.9 | 0.142 | 1.25 |
| IR_2A2_test_casts | 11072 | 9268 | tubule_collecting | TP | ok | 0.892 | 9.37 | 8.1 | 21.3 | 0.014 | 1.04 |
| IR_2A2_test_casts | 8449 | 12607 | tubule_distal | TP | leak | 0.860 | 8.81 | 20.0 | 9.4 | 0.112 | 1.26 |

## Worst matched objects by leak fraction

| slide | cx | cy | class | status | failure | Dice | HD95 µm | pred→GT px | GT→pred px | leak | area ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IR_2A2_test_casts | 7531 | 12948 | tubule_proximal | TP | merge | 0.677 | 29.27 | 66.4 | 20.8 | 0.427 | 1.78 |
| IR_2A2_test_casts | 9188 | 12615 | tubule_proximal | TP | leak | 0.691 | 35.05 | 79.5 | 23.4 | 0.427 | 1.81 |
| IR_2A2_test_casts | 11247 | 9194 | tubule_collecting | TP | leak | 0.704 | 33.18 | 75.3 | 9.1 | 0.396 | 1.63 |
| IR_2A2_test_casts | 10005 | 10777 | tubule_proximal | TP | leak | 0.701 | 18.93 | 43.0 | 5.7 | 0.386 | 1.61 |
| IR_2A2_test_casts | 9961 | 10323 | tubule_collecting | TP | leak | 0.695 | 20.47 | 46.5 | 10.9 | 0.369 | 1.79 |
| IR_2A2_test_casts | 8799 | 12520 | tubule_proximal | TP | leak | 0.748 | 40.26 | 91.4 | 18.0 | 0.368 | 1.61 |
| IR_2A2_test_casts | 9160 | 12738 | tubule_proximal | TP | leak | 0.765 | 27.06 | 61.4 | 7.1 | 0.335 | 1.58 |
| IR_2A2_test_casts | 8090 | 12350 | tubule_distal | TP | merge | 0.731 | 31.80 | 72.2 | 10.2 | 0.329 | 1.55 |
| IR_2A2_test_casts | 8167 | 12409 | tubule_distal | TP | merge | 0.765 | 19.04 | 43.2 | 13.7 | 0.310 | 1.47 |
| IR_2A2_test_casts | 10100 | 10389 | tubule_collecting | TP | leak | 0.765 | 26.50 | 60.1 | 8.3 | 0.286 | 1.59 |
| IR_2A2_test_casts | 8313 | 12234 | tubule_distal | TP | leak | 0.818 | 24.24 | 55.0 | 23.5 | 0.235 | 1.38 |
| IR_2A2_test_casts | 9522 | 10883 | tubule_proximal | TP | leak | 0.732 | 15.37 | 34.9 | 8.2 | 0.232 | 1.43 |
| IR_2A2_test_casts | 10973 | 9258 | tubule_collecting | TP | leak | 0.827 | 30.51 | 69.2 | 6.2 | 0.216 | 1.39 |
| IR_2A2_test_casts | 7999 | 12335 | tubule_proximal | TP | leak | 0.865 | 16.33 | 37.0 | 19.7 | 0.171 | 1.29 |
| IR_2A2_test_casts | 9197 | 13076 | tubule_proximal | TP | merge | 0.885 | 22.02 | 29.7 | 50.0 | 0.158 | 1.18 |
| IR_2A2_test_casts | 9389 | 10966 | tubule_proximal | TP | merge | 0.853 | 14.19 | 32.2 | 9.9 | 0.142 | 1.25 |
| IR_2A2_test_casts | 10038 | 10877 | tubule_proximal | TP | leak | 0.875 | 8.00 | 18.2 | 11.0 | 0.121 | 1.13 |
| IR_2A2_test_casts | 8449 | 12607 | tubule_distal | TP | leak | 0.860 | 8.81 | 20.0 | 9.4 | 0.112 | 1.26 |
| IR_2A2_test_casts | 8928 | 13146 | tubule_proximal | TP | leak | 0.896 | 15.02 | 34.1 | 9.7 | 0.101 | 1.16 |
| IR_2A2_test_casts | 8510 | 12486 | tubule_distal | TP | leak | 0.904 | 7.01 | 15.9 | 10.0 | 0.082 | 1.18 |

## Unmatched annotated objects (22; largest first)

| slide | cx | cy | class | failure | area px | best IoU |
|---|---|---|---|---|---|---|
| IR_2A2_test_casts | 8564 | 12748 | tubule_proximal | split | 14205 | 0.413 |
| IR_2A2_test_casts | 11292 | 9060 | tubule_collecting | merge | 13190 | 0.455 |
| IR_2A2_test_casts | 9508 | 12947 | tubule_proximal | miss | 10158 | 0.000 |
| IR_2A2_test_casts | 7704 | 13183 | tubule_proximal | miss | 7804 | 0.000 |
| IR_2A2_test_casts | 11387 | 9170 | tubule_collecting | merge | 5387 | 0.488 |
| IR_2A2_test_casts | 11366 | 9238 | tubule_collecting | merge | 5201 | 0.181 |
| IR_2A2_test_casts | 9233 | 13089 | tubule_proximal | merge | 5162 | 0.165 |
| IR_2A2_test_casts | 11407 | 9085 | tubule_collecting | merge | 4693 | 0.412 |
| IR_2A2_test_casts | 7585 | 12913 | tubule_proximal | merge | 4090 | 0.430 |
| IR_2A2_test_casts | 9906 | 11257 | tubule_proximal | poor_overlap | 4032 | 0.499 |
| IR_2A2_test_casts | 10014 | 9932 | tubule_collecting | merge | 3721 | 0.143 |
| IR_2A2_test_casts | 9453 | 11031 | tubule_proximal | merge | 3711 | 0.111 |
| IR_2A2_test_casts | 10086 | 11098 | tubule_proximal | miss | 3108 | 0.000 |
| IR_2A2_test_casts | 9962 | 9986 | tubule_collecting | merge | 3106 | 0.287 |
| IR_2A2_test_casts | 8188 | 12237 | tubule_distal | merge | 2955 | 0.204 |
| IR_2A2_test_casts | 9870 | 10863 | tubule_proximal | miss | 2797 | 0.000 |
| IR_2A2_test_casts | 9997 | 10040 | tubule_collecting | merge | 2792 | 0.489 |
| IR_2A2_test_casts | 8197 | 12445 | tubule_distal | merge | 2271 | 0.321 |
| IR_2A2_test_casts | 9988 | 11017 | tubule_proximal | miss | 2164 | 0.000 |
| IR_2A2_test_casts | 10259 | 11012 | tubule_proximal | miss | 2124 | 0.000 |

## Edge cases

### Boundary leakage

| quantity | value |
|---|---|
| n_matched | 183 |
| leak_frac_mean | 0.034 |
| leak_frac_gt_0.05_rate | 0.137 |
| over_reach_asymmetry_px_mean | 4.086 |
| over_reach_asymmetry_px_median | 0.099 |
| area_ratio_median | 1.022 |
| area_ratio_mean | 1.064 |
| pred_solidity_lt_0.85_rate | 0.087 |
| gt_solidity_lt_0.85_rate | 0.059 |
| pred_px_on_trusted_background_frac | 0.061 |

### Small and disconnected components

| quantity | value |
|---|---|
| predictions inside the rectangles (not edge-cut) | 2223 |
|   below their class min_area floor | 0 |
|   with more than one connected component | 0 |
|   mean stray area share among those | 0.000 |
| false positives | 8 |
|   fragments on an annotated object | 7 |
|   on trusted background | 1 |
|   area px, quartiles | [4249.5, 7590.5, 11674.75] |

### By ground-truth size

| quartile | area px | n | recall | dice_per_gt | HD95 µm | merge |
|---|---|---|---|---|---|---|
| 1 | 1252–3217 | 51 | 0.804 | 0.735 | 3.01 | 0.098 |
| 2 | 3217–4975 | 51 | 0.902 | 0.832 | 4.15 | 0.098 |
| 3 | 4975–9269 | 51 | 0.922 | 0.857 | 5.22 | 0.098 |
| 4 | 9269–34303 | 52 | 0.942 | 0.883 | 6.39 | 0.058 |

### Stain intensity (observational)

Observational only: staining intensity is confounded with anatomy (medulla stains differently from cortex), so an association here is not evidence of stain sensitivity on its own. The controlled test is --stain-drift.

| pair | Spearman ρ | p | n tiles |
|---|---|---|---|
| h_od,dice_per_gt | 0.055 | 0.881 | 10 |
| h_od,hd95_um_mean | 0.345 | 0.328 | 10 |
| e_od,dice_per_gt | 0.152 | 0.676 | 10 |
| e_od,hd95_um_mean | -0.212 | 0.556 | 10 |

| h_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.010 | 3 | 0.799 | 0.795 | 3.81 |
| 2 | 0.010 | 3 | 0.787 | 0.828 | 4.87 |
| 3 | 0.012 | 4 | 0.815 | 0.845 | 5.31 |

| e_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.042 | 3 | 0.760 | 0.790 | 4.86 |
| 2 | 0.046 | 3 | 0.825 | 0.852 | 4.60 |
| 3 | 0.049 | 4 | 0.818 | 0.817 | 5.35 |
