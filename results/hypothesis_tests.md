# Hypothesis Tests (DOC-FIX-001 Part B)

> **Interpretation:** p-values describe seed-to-seed simulation variability under common
> random numbers, not real-world inference. N is small (15 or 30 paired seeds).
> No claim of precision beyond these data is made.
>
> `mean_diff` is **right minus left** in each `A -> B` comparison. A negative value means
> the right-hand configuration/case has lower unserved energy or grid import.

## 1. Paired sizing comparisons — unserved Tier 1+2, 2019 typhoon, bottom-up

| comparison         |   n |   mean_diff |   median_diff |   sd_diff |   ci95_half |   cohens_dz |   wilcoxon_p |   paired_t_p |   holm_adjusted_p |
|:-------------------|----:|------------:|--------------:|----------:|------------:|------------:|-------------:|-------------:|------------------:|
| 100/50 -> 100/100  |  30 |    -44.1135 |      -38.6667 |   31.1942 |    11.6481  |   -1.41416  |  2.56308e-06 |  1.53122e-08 |       7.68925e-06 |
| 100/100 -> 200/100 |  30 |    -61.4916 |      -58.4329 |   52.6039 |    19.6426  |   -1.16896  |  5.60612e-06 |  5.31073e-07 |       7.68925e-06 |
| 200/100 -> 200/200 |  30 |    -19.4415 |      -13.6677 |   20.6154 |     7.69792 |   -0.943055 |  3.78962e-06 |  1.60204e-05 |       7.68925e-06 |
| 0/0 -> 100/100     |  30 |   -534.539  |     -501.154  |  315.791  |   117.918   |   -1.6927   |  1.86265e-09 |  3.56895e-10 |       7.45058e-09 |

## 2. Paired grid import — weather year and +2 °C

| comparison                                        |   n |   mean_diff |   median_diff |   sd_diff |   ci95_half |   cohens_dz |   wilcoxon_p |   paired_t_p |   holm_adjusted_p |
|:--------------------------------------------------|----:|------------:|--------------:|----------:|------------:|------------:|-------------:|-------------:|------------------:|
| 2019 minus 2016, normal, 0/0                      |  30 |    -9434.29 |      -9432.25 |  125.916  |     47.0178 |    -74.9253 |  1.86265e-09 |  3.87474e-56 |       5.58794e-09 |
| 2019 minus 2016, normal, 100/100                  |  30 |    -6129.09 |      -6144.73 |  125.703  |     46.9384 |    -48.7584 |  1.86265e-09 |  9.9451e-51  |       5.58794e-09 |
| +2 C minus base, 2019 normal, grid-only, 15 seeds |  15 |    14347.4  |      14357.1  |   32.0112 |     17.7272 |    448.199  |  6.10352e-05 |  9.78984e-39 |       6.10352e-05 |

## 3. Unpaired typhoon vs normal — unserved Tier 1+2, 2019, 100/100

| comparison                       |   n_left |   n_right |   mean_left |   mean_right |   mean_diff |   mannwhitney_p |   welch_t_p |
|:---------------------------------|---------:|----------:|------------:|-------------:|------------:|----------------:|------------:|
| typhoon vs normal, 2019, 100/100 |       30 |        30 |     6.40894 |      110.981 |     104.572 |     3.36587e-09 | 1.19417e-06 |
