# Segmentation benchmark — failure report

355 annotated objects, 327 scored predictions, 29 tiles of 1024 px over 2 slide(s). TP 315 / FP 12 / FN 40. Brackets are 95% intervals (2000 bootstrap replicates over tiles).

**Read this first**

- Confidence intervals describe spatial sampling variability WITHIN the scored slides. They do not describe generalisation across animals, sections, stain batches or scanners: with fewer than 5 slides the between-slide variance is not estimable and no between-slide standard error is reported.

## Pooled metrics

| metric | estimate [95% CI] |
|---|---|
| PQ | 0.804 [0.776, 0.831] |
| SQ | 0.870 [0.859, 0.886] |
| DQ | 0.924 [0.899, 0.944] |
| recall | 0.887 [0.851, 0.918] |
| precision | 0.963 [0.946, 0.978] |
| dice_per_gt | 0.823 [0.786, 0.856] |
| iou_per_gt | 0.772 [0.735, 0.806] |
| dice_matched | 0.927 [0.920, 0.937] |
| iou_matched | 0.870 [0.859, 0.886] |
| hd95_um_mean | 5.804 [4.459, 7.507] |
| hd95_um_median | 2.234 [2.203, 2.570] |
| hd95_px_mean | 13.170 [10.119, 17.034] |
| assd_um_mean | 1.360 [1.162, 1.616] |
| split_rate | 0.006 [0.000, 0.013] |
| merge_rate | 0.118 [0.077, 0.175] |
| fg_dice_px | 0.951 [0.941, 0.958] |
| fg_iou_px | 0.906 [0.888, 0.919] |
| dice_px[tubule_proximal] | 0.947 [0.928, 0.960] |
| dice_px[tubule_distal] | 0.871 [0.796, 0.926] |
| dice_px[tubule_collecting] | 0.930 [0.893, 0.945] |
| dice_px[glomerulus] | 0.950 [0.940, 0.965] |

HD95 and ASSD are over true positives only; read them next to recall. `dice_per_gt` counts each missed object as 0, `dice_matched` does not.

## Per slide

| slide | n GT | PQ | recall | dice_per_gt | dice_matched | hd95_um_mean | merge_rate |
|---|---|---|---|---|---|---|---|
| Ctrl_1A2_test | 150 | 0.806 [0.765, 0.854] | 0.880 [0.821, 0.929] | 0.817 [0.758, 0.872] | 0.929 [0.918, 0.946] | 7.241 [4.316, 10.284] | 0.160 [0.083, 0.263] |
| IR_2A2_test_casts | 205 | 0.803 [0.759, 0.838] | 0.893 [0.837, 0.932] | 0.827 [0.770, 0.869] | 0.927 [0.917, 0.937] | 4.767 [3.747, 6.520] | 0.088 [0.051, 0.144] |

2 slide(s) scored: between-slide standard error is not estimable; per-slide point estimates are shown instead.

## By ground-truth class

| group | n GT | recall | dice_per_gt | hd95_um_mean | split_rate | merge_rate |
|---|---|---|---|---|---|---|
| tubule_proximal | 194 | 0.902 [0.845, 0.970] | 0.845 [0.785, 0.917] | 5.595 [3.657, 8.092] | 0.005 [0.000, 0.017] | 0.098 [0.020, 0.194] |
| tubule_distal | 34 | 0.853 [0.792, 1.000] | 0.770 [0.727, 0.880] | 7.362 [5.292, 10.325] | 0.000 [0.000, 0.000] | 0.235 [0.000, 0.321] |
| tubule_collecting | 106 | 0.858 [0.706, 0.909] | 0.783 [0.658, 0.826] | 5.928 [2.998, 8.150] | 0.009 [0.000, 0.020] | 0.142 [0.109, 0.294] |
| glomerulus | 21 | 0.952 [0.875, 1.000] | 0.905 [0.827, 0.960] | 4.806 [2.707, 7.078] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

## By annotation source

| group | n GT | recall | dice_per_gt | hd95_um_mean | split_rate | merge_rate |
|---|---|---|---|---|---|---|
| cast | 54 | 0.889 [0.842, 1.000] | 0.822 [0.779, 0.933] | 3.421 [3.398, 4.340] | 0.000 [0.000, 0.000] | 0.037 [0.000, 0.053] |
| intact | 151 | 0.894 [0.821, 0.939] | 0.829 [0.755, 0.877] | 5.246 [3.896, 7.239] | 0.007 [0.000, 0.019] | 0.106 [0.054, 0.174] |

## Failure types (annotated objects)

| type | n | share |
|---|---|---|
| ok | 269 | 75.8% |
| merge | 42 | 11.8% |
| leak | 32 | 9.0% |
| miss | 9 | 2.5% |
| poor_overlap | 2 | 0.6% |
| split | 1 | 0.3% |

`merge` and `split` take precedence over the detection outcome; `miss` is an unmatched object whose best overlap is IoU < 0.10; `leak` is a matched object with more than 5% of the prediction beyond the 5 px ring.

## Worst tiles by Dice (lowest `dice_per_gt`, tiles with ≥ 3 objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| IR_2A2_test_casts | 11342 | 8792 | 8 | 5/1/3 | 0.579 | 3.03 | 5.58 | 3 | 0 | 0.938 |
| IR_2A2_test_casts | 9294 | 12888 | 3 | 2/0/1 | 0.639 | 2.27 | 2.79 | 0 | 0 | 0.956 |
| Ctrl_1A2_test | 11132 | 11809 | 8 | 6/1/2 | 0.705 | 3.29 | 10.14 | 2 | 0 | 0.949 |
| Ctrl_1A2_test | 9084 | 11809 | 31 | 24/1/7 | 0.706 | 14.03 | 98.24 | 11 | 0 | 0.966 |
| IR_2A2_test_casts | 7246 | 12888 | 10 | 8/1/2 | 0.732 | 7.69 | 29.27 | 2 | 0 | 0.957 |
| IR_2A2_test_casts | 10318 | 8792 | 9 | 8/1/1 | 0.778 | 11.80 | 33.18 | 1 | 0 | 0.935 |
| IR_2A2_test_casts | 9294 | 10840 | 38 | 32/1/6 | 0.779 | 3.40 | 15.37 | 2 | 0 | 0.897 |
| IR_2A2_test_casts | 9294 | 9816 | 50 | 45/2/5 | 0.826 | 3.83 | 26.50 | 4 | 0 | 0.929 |
| Ctrl_1A2_test | 11132 | 10785 | 45 | 41/1/4 | 0.833 | 7.03 | 47.85 | 5 | 1 | 0.948 |
| Ctrl_1A2_test | 8060 | 12833 | 20 | 18/1/2 | 0.840 | 5.25 | 26.52 | 2 | 0 | 0.945 |
| Ctrl_1A2_test | 9084 | 12833 | 30 | 27/0/3 | 0.852 | 6.36 | 63.93 | 4 | 0 | 0.954 |
| IR_2A2_test_casts | 8270 | 12888 | 13 | 12/0/1 | 0.877 | 5.15 | 22.02 | 2 | 0 | 0.966 |
| IR_2A2_test_casts | 7246 | 11864 | 38 | 36/0/2 | 0.891 | 3.75 | 31.80 | 4 | 0 | 0.958 |
| IR_2A2_test_casts | 8270 | 11864 | 30 | 29/2/1 | 0.895 | 6.99 | 40.26 | 0 | 1 | 0.957 |
| Ctrl_1A2_test | 8060 | 11809 | 10 | 10/0/0 | 0.951 | 2.89 | 6.14 | 0 | 0 | 0.962 |
| Ctrl_1A2_test | 10108 | 11809 | 4 | 4/0/0 | 0.957 | 3.01 | 5.99 | 0 | 0 | 0.952 |
| IR_2A2_test_casts | 9294 | 11864 | 4 | 4/0/0 | 0.965 | 2.78 | 6.72 | 0 | 0 | 0.965 |

## Worst tiles by HD95 (highest mean, tiles with ≥ 3 matched objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| Ctrl_1A2_test | 9084 | 11809 | 31 | 24/1/7 | 0.706 | 14.03 | 98.24 | 11 | 0 | 0.966 |
| IR_2A2_test_casts | 10318 | 8792 | 9 | 8/1/1 | 0.778 | 11.80 | 33.18 | 1 | 0 | 0.935 |
| IR_2A2_test_casts | 7246 | 12888 | 10 | 8/1/2 | 0.732 | 7.69 | 29.27 | 2 | 0 | 0.957 |
| Ctrl_1A2_test | 11132 | 10785 | 45 | 41/1/4 | 0.833 | 7.03 | 47.85 | 5 | 1 | 0.948 |
| IR_2A2_test_casts | 8270 | 11864 | 30 | 29/2/1 | 0.895 | 6.99 | 40.26 | 0 | 1 | 0.957 |
| Ctrl_1A2_test | 9084 | 12833 | 30 | 27/0/3 | 0.852 | 6.36 | 63.93 | 4 | 0 | 0.954 |
| Ctrl_1A2_test | 8060 | 12833 | 20 | 18/1/2 | 0.840 | 5.25 | 26.52 | 2 | 0 | 0.945 |
| IR_2A2_test_casts | 8270 | 12888 | 13 | 12/0/1 | 0.877 | 5.15 | 22.02 | 2 | 0 | 0.966 |
| IR_2A2_test_casts | 9294 | 9816 | 50 | 45/2/5 | 0.826 | 3.83 | 26.50 | 4 | 0 | 0.929 |
| IR_2A2_test_casts | 7246 | 11864 | 38 | 36/0/2 | 0.891 | 3.75 | 31.80 | 4 | 0 | 0.958 |
| IR_2A2_test_casts | 9294 | 10840 | 38 | 32/1/6 | 0.779 | 3.40 | 15.37 | 2 | 0 | 0.897 |
| Ctrl_1A2_test | 11132 | 11809 | 8 | 6/1/2 | 0.705 | 3.29 | 10.14 | 2 | 0 | 0.949 |
| IR_2A2_test_casts | 11342 | 8792 | 8 | 5/1/3 | 0.579 | 3.03 | 5.58 | 3 | 0 | 0.938 |
| Ctrl_1A2_test | 10108 | 11809 | 4 | 4/0/0 | 0.957 | 3.01 | 5.99 | 0 | 0 | 0.952 |
| Ctrl_1A2_test | 8060 | 11809 | 10 | 10/0/0 | 0.951 | 2.89 | 6.14 | 0 | 0 | 0.962 |
| IR_2A2_test_casts | 9294 | 11864 | 4 | 4/0/0 | 0.965 | 2.78 | 6.72 | 0 | 0 | 0.965 |

17 of 29 tiles have ≥ 3 annotated objects and are ranked. Coordinates are the tile's top-left corner in working pixels.

## Worst matched objects by HD95

| slide | cx | cy | class | status | failure | Dice | HD95 µm | pred→GT px | GT→pred px | leak | area ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Ctrl_1A2_test | 9708 | 12312 | tubule_proximal | TP | merge | 0.690 | 98.24 | 222.9 | 19.4 | 0.440 | 1.86 |
| Ctrl_1A2_test | 9525 | 12589 | tubule_proximal | TP | merge | 0.808 | 76.62 | 173.9 | 5.0 | 0.288 | 1.45 |
| Ctrl_1A2_test | 9289 | 13152 | tubule_proximal | TP | merge | 0.728 | 63.93 | 145.1 | 19.0 | 0.389 | 1.71 |
| Ctrl_1A2_test | 11617 | 10969 | tubule_collecting | TP | merge | 0.811 | 47.85 | 108.6 | 6.9 | 0.270 | 1.39 |
| Ctrl_1A2_test | 9668 | 12106 | tubule_proximal | TP | merge | 0.757 | 44.04 | 99.9 | 16.3 | 0.352 | 1.63 |
| Ctrl_1A2_test | 11725 | 11101 | tubule_collecting | TP | leak | 0.837 | 41.79 | 94.8 | 7.2 | 0.218 | 1.35 |
| Ctrl_1A2_test | 11913 | 11206 | tubule_collecting | TP | leak | 0.797 | 40.82 | 92.6 | 7.8 | 0.288 | 1.43 |
| IR_2A2_test_casts | 8799 | 12520 | tubule_proximal | TP | leak | 0.748 | 40.26 | 91.4 | 18.0 | 0.368 | 1.61 |
| IR_2A2_test_casts | 9188 | 12615 | tubule_proximal | TP | leak | 0.691 | 35.05 | 79.5 | 23.4 | 0.427 | 1.81 |
| IR_2A2_test_casts | 11247 | 9194 | tubule_collecting | TP | leak | 0.704 | 33.18 | 75.3 | 9.1 | 0.396 | 1.63 |
| IR_2A2_test_casts | 8090 | 12350 | tubule_distal | TP | merge | 0.731 | 31.80 | 72.2 | 10.2 | 0.329 | 1.55 |
| IR_2A2_test_casts | 10973 | 9258 | tubule_collecting | TP | leak | 0.827 | 30.51 | 69.2 | 6.2 | 0.216 | 1.39 |
| IR_2A2_test_casts | 7531 | 12948 | tubule_proximal | TP | merge | 0.677 | 29.27 | 66.4 | 20.8 | 0.427 | 1.78 |
| IR_2A2_test_casts | 9160 | 12738 | tubule_proximal | TP | leak | 0.765 | 27.06 | 61.4 | 7.1 | 0.335 | 1.58 |
| Ctrl_1A2_test | 8866 | 13349 | tubule_proximal | TP | leak | 0.853 | 26.52 | 60.2 | 13.4 | 0.194 | 1.32 |
| IR_2A2_test_casts | 10100 | 10389 | tubule_collecting | TP | leak | 0.765 | 26.50 | 60.1 | 8.3 | 0.286 | 1.59 |
| Ctrl_1A2_test | 9405 | 12396 | tubule_proximal | TP | merge | 0.677 | 25.12 | 57.0 | 24.5 | 0.404 | 1.67 |
| IR_2A2_test_casts | 8313 | 12234 | tubule_distal | TP | leak | 0.818 | 24.24 | 55.0 | 23.5 | 0.235 | 1.38 |
| Ctrl_1A2_test | 9686 | 12488 | tubule_distal | TP | leak | 0.842 | 24.01 | 54.5 | 7.1 | 0.193 | 1.25 |
| Ctrl_1A2_test | 11591 | 11551 | tubule_collecting | TP | merge | 0.668 | 23.42 | 53.1 | 10.2 | 0.419 | 1.95 |

## Worst matched objects by leak fraction

| slide | cx | cy | class | status | failure | Dice | HD95 µm | pred→GT px | GT→pred px | leak | area ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Ctrl_1A2_test | 9708 | 12312 | tubule_proximal | TP | merge | 0.690 | 98.24 | 222.9 | 19.4 | 0.440 | 1.86 |
| IR_2A2_test_casts | 7531 | 12948 | tubule_proximal | TP | merge | 0.677 | 29.27 | 66.4 | 20.8 | 0.427 | 1.78 |
| IR_2A2_test_casts | 9188 | 12615 | tubule_proximal | TP | leak | 0.691 | 35.05 | 79.5 | 23.4 | 0.427 | 1.81 |
| Ctrl_1A2_test | 11591 | 11551 | tubule_collecting | TP | merge | 0.668 | 23.42 | 53.1 | 10.2 | 0.419 | 1.95 |
| Ctrl_1A2_test | 9405 | 12396 | tubule_proximal | TP | merge | 0.677 | 25.12 | 57.0 | 24.5 | 0.404 | 1.67 |
| IR_2A2_test_casts | 11247 | 9194 | tubule_collecting | TP | leak | 0.704 | 33.18 | 75.3 | 9.1 | 0.396 | 1.63 |
| Ctrl_1A2_test | 9289 | 13152 | tubule_proximal | TP | merge | 0.728 | 63.93 | 145.1 | 19.0 | 0.389 | 1.71 |
| IR_2A2_test_casts | 10005 | 10777 | tubule_proximal | TP | leak | 0.701 | 18.93 | 43.0 | 5.7 | 0.386 | 1.61 |
| IR_2A2_test_casts | 9961 | 10323 | tubule_collecting | TP | leak | 0.695 | 20.47 | 46.5 | 10.9 | 0.369 | 1.79 |
| IR_2A2_test_casts | 8799 | 12520 | tubule_proximal | TP | leak | 0.748 | 40.26 | 91.4 | 18.0 | 0.368 | 1.61 |
| Ctrl_1A2_test | 9668 | 12106 | tubule_proximal | TP | merge | 0.757 | 44.04 | 99.9 | 16.3 | 0.352 | 1.63 |
| IR_2A2_test_casts | 9160 | 12738 | tubule_proximal | TP | leak | 0.765 | 27.06 | 61.4 | 7.1 | 0.335 | 1.58 |
| IR_2A2_test_casts | 8090 | 12350 | tubule_distal | TP | merge | 0.731 | 31.80 | 72.2 | 10.2 | 0.329 | 1.55 |
| IR_2A2_test_casts | 8167 | 12409 | tubule_distal | TP | merge | 0.765 | 19.04 | 43.2 | 13.7 | 0.310 | 1.47 |
| Ctrl_1A2_test | 11742 | 11621 | tubule_collecting | TP | leak | 0.769 | 22.34 | 50.7 | 14.5 | 0.305 | 1.52 |
| Ctrl_1A2_test | 9025 | 12924 | tubule_distal | TP | merge | 0.753 | 23.06 | 52.3 | 21.2 | 0.289 | 1.54 |
| Ctrl_1A2_test | 9525 | 12589 | tubule_proximal | TP | merge | 0.808 | 76.62 | 173.9 | 5.0 | 0.288 | 1.45 |
| Ctrl_1A2_test | 11913 | 11206 | tubule_collecting | TP | leak | 0.797 | 40.82 | 92.6 | 7.8 | 0.288 | 1.43 |
| IR_2A2_test_casts | 10100 | 10389 | tubule_collecting | TP | leak | 0.765 | 26.50 | 60.1 | 8.3 | 0.286 | 1.59 |
| Ctrl_1A2_test | 11617 | 10969 | tubule_collecting | TP | merge | 0.811 | 47.85 | 108.6 | 6.9 | 0.270 | 1.39 |

## Unmatched annotated objects (40; largest first)

| slide | cx | cy | class | failure | area px | best IoU |
|---|---|---|---|---|---|---|
| Ctrl_1A2_test | 9919 | 12047 | tubule_proximal | merge | 17319 | 0.269 |
| Ctrl_1A2_test | 9623 | 13702 | tubule_distal | miss | 14354 | 0.000 |
| IR_2A2_test_casts | 8564 | 12748 | tubule_proximal | split | 14205 | 0.413 |
| IR_2A2_test_casts | 11292 | 9060 | tubule_collecting | merge | 13190 | 0.455 |
| Ctrl_1A2_test | 9091 | 12335 | tubule_proximal | merge | 12770 | 0.287 |
| Ctrl_1A2_test | 9824 | 12487 | tubule_proximal | merge | 12589 | 0.265 |
| Ctrl_1A2_test | 9521 | 12479 | tubule_proximal | merge | 10459 | 0.159 |
| Ctrl_1A2_test | 9426 | 13066 | tubule_proximal | merge | 10371 | 0.377 |
| IR_2A2_test_casts | 9508 | 12947 | tubule_proximal | miss | 10158 | 0.000 |
| IR_2A2_test_casts | 7704 | 13183 | tubule_proximal | miss | 7804 | 0.000 |
| Ctrl_1A2_test | 9105 | 12495 | tubule_proximal | merge | 7623 | 0.171 |
| Ctrl_1A2_test | 11482 | 11096 | tubule_collecting | merge | 7540 | 0.305 |
| Ctrl_1A2_test | 11635 | 11769 | tubule_collecting | merge | 7128 | 0.427 |
| Ctrl_1A2_test | 9008 | 13639 | glomerulus | poor_overlap | 6853 | 0.452 |
| Ctrl_1A2_test | 9560 | 12191 | tubule_proximal | merge | 6708 | 0.328 |
| IR_2A2_test_casts | 11387 | 9170 | tubule_collecting | merge | 5387 | 0.488 |
| IR_2A2_test_casts | 11366 | 9238 | tubule_collecting | merge | 5201 | 0.181 |
| IR_2A2_test_casts | 9233 | 13089 | tubule_proximal | merge | 5162 | 0.165 |
| Ctrl_1A2_test | 9469 | 12366 | tubule_proximal | merge | 5113 | 0.382 |
| IR_2A2_test_casts | 11407 | 9085 | tubule_collecting | merge | 4693 | 0.412 |

## Edge cases

### Boundary leakage

| quantity | value |
|---|---|
| n_matched | 315 |
| leak_frac_mean | 0.037 |
| leak_frac_gt_0.05_rate | 0.146 |
| over_reach_asymmetry_px_mean | 6.565 |
| over_reach_asymmetry_px_median | 0.228 |
| area_ratio_median | 1.022 |
| area_ratio_mean | 1.071 |
| pred_solidity_lt_0.85_rate | 0.130 |
| gt_solidity_lt_0.85_rate | 0.101 |
| pred_px_on_trusted_background_frac | 0.056 |

### Small and disconnected components

| quantity | value |
|---|---|
| predictions inside the rectangles (not edge-cut) | 3110 |
|   below their class min_area floor | 0 |
|   with more than one connected component | 0 |
|   mean stray area share among those | 0.000 |
| false positives | 12 |
|   fragments on an annotated object | 10 |
|   on trusted background | 2 |
|   area px, quartiles | [2974.5, 7590.5, 15454.75] |

### By ground-truth size

| quartile | area px | n | recall | dice_per_gt | HD95 µm | merge |
|---|---|---|---|---|---|---|
| 1 | 1252–3588 | 89 | 0.843 | 0.775 | 3.05 | 0.101 |
| 2 | 3588–6371 | 88 | 0.875 | 0.803 | 5.06 | 0.148 |
| 3 | 6371–10364 | 89 | 0.921 | 0.864 | 4.82 | 0.067 |
| 4 | 10364–36737 | 89 | 0.910 | 0.849 | 10.06 | 0.157 |

### Stain intensity (observational)

Observational only: staining intensity is confounded with anatomy (medulla stains differently from cortex), so an association here is not evidence of stain sensitivity on its own. The controlled test is --stain-drift.

| pair | Spearman ρ | p | n tiles |
|---|---|---|---|
| h_od,dice_per_gt | -0.110 | 0.673 | 17 |
| h_od,hd95_um_mean | 0.228 | 0.379 | 17 |
| e_od,dice_per_gt | 0.346 | 0.174 | 17 |
| e_od,hd95_um_mean | -0.248 | 0.338 | 17 |

| h_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.008 | 6 | 0.807 | 0.808 | 7.46 |
| 2 | 0.010 | 5 | 0.793 | 0.803 | 4.84 |
| 3 | 0.012 | 6 | 0.805 | 0.837 | 5.33 |

| e_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.041 | 6 | 0.773 | 0.795 | 5.10 |
| 2 | 0.046 | 5 | 0.826 | 0.842 | 7.15 |
| 3 | 0.049 | 6 | 0.831 | 0.847 | 4.86 |
