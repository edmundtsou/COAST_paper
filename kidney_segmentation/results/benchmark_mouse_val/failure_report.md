# Segmentation benchmark — failure report

511 annotated objects, 488 scored predictions, 173 tiles of 1024 px over 2 slide(s). TP 453 / FP 35 / FN 58. Brackets are 95% intervals (2000 bootstrap replicates over tiles).

**Read this first**

- Confidence intervals describe spatial sampling variability WITHIN the scored slides. They do not describe generalisation across animals, sections, stain batches or scanners: with fewer than 5 slides the between-slide variance is not estimable and no between-slide standard error is reported.
- Ctrl_1A2_val is a set of held-out blocks of a section whose other blocks were used for training. Pixels are disjoint; the section, stain run and scan are shared.
- Nx_4wk_050 supplied most of the patches used to select the checkpoint (validation PQ). Results on it are validation results, not results on an independent test set.

## Pooled metrics

| metric | estimate [95% CI] |
|---|---|
| PQ | 0.800 [0.763, 0.834] |
| SQ | 0.882 [0.869, 0.894] |
| DQ | 0.907 [0.873, 0.940] |
| recall | 0.886 [0.835, 0.925] |
| precision | 0.928 [0.888, 0.965] |
| dice_per_gt | 0.828 [0.779, 0.866] |
| iou_per_gt | 0.782 [0.734, 0.819] |
| dice_matched | 0.934 [0.926, 0.941] |
| iou_matched | 0.882 [0.869, 0.894] |
| hd95_um_mean | 6.678 [5.172, 8.653] |
| hd95_um_median | 2.203 [1.971, 2.570] |
| hd95_px_mean | 15.155 [11.737, 19.635] |
| assd_um_mean | 1.417 [1.200, 1.703] |
| split_rate | 0.025 [0.008, 0.047] |
| merge_rate | 0.108 [0.067, 0.153] |
| fg_dice_px | 0.959 [0.956, 0.962] |
| fg_iou_px | 0.921 [0.916, 0.926] |
| dice_px[tubule_proximal] | 0.950 [0.931, 0.963] |
| dice_px[tubule_distal] | 0.862 [0.783, 0.916] |
| dice_px[tubule_collecting] | 0.952 [0.948, 0.958] |
| dice_px[glomerulus] | 0.907 [0.856, 0.944] |

HD95 and ASSD are over true positives only; read them next to recall. `dice_per_gt` counts each missed object as 0, `dice_matched` does not.

## Per slide

| slide | n GT | PQ | recall | dice_per_gt | dice_matched | hd95_um_mean | merge_rate |
|---|---|---|---|---|---|---|---|
| Ctrl_1A2_val | 356 | 0.773 [0.715, 0.817] | 0.868 [0.778, 0.925] | 0.805 [0.718, 0.859] | 0.928 [0.916, 0.935] | 7.262 [5.329, 10.189] | 0.121 [0.061, 0.193] |
| Nx_4wk_050 | 155 | 0.861 [0.830, 0.892] | 0.929 [0.899, 0.961] | 0.879 [0.847, 0.913] | 0.946 [0.935, 0.956] | 5.426 [3.348, 7.698] | 0.077 [0.035, 0.120] |

2 slide(s) scored: between-slide standard error is not estimable; per-slide point estimates are shown instead.

## By ground-truth class

| group | n GT | recall | dice_per_gt | hd95_um_mean | split_rate | merge_rate |
|---|---|---|---|---|---|---|
| tubule_proximal | 296 | 0.922 [0.834, 0.979] | 0.874 [0.790, 0.931] | 5.406 [3.886, 7.002] | 0.020 [0.000, 0.042] | 0.078 [0.013, 0.162] |
| tubule_distal | 99 | 0.818 [0.753, 0.908] | 0.737 [0.665, 0.829] | 8.275 [5.363, 11.844] | 0.061 [0.000, 0.130] | 0.192 [0.095, 0.259] |
| tubule_collecting | 86 | 0.837 [0.667, 0.900] | 0.771 [0.595, 0.835] | 10.541 [2.716, 17.257] | 0.012 [0.000, 0.056] | 0.140 [0.088, 0.222] |
| glomerulus | 30 | 0.900 [0.778, 1.000] | 0.829 [0.716, 0.921] | 4.455 [2.882, 5.913] | 0.000 [0.000, 0.000] | 0.033 [0.000, 0.100] |

## Failure types (annotated objects)

| type | n | share |
|---|---|---|
| ok | 402 | 78.7% |
| merge | 55 | 10.8% |
| leak | 25 | 4.9% |
| split | 13 | 2.5% |
| miss | 12 | 2.3% |
| poor_overlap | 4 | 0.8% |

`merge` and `split` take precedence over the detection outcome; `miss` is an unmatched object whose best overlap is IoU < 0.10; `leak` is a matched object with more than 5% of the prediction beyond the 5 px ring.

## Worst tiles by Dice (lowest `dice_per_gt`, tiles with ≥ 3 objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| Ctrl_1A2_val | 10733 | 10240 | 18 | 12/1/6 | 0.595 | 19.44 | 95.25 | 4 | 0 | 0.956 |
| Ctrl_1A2_val | 10733 | 6144 | 37 | 25/3/12 | 0.629 | 7.21 | 55.28 | 11 | 0 | 0.954 |
| Ctrl_1A2_val | 6637 | 9216 | 6 | 5/0/1 | 0.785 | 2.71 | 3.93 | 0 | 0 | 0.953 |
| Ctrl_1A2_val | 6637 | 8192 | 77 | 65/7/12 | 0.793 | 5.70 | 69.84 | 14 | 2 | 0.964 |
| Nx_4wk_050 | 10308 | 6457 | 16 | 14/1/2 | 0.813 | 8.79 | 43.52 | 2 | 1 | 0.951 |
| Nx_4wk_050 | 10308 | 14649 | 16 | 14/1/2 | 0.814 | 10.19 | 75.03 | 1 | 1 | 0.949 |
| Nx_4wk_050 | 9284 | 6457 | 8 | 7/0/1 | 0.818 | 3.74 | 15.88 | 2 | 0 | 0.971 |
| Ctrl_1A2_val | 9709 | 10240 | 32 | 29/1/3 | 0.822 | 11.62 | 58.57 | 4 | 0 | 0.948 |
| Ctrl_1A2_val | 10733 | 7168 | 19 | 17/2/2 | 0.828 | 7.60 | 76.19 | 0 | 2 | 0.962 |
| Ctrl_1A2_val | 9709 | 7168 | 63 | 57/14/6 | 0.828 | 9.84 | 178.89 | 4 | 6 | 0.958 |
| Nx_4wk_050 | 13380 | 16697 | 9 | 8/0/1 | 0.831 | 5.62 | 25.61 | 2 | 0 | 0.965 |
| Nx_4wk_050 | 15428 | 9529 | 18 | 16/1/2 | 0.850 | 2.62 | 5.42 | 2 | 0 | 0.956 |
| Ctrl_1A2_val | 5613 | 8192 | 15 | 14/0/1 | 0.875 | 4.06 | 21.15 | 0 | 0 | 0.955 |
| Nx_4wk_050 | 20548 | 6457 | 14 | 13/0/1 | 0.878 | 7.76 | 78.64 | 2 | 0 | 0.971 |
| Ctrl_1A2_val | 9709 | 6144 | 89 | 85/4/4 | 0.894 | 4.27 | 39.59 | 6 | 1 | 0.957 |
| Nx_4wk_050 | 7236 | 18745 | 7 | 7/0/0 | 0.897 | 11.38 | 35.93 | 0 | 0 | 0.956 |
| Nx_4wk_050 | 7236 | 17721 | 4 | 4/0/0 | 0.898 | 22.32 | 74.04 | 0 | 0 | 0.956 |
| Nx_4wk_050 | 16452 | 4409 | 18 | 17/0/1 | 0.910 | 1.95 | 5.50 | 0 | 0 | 0.965 |
| Nx_4wk_050 | 7236 | 10553 | 8 | 8/0/0 | 0.962 | 2.08 | 2.82 | 0 | 0 | 0.965 |
| Nx_4wk_050 | 7236 | 9529 | 3 | 3/0/0 | 0.963 | 2.48 | 3.55 | 0 | 0 | 0.959 |

## Worst tiles by HD95 (highest mean, tiles with ≥ 3 matched objects)

| slide | x0 | y0 | n GT | TP/FP/FN | dice_per_gt | HD95 µm mean | HD95 µm max | merged | split | fg Dice px |
|---|---|---|---|---|---|---|---|---|---|---|
| Nx_4wk_050 | 7236 | 17721 | 4 | 4/0/0 | 0.898 | 22.32 | 74.04 | 0 | 0 | 0.956 |
| Ctrl_1A2_val | 10733 | 10240 | 18 | 12/1/6 | 0.595 | 19.44 | 95.25 | 4 | 0 | 0.956 |
| Ctrl_1A2_val | 9709 | 10240 | 32 | 29/1/3 | 0.822 | 11.62 | 58.57 | 4 | 0 | 0.948 |
| Nx_4wk_050 | 7236 | 18745 | 7 | 7/0/0 | 0.897 | 11.38 | 35.93 | 0 | 0 | 0.956 |
| Nx_4wk_050 | 10308 | 14649 | 16 | 14/1/2 | 0.814 | 10.19 | 75.03 | 1 | 1 | 0.949 |
| Ctrl_1A2_val | 9709 | 7168 | 63 | 57/14/6 | 0.828 | 9.84 | 178.89 | 4 | 6 | 0.958 |
| Nx_4wk_050 | 10308 | 6457 | 16 | 14/1/2 | 0.813 | 8.79 | 43.52 | 2 | 1 | 0.951 |
| Nx_4wk_050 | 20548 | 6457 | 14 | 13/0/1 | 0.878 | 7.76 | 78.64 | 2 | 0 | 0.971 |
| Ctrl_1A2_val | 10733 | 7168 | 19 | 17/2/2 | 0.828 | 7.60 | 76.19 | 0 | 2 | 0.962 |
| Ctrl_1A2_val | 10733 | 6144 | 37 | 25/3/12 | 0.629 | 7.21 | 55.28 | 11 | 0 | 0.954 |
| Ctrl_1A2_val | 6637 | 8192 | 77 | 65/7/12 | 0.793 | 5.70 | 69.84 | 14 | 2 | 0.964 |
| Nx_4wk_050 | 13380 | 16697 | 9 | 8/0/1 | 0.831 | 5.62 | 25.61 | 2 | 0 | 0.965 |
| Ctrl_1A2_val | 9709 | 6144 | 89 | 85/4/4 | 0.894 | 4.27 | 39.59 | 6 | 1 | 0.957 |
| Ctrl_1A2_val | 5613 | 8192 | 15 | 14/0/1 | 0.875 | 4.06 | 21.15 | 0 | 0 | 0.955 |
| Nx_4wk_050 | 9284 | 6457 | 8 | 7/0/1 | 0.818 | 3.74 | 15.88 | 2 | 0 | 0.971 |
| Ctrl_1A2_val | 6637 | 9216 | 6 | 5/0/1 | 0.785 | 2.71 | 3.93 | 0 | 0 | 0.953 |
| Nx_4wk_050 | 15428 | 9529 | 18 | 16/1/2 | 0.850 | 2.62 | 5.42 | 2 | 0 | 0.956 |
| Nx_4wk_050 | 18500 | 11577 | 4 | 4/0/0 | 0.966 | 2.52 | 3.50 | 0 | 0 | 0.968 |
| Nx_4wk_050 | 7236 | 9529 | 3 | 3/0/0 | 0.963 | 2.48 | 3.55 | 0 | 0 | 0.959 |
| Nx_4wk_050 | 5188 | 12601 | 11 | 11/0/0 | 0.968 | 2.12 | 6.17 | 0 | 0 | 0.965 |

24 of 173 tiles have ≥ 3 annotated objects and are ranked. Coordinates are the tile's top-left corner in working pixels.

## Worst matched objects by HD95

| slide | cx | cy | class | status | failure | Dice | HD95 µm | pred→GT px | GT→pred px | leak | area ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Ctrl_1A2_val | 10180 | 7789 | tubule_proximal | TP | split | 0.733 | 178.89 | 11.3 | 405.9 | 0.004 | 0.62 |
| Ctrl_1A2_val | 10999 | 10561 | tubule_collecting | TP | merge | 0.725 | 95.25 | 216.2 | 6.3 | 0.380 | 1.67 |
| Nx_4wk_050 | 20880 | 6606 | tubule_distal | TP | merge | 0.676 | 78.64 | 178.5 | 3.6 | 0.464 | 1.86 |
| Ctrl_1A2_val | 10767 | 7365 | tubule_proximal | TP | split | 0.676 | 76.19 | 32.7 | 172.9 | 0.042 | 0.57 |
| Nx_4wk_050 | 11296 | 15135 | tubule_collecting | TP | merge | 0.777 | 75.03 | 170.3 | 4.2 | 0.334 | 1.50 |
| Nx_4wk_050 | 7566 | 18742 | tubule_proximal | TP | leak | 0.808 | 74.04 | 168.0 | 6.0 | 0.299 | 1.45 |
| Ctrl_1A2_val | 7486 | 8835 | tubule_proximal | TP | merge | 0.695 | 69.84 | 158.5 | 8.5 | 0.441 | 1.84 |
| Ctrl_1A2_val | 11302 | 10575 | tubule_collecting | TP | leak | 0.673 | 64.80 | 147.1 | 38.6 | 0.437 | 1.94 |
| Ctrl_1A2_val | 10084 | 10989 | tubule_collecting | TP | leak | 0.810 | 58.57 | 132.9 | 3.6 | 0.268 | 1.44 |
| Ctrl_1A2_val | 10877 | 6600 | tubule_proximal | TP | merge | 0.852 | 55.28 | 125.4 | 7.1 | 0.213 | 1.26 |
| Ctrl_1A2_val | 10512 | 7185 | tubule_distal | TP | leak | 0.667 | 51.64 | 117.2 | 12.8 | 0.450 | 1.93 |
| Nx_4wk_050 | 11110 | 15072 | tubule_collecting | TP | split | 0.692 | 48.56 | 12.4 | 110.2 | 0.000 | 0.55 |
| Ctrl_1A2_val | 7623 | 8968 | tubule_proximal | TP | merge | 0.720 | 48.37 | 109.8 | 14.6 | 0.400 | 1.70 |
| Ctrl_1A2_val | 10620 | 7414 | tubule_distal | TP | merge | 0.709 | 47.10 | 106.9 | 19.1 | 0.400 | 1.69 |
| Ctrl_1A2_val | 9882 | 10489 | tubule_collecting | TP | merge | 0.842 | 45.11 | 102.4 | 4.3 | 0.206 | 1.34 |
| Ctrl_1A2_val | 10320 | 10377 | tubule_collecting | TP | merge | 0.803 | 43.93 | 99.7 | 8.5 | 0.234 | 1.29 |
| Nx_4wk_050 | 10779 | 6959 | tubule_distal | TP | merge | 0.897 | 43.52 | 98.8 | 5.4 | 0.152 | 1.18 |
| Nx_4wk_050 | 10885 | 6860 | tubule_distal | TP | split | 0.717 | 40.57 | 12.3 | 92.1 | 0.000 | 0.59 |
| Ctrl_1A2_val | 9945 | 6272 | tubule_proximal | TP | split | 0.769 | 39.59 | 86.4 | 89.8 | 0.180 | 0.98 |
| Ctrl_1A2_val | 9740 | 7473 | tubule_proximal | TP | split | 0.672 | 39.20 | 7.2 | 89.0 | 0.000 | 0.53 |

## Worst matched objects by leak fraction

| slide | cx | cy | class | status | failure | Dice | HD95 µm | pred→GT px | GT→pred px | leak | area ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Nx_4wk_050 | 20880 | 6606 | tubule_distal | TP | merge | 0.676 | 78.64 | 178.5 | 3.6 | 0.464 | 1.86 |
| Ctrl_1A2_val | 10512 | 7185 | tubule_distal | TP | leak | 0.667 | 51.64 | 117.2 | 12.8 | 0.450 | 1.93 |
| Ctrl_1A2_val | 7486 | 8835 | tubule_proximal | TP | merge | 0.695 | 69.84 | 158.5 | 8.5 | 0.441 | 1.84 |
| Ctrl_1A2_val | 11302 | 10575 | tubule_collecting | TP | leak | 0.673 | 64.80 | 147.1 | 38.6 | 0.437 | 1.94 |
| Ctrl_1A2_val | 10620 | 7414 | tubule_distal | TP | merge | 0.709 | 47.10 | 106.9 | 19.1 | 0.400 | 1.69 |
| Ctrl_1A2_val | 7623 | 8968 | tubule_proximal | TP | merge | 0.720 | 48.37 | 109.8 | 14.6 | 0.400 | 1.70 |
| Ctrl_1A2_val | 7385 | 9028 | tubule_proximal | TP | merge | 0.721 | 25.69 | 58.3 | 12.5 | 0.393 | 1.66 |
| Ctrl_1A2_val | 10999 | 10561 | tubule_collecting | TP | merge | 0.725 | 95.25 | 216.2 | 6.3 | 0.380 | 1.67 |
| Nx_4wk_050 | 7915 | 18836 | tubule_distal | TP | leak | 0.720 | 30.46 | 69.1 | 11.5 | 0.369 | 1.65 |
| Nx_4wk_050 | 13979 | 17585 | tubule_distal | TP | merge | 0.750 | 25.61 | 58.1 | 50.7 | 0.360 | 1.63 |
| Ctrl_1A2_val | 10042 | 7614 | tubule_proximal | TP | merge | 0.757 | 34.54 | 78.4 | 13.2 | 0.336 | 1.55 |
| Nx_4wk_050 | 10186 | 7163 | tubule_distal | TP | merge | 0.730 | 15.88 | 36.0 | 19.7 | 0.335 | 1.63 |
| Nx_4wk_050 | 11296 | 15135 | tubule_collecting | TP | merge | 0.777 | 75.03 | 170.3 | 4.2 | 0.334 | 1.50 |
| Ctrl_1A2_val | 6843 | 8776 | tubule_distal | TP | merge | 0.724 | 32.13 | 72.9 | 13.9 | 0.324 | 1.32 |
| Ctrl_1A2_val | 9745 | 6891 | tubule_distal | TP | leak | 0.773 | 26.89 | 61.0 | 6.0 | 0.311 | 1.48 |
| Nx_4wk_050 | 7566 | 18742 | tubule_proximal | TP | leak | 0.808 | 74.04 | 168.0 | 6.0 | 0.299 | 1.45 |
| Ctrl_1A2_val | 9786 | 6565 | tubule_distal | TP | merge | 0.738 | 16.28 | 36.9 | 24.0 | 0.289 | 1.36 |
| Ctrl_1A2_val | 10084 | 10989 | tubule_collecting | TP | leak | 0.810 | 58.57 | 132.9 | 3.6 | 0.268 | 1.44 |
| Ctrl_1A2_val | 6456 | 8292 | tubule_proximal | TP | leak | 0.808 | 21.15 | 48.0 | 18.8 | 0.266 | 1.44 |
| Ctrl_1A2_val | 10102 | 7237 | tubule_proximal | TP | leak | 0.811 | 18.17 | 41.2 | 20.9 | 0.246 | 1.38 |

## Unmatched annotated objects (58; largest first)

| slide | cx | cy | class | failure | area px | best IoU |
|---|---|---|---|---|---|---|
| Ctrl_1A2_val | 10746 | 8132 | tubule_proximal | split | 21282 | 0.430 |
| Ctrl_1A2_val | 11177 | 6882 | tubule_proximal | merge | 19596 | 0.218 |
| Ctrl_1A2_val | 10426 | 7688 | tubule_proximal | split | 15785 | 0.470 |
| Ctrl_1A2_val | 11190 | 7072 | tubule_proximal | merge | 15519 | 0.186 |
| Ctrl_1A2_val | 7611 | 8677 | tubule_proximal | merge | 13904 | 0.432 |
| Ctrl_1A2_val | 11030 | 7144 | tubule_proximal | merge | 12896 | 0.147 |
| Nx_4wk_050 | 13964 | 17634 | tubule_distal | merge | 12585 | 0.325 |
| Ctrl_1A2_val | 11339 | 6949 | tubule_proximal | merge | 11246 | 0.131 |
| Ctrl_1A2_val | 9999 | 10506 | tubule_collecting | poor_overlap | 11132 | 0.471 |
| Nx_4wk_050 | 16797 | 5177 | tubule_distal | miss | 11064 | 0.001 |
| Ctrl_1A2_val | 10099 | 8057 | tubule_distal | split | 10737 | 0.447 |
| Nx_4wk_050 | 11418 | 15316 | tubule_collecting | merge | 10419 | 0.328 |
| Ctrl_1A2_val | 11144 | 6654 | tubule_proximal | merge | 10290 | 0.460 |
| Ctrl_1A2_val | 10752 | 10746 | tubule_collecting | merge | 9573 | 0.360 |
| Ctrl_1A2_val | 7254 | 8563 | tubule_distal | split | 9207 | 0.322 |
| Nx_4wk_050 | 20921 | 6462 | tubule_distal | merge | 9176 | 0.422 |
| Ctrl_1A2_val | 10688 | 7554 | tubule_distal | merge | 9120 | 0.342 |
| Ctrl_1A2_val | 9821 | 8090 | tubule_distal | split | 8331 | 0.466 |
| Ctrl_1A2_val | 7210 | 9092 | tubule_distal | split | 8322 | 0.490 |
| Ctrl_1A2_val | 11069 | 6580 | tubule_proximal | merge | 7939 | 0.190 |

## Edge cases

### Boundary leakage

| quantity | value |
|---|---|
| n_matched | 453 |
| leak_frac_mean | 0.027 |
| leak_frac_gt_0.05_rate | 0.099 |
| over_reach_asymmetry_px_mean | 3.754 |
| over_reach_asymmetry_px_median | 0.000 |
| area_ratio_median | 1.005 |
| area_ratio_mean | 1.026 |
| pred_solidity_lt_0.85_rate | 0.168 |
| gt_solidity_lt_0.85_rate | 0.176 |
| pred_px_on_trusted_background_frac | 0.042 |

### Small and disconnected components

| quantity | value |
|---|---|
| predictions inside the rectangles (not edge-cut) | 15396 |
|   below their class min_area floor | 0 |
|   with more than one connected component | 1 |
|   mean stray area share among those | 0.117 |
| false positives | 35 |
|   fragments on an annotated object | 33 |
|   on trusted background | 2 |
|   area px, quartiles | [2167.5, 4524.0, 8751.5] |

### By ground-truth size

| quartile | area px | n | recall | dice_per_gt | HD95 µm | merge |
|---|---|---|---|---|---|---|
| 1 | 13–5061 | 128 | 0.789 | 0.730 | 3.22 | 0.117 |
| 2 | 5061–7644 | 127 | 0.921 | 0.867 | 4.26 | 0.079 |
| 3 | 7644–11286 | 128 | 0.891 | 0.834 | 6.17 | 0.109 |
| 4 | 11286–84485 | 128 | 0.945 | 0.880 | 12.38 | 0.125 |

### Stain intensity (observational)

Observational only: staining intensity is confounded with anatomy (medulla stains differently from cortex), so an association here is not evidence of stain sensitivity on its own. The controlled test is --stain-drift.

| pair | Spearman ρ | p | n tiles |
|---|---|---|---|
| h_od,dice_per_gt | 0.380 | 0.067 | 24 |
| h_od,hd95_um_mean | -0.309 | 0.142 | 24 |
| e_od,dice_per_gt | -0.256 | 0.228 | 24 |
| e_od,hd95_um_mean | 0.197 | 0.357 | 24 |

| h_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.009 | 8 | 0.772 | 0.804 | 6.81 |
| 2 | 0.022 | 8 | 0.852 | 0.876 | 7.36 |
| 3 | 0.029 | 8 | 0.844 | 0.867 | 5.76 |

| e_od tertile | mean OD | n tiles | PQ | dice_per_gt | HD95 µm |
|---|---|---|---|---|---|
| 1 | 0.027 | 8 | 0.844 | 0.866 | 5.77 |
| 2 | 0.032 | 8 | 0.862 | 0.887 | 5.73 |
| 3 | 0.045 | 8 | 0.773 | 0.804 | 7.24 |

### Stain drift (controlled perturbation)

Synthetic perturbation of the haematoxylin / eosin optical densities of held-out windows, re-inferred window-locally. Training augmentation draws each scale from U(0.9, 1.1); larger steps are outside it. The 'roundtrip' level applies the colour-space conversion with both scales at 1.0 and is the reference for the scaled levels: the conversion alone perturbs pixels. This measures sensitivity to stain STRENGTH on these sections; it is not evidence about other stains, protocols or scanners. The baseline differs slightly from the headline numbers because it is a window-local re-inference, not the slide-wide map.

| level | H× | E× | PQ | recall | dice_per_gt | HD95 µm | merge | n pred | PQ vs unperturbed | tissue |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 1.0 | 1.0 | 0.786 | 0.858 | 0.802 | 5.81 | 0.107 | 341 | 1.000 | 0.908 |
| roundtrip | 1.0 | 1.0 | 0.789 | 0.866 | 0.809 | 5.85 | 0.107 | 343 | 0.943 | 0.908 |
| both-0.3 | 0.7 | 0.7 | 0.783 | 0.852 | 0.796 | 5.95 | 0.123 | 337 | 0.923 | 0.904 |
| both-0.2 | 0.8 | 0.8 | 0.781 | 0.850 | 0.795 | 5.73 | 0.120 | 339 | 0.934 | 0.907 |
| both-0.1 | 0.9 | 0.9 | 0.787 | 0.861 | 0.805 | 5.62 | 0.107 | 342 | 0.939 | 0.908 |
| both+0.1 | 1.1 | 1.1 | 0.792 | 0.869 | 0.812 | 5.74 | 0.104 | 343 | 0.944 | 0.909 |
| both+0.2 | 1.2 | 1.2 | 0.793 | 0.866 | 0.811 | 5.61 | 0.104 | 342 | 0.942 | 0.911 |
| both+0.3 | 1.3 | 1.3 | 0.787 | 0.852 | 0.800 | 5.53 | 0.115 | 339 | 0.939 | 0.911 |
| H-0.3 | 0.7 | 1.0 | 0.788 | 0.855 | 0.799 | 6.10 | 0.126 | 336 | 0.927 | 0.908 |
| H+0.3 | 1.3 | 1.0 | 0.795 | 0.872 | 0.815 | 5.26 | 0.107 | 344 | 0.942 | 0.908 |
| E-0.3 | 1.0 | 0.7 | 0.780 | 0.855 | 0.799 | 5.52 | 0.126 | 342 | 0.930 | 0.905 |
| E+0.3 | 1.0 | 1.3 | 0.784 | 0.855 | 0.800 | 5.82 | 0.126 | 341 | 0.931 | 0.911 |
