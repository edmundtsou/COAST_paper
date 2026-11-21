# Segmentation benchmark — failure report

150 annotated objects, 136 scored predictions, 8 tiles of 1024 px over 1 slide(s). TP 132 / FP 4 / FN 18. Brackets are 95% intervals (2000 bootstrap replicates over tiles).

**Read this first**

- Confidence intervals describe spatial sampling variability WITHIN the scored slides. They do not describe generalisation across animals, sections, stain batches or scanners: with fewer than 5 slides the between-slide variance is not estimable and no between-slide standard error is reported.

## Pooled metrics

| metric | estimate [95% CI] |
|---|---|
| PQ | 0.806 [0.765, 0.854] |
| SQ | 0.873 [0.856, 0.901] |
| DQ | 0.923 [0.883, 0.956] |
| recall | 0.880 [0.821, 0.929] |
| precision | 0.971 [0.946, 0.989] |
| dice_per_gt | 0.817 [0.758, 0.872] |
| iou_per_gt | 0.768 [0.711, 0.827] |
| dice_matched | 0.929 [0.918, 0.946] |
| iou_matched | 0.873 [0.856, 0.901] |
| hd95_um_mean | 7.241 [4.316, 10.284] |
| hd95_um_median | 2.240 [2.203, 2.493] |
| hd95_px_mean | 16.431 [9.795, 23.337] |
| assd_um_mean | 1.549 [1.171, 2.016] |
| split_rate | 0.007 [0.000, 0.016] |
| merge_rate | 0.160 [0.083, 0.263] |
| fg_dice_px | 0.956 [0.949, 0.963] |
| fg_iou_px | 0.916 [0.903, 0.928] |
| dice_px[tubule_proximal] | 0.949 [0.921, 0.966] |
| dice_px[tubule_distal] | 0.811 [0.773, 0.913] |
| dice_px[tubule_collecting] | 0.948 [0.000, 0.949] |
| dice_px[glomerulus] | 0.942 [0.931, 0.966] |

HD95 and ASSD are over true positives only; read them next to recall. `dice_per_gt` counts each missed object as 0, `dice_matched` does not.

## Per slide

| slide | n GT | PQ | recall | dice_per_gt | dice_matched | hd95_um_mean | merge_rate |
|---|---|---|---|---|---|---|---|
| Ctrl_1A2_test | 150 | 0.806 [0.765, 0.854] | 0.880 [0.821, 0.929] | 0.817 [0.758, 0.872] | 0.929 [0.918, 0.946] | 7.241 [4.316, 10.284] | 0.160 [0.083, 0.263] |

1 slide(s) scored: between-slide standard error is not estimable; per-slide point estimates are shown instead.

## By ground-truth class

| group | n GT | recall | dice_per_gt | hd95_um_mean | split_rate | merge_rate |
|---|---|---|---|---|---|---|
| tubule_proximal | 70 | 0.886 [0.800, 1.000] | 0.833 [0.740, 0.954] | 7.825 [3.256, 11.592] | 0.000 [0.000, 0.000] | 0.186 [0.000, 0.316] |
| tubule_distal | 15 | 0.800 [0.750, 1.000] | 0.725 [0.702, 0.859] | 7.982 [4.351, 16.214] | 0.000 [0.000, 0.000] | 0.267 [0.000, 0.400] |
| tubule_collecting | 53 | 0.887 [0.750, 0.911] | 0.813 [0.705, 0.833] | 6.552 [3.293, 7.029] | 0.019 [0.000, 0.022] | 0.132 [0.111, 0.250] |
| glomerulus | 12 | 0.917 [0.800, 1.000] | 0.862 [0.753, 0.940] | 6.086 [2.973, 8.555] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

## Failure types (annotated objects)

| type | n | share |
|---|---|---|
| ok | 111 | 74.0% |
| merge | 24 | 16.0% |
| leak | 12 | 8.0% |
| miss | 2 | 1.3% |
| poor_overlap | 1 | 0.7% |

`merge` and `split` take precedence over the detection outcome; `miss` is an unmatched object whose best overlap is IoU < 0.10; `leak` is a matched object with more than 5% of the prediction beyond the 5 px ring.

## Worst tiles by Dice (lowest `dice_per_gt`, tiles with ≥ 3 objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| Ctrl_1A2_test | 11132 | 11809 | 8 | 6/1/2 | 0.705 | 3.29 | 10.14 | 2 | 0 | 0.949 |
| Ctrl_1A2_test | 9084 | 11809 | 31 | 24/1/7 | 0.706 | 14.03 | 98.24 | 11 | 0 | 0.966 |
| Ctrl_1A2_test | 11132 | 10785 | 45 | 41/1/4 | 0.833 | 7.03 | 47.85 | 5 | 1 | 0.948 |
| Ctrl_1A2_test | 8060 | 12833 | 20 | 18/1/2 | 0.840 | 5.25 | 26.52 | 2 | 0 | 0.945 |
| Ctrl_1A2_test | 9084 | 12833 | 30 | 27/0/3 | 0.852 | 6.36 | 63.93 | 4 | 0 | 0.954 |
| Ctrl_1A2_test | 8060 | 11809 | 10 | 10/0/0 | 0.951 | 2.89 | 6.14 | 0 | 0 | 0.962 |
| Ctrl_1A2_test | 10108 | 11809 | 4 | 4/0/0 | 0.957 | 3.01 | 5.99 | 0 | 0 | 0.952 |

## Worst tiles by HD95 (highest mean, tiles with ≥ 3 matched objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| Ctrl_1A2_test | 9084 | 11809 | 31 | 24/1/7 | 0.706 | 14.03 | 98.24 | 11 | 0 | 0.966 |
| Ctrl_1A2_test | 11132 | 10785 | 45 | 41/1/4 | 0.833 | 7.03 | 47.85 | 5 | 1 | 0.948 |
| Ctrl_1A2_test | 9084 | 12833 | 30 | 27/0/3 | 0.852 | 6.36 | 63.93 | 4 | 0 | 0.954 |
| Ctrl_1A2_test | 8060 | 12833 | 20 | 18/1/2 | 0.840 | 5.25 | 26.52 | 2 | 0 | 0.945 |
| Ctrl_1A2_test | 11132 | 11809 | 8 | 6/1/2 | 0.705 | 3.29 | 10.14 | 2 | 0 | 0.949 |
| Ctrl_1A2_test | 10108 | 11809 | 4 | 4/0/0 | 0.957 | 3.01 | 5.99 | 0 | 0 | 0.952 |
| Ctrl_1A2_test | 8060 | 11809 | 10 | 10/0/0 | 0.951 | 2.89 | 6.14 | 0 | 0 | 0.962 |

7 of 8 tiles have ≥ 3 annotated objects and are ranked. Coordinates are the tile's top-left corner in working pixels.

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
| Ctrl_1A2_test | 8866 | 13349 | tubule_proximal | TP | leak | 0.853 | 26.52 | 60.2 | 13.4 | 0.194 | 1.32 |
| Ctrl_1A2_test | 9405 | 12396 | tubule_proximal | TP | merge | 0.677 | 25.12 | 57.0 | 24.5 | 0.404 | 1.67 |
| Ctrl_1A2_test | 9686 | 12488 | tubule_distal | TP | leak | 0.842 | 24.01 | 54.5 | 7.1 | 0.193 | 1.25 |
| Ctrl_1A2_test | 11591 | 11551 | tubule_collecting | TP | merge | 0.668 | 23.42 | 53.1 | 10.2 | 0.419 | 1.95 |
| Ctrl_1A2_test | 9648 | 12734 | tubule_proximal | TP | leak | 0.844 | 23.11 | 52.4 | 11.5 | 0.190 | 1.25 |
| Ctrl_1A2_test | 9025 | 12924 | tubule_distal | TP | merge | 0.753 | 23.06 | 52.3 | 21.2 | 0.289 | 1.54 |
| Ctrl_1A2_test | 11742 | 11621 | tubule_collecting | TP | leak | 0.769 | 22.34 | 50.7 | 14.5 | 0.305 | 1.52 |
| Ctrl_1A2_test | 9139 | 12852 | glomerulus | TP | ok | 0.953 | 17.74 | 40.3 | 7.1 | 0.005 | 1.02 |
| Ctrl_1A2_test | 9752 | 12842 | tubule_distal | TP | merge | 0.931 | 14.65 | 33.2 | 4.2 | 0.056 | 1.09 |
| Ctrl_1A2_test | 10075 | 12949 | glomerulus | TP | ok | 0.936 | 12.34 | 28.0 | 23.0 | 0.000 | 0.90 |
| Ctrl_1A2_test | 12023 | 11378 | tubule_collecting | TP | leak | 0.837 | 11.55 | 26.2 | 12.1 | 0.167 | 1.36 |
| Ctrl_1A2_test | 11840 | 11505 | tubule_collecting | TP | leak | 0.849 | 11.02 | 25.0 | 14.6 | 0.145 | 1.30 |
| Ctrl_1A2_test | 11632 | 11612 | tubule_collecting | TP | leak | 0.877 | 11.00 | 25.0 | 9.3 | 0.121 | 1.27 |

## Worst matched objects by leak fraction

| slide | cx | cy | class | status | failure | Dice | HD95 µm | pred→GT px | GT→pred px | leak | area ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Ctrl_1A2_test | 9708 | 12312 | tubule_proximal | TP | merge | 0.690 | 98.24 | 222.9 | 19.4 | 0.440 | 1.86 |
| Ctrl_1A2_test | 11591 | 11551 | tubule_collecting | TP | merge | 0.668 | 23.42 | 53.1 | 10.2 | 0.419 | 1.95 |
| Ctrl_1A2_test | 9405 | 12396 | tubule_proximal | TP | merge | 0.677 | 25.12 | 57.0 | 24.5 | 0.404 | 1.67 |
| Ctrl_1A2_test | 9289 | 13152 | tubule_proximal | TP | merge | 0.728 | 63.93 | 145.1 | 19.0 | 0.389 | 1.71 |
| Ctrl_1A2_test | 9668 | 12106 | tubule_proximal | TP | merge | 0.757 | 44.04 | 99.9 | 16.3 | 0.352 | 1.63 |
| Ctrl_1A2_test | 11742 | 11621 | tubule_collecting | TP | leak | 0.769 | 22.34 | 50.7 | 14.5 | 0.305 | 1.52 |
| Ctrl_1A2_test | 9025 | 12924 | tubule_distal | TP | merge | 0.753 | 23.06 | 52.3 | 21.2 | 0.289 | 1.54 |
| Ctrl_1A2_test | 9525 | 12589 | tubule_proximal | TP | merge | 0.808 | 76.62 | 173.9 | 5.0 | 0.288 | 1.45 |
| Ctrl_1A2_test | 11913 | 11206 | tubule_collecting | TP | leak | 0.797 | 40.82 | 92.6 | 7.8 | 0.288 | 1.43 |
| Ctrl_1A2_test | 11617 | 10969 | tubule_collecting | TP | merge | 0.811 | 47.85 | 108.6 | 6.9 | 0.270 | 1.39 |
| Ctrl_1A2_test | 11725 | 11101 | tubule_collecting | TP | leak | 0.837 | 41.79 | 94.8 | 7.2 | 0.218 | 1.35 |
| Ctrl_1A2_test | 8866 | 13349 | tubule_proximal | TP | leak | 0.853 | 26.52 | 60.2 | 13.4 | 0.194 | 1.32 |
| Ctrl_1A2_test | 9686 | 12488 | tubule_distal | TP | leak | 0.842 | 24.01 | 54.5 | 7.1 | 0.193 | 1.25 |
| Ctrl_1A2_test | 9648 | 12734 | tubule_proximal | TP | leak | 0.844 | 23.11 | 52.4 | 11.5 | 0.190 | 1.25 |
| Ctrl_1A2_test | 12023 | 11378 | tubule_collecting | TP | leak | 0.837 | 11.55 | 26.2 | 12.1 | 0.167 | 1.36 |
| Ctrl_1A2_test | 11840 | 11505 | tubule_collecting | TP | leak | 0.849 | 11.02 | 25.0 | 14.6 | 0.145 | 1.30 |
| Ctrl_1A2_test | 11632 | 11612 | tubule_collecting | TP | leak | 0.877 | 11.00 | 25.0 | 9.3 | 0.121 | 1.27 |
| Ctrl_1A2_test | 11579 | 11911 | tubule_collecting | TP | leak | 0.874 | 10.14 | 23.0 | 14.3 | 0.121 | 1.11 |
| Ctrl_1A2_test | 8781 | 12913 | tubule_distal | TP | leak | 0.854 | 8.33 | 18.9 | 12.0 | 0.116 | 1.18 |
| Ctrl_1A2_test | 9465 | 13736 | glomerulus | TP | leak | 0.886 | 8.92 | 20.2 | 16.3 | 0.084 | 1.25 |

## Unmatched annotated objects (18; largest first)

| slide | cx | cy | class | failure | area px | best IoU |
|---|---|---|---|---|---|---|
| Ctrl_1A2_test | 9919 | 12047 | tubule_proximal | merge | 17319 | 0.269 |
| Ctrl_1A2_test | 9623 | 13702 | tubule_distal | miss | 14354 | 0.000 |
| Ctrl_1A2_test | 9091 | 12335 | tubule_proximal | merge | 12770 | 0.287 |
| Ctrl_1A2_test | 9824 | 12487 | tubule_proximal | merge | 12589 | 0.265 |
| Ctrl_1A2_test | 9521 | 12479 | tubule_proximal | merge | 10459 | 0.159 |
| Ctrl_1A2_test | 9426 | 13066 | tubule_proximal | merge | 10371 | 0.377 |
| Ctrl_1A2_test | 9105 | 12495 | tubule_proximal | merge | 7623 | 0.171 |
| Ctrl_1A2_test | 11482 | 11096 | tubule_collecting | merge | 7540 | 0.305 |
| Ctrl_1A2_test | 11635 | 11769 | tubule_collecting | merge | 7128 | 0.427 |
| Ctrl_1A2_test | 9008 | 13639 | glomerulus | poor_overlap | 6853 | 0.452 |
| Ctrl_1A2_test | 9560 | 12191 | tubule_proximal | merge | 6708 | 0.328 |
| Ctrl_1A2_test | 9469 | 12366 | tubule_proximal | merge | 5113 | 0.382 |
| Ctrl_1A2_test | 11718 | 11888 | tubule_collecting | merge | 4004 | 0.250 |
| Ctrl_1A2_test | 11717 | 11958 | tubule_collecting | merge | 3994 | 0.249 |
| Ctrl_1A2_test | 11944 | 11493 | tubule_collecting | miss | 2828 | 0.000 |
| Ctrl_1A2_test | 8969 | 12947 | tubule_distal | merge | 2683 | 0.280 |
| Ctrl_1A2_test | 11547 | 11595 | tubule_collecting | merge | 2167 | 0.410 |
| Ctrl_1A2_test | 9551 | 12969 | tubule_distal | merge | 2009 | 0.051 |

## Edge cases

### Boundary leakage

| quantity | value |
|---|---|
| n_matched | 132 |
| leak_frac_mean | 0.042 |
| leak_frac_gt_0.05_rate | 0.159 |
| over_reach_asymmetry_px_mean | 10.003 |
| over_reach_asymmetry_px_median | 0.502 |
| area_ratio_median | 1.022 |
| area_ratio_mean | 1.080 |
| pred_solidity_lt_0.85_rate | 0.189 |
| gt_solidity_lt_0.85_rate | 0.160 |
| pred_px_on_trusted_background_frac | 0.052 |

### Small and disconnected components

| quantity | value |
|---|---|
| predictions inside the rectangles (not edge-cut) | 887 |
|   below their class min_area floor | 0 |
|   with more than one connected component | 0 |
|   mean stray area share among those | 0.000 |
| false positives | 4 |
|   fragments on an annotated object | 3 |
|   on trusted background | 1 |
|   area px, quartiles | [2902.75, 9178.0, 22295.0] |

### By ground-truth size

| quartile | area px | n | recall | dice_per_gt | HD95 µm | merge |
|---|---|---|---|---|---|---|
| 1 | 1581–4284 | 38 | 0.842 | 0.775 | 3.76 | 0.158 |
| 2 | 4284–7628 | 37 | 0.838 | 0.772 | 5.55 | 0.189 |
| 3 | 7628–11862 | 37 | 0.946 | 0.900 | 3.28 | 0.054 |
| 4 | 11862–36737 | 38 | 0.895 | 0.823 | 16.13 | 0.237 |

### Stain intensity (observational)

Observational only: staining intensity is confounded with anatomy (medulla stains differently from cortex), so an association here is not evidence of stain sensitivity on its own. The controlled test is --stain-drift.

| pair | Spearman ρ | p | n tiles |
|---|---|---|---|
| h_od,dice_per_gt | -0.321 | 0.482 | 7 |
| h_od,hd95_um_mean | 0.429 | 0.337 | 7 |
| e_od,dice_per_gt | 0.357 | 0.432 | 7 |
| e_od,hd95_um_mean | -0.286 | 0.535 | 7 |

| h_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.008 | 2 | 0.776 | 0.766 | 10.75 |
| 2 | 0.008 | 2 | 0.830 | 0.859 | 4.85 |
| 3 | 0.010 | 3 | 0.810 | 0.827 | 6.48 |

| e_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.039 | 2 | 0.785 | 0.813 | 6.55 |
| 2 | 0.046 | 2 | 0.862 | 0.864 | 5.93 |
| 3 | 0.049 | 3 | 0.788 | 0.790 | 8.85 |
