### Config summary

| Config | N origins | Mean loss | Std loss |
|---|---:|---:|---:|
| unimodal | 12 | 1387.3578 | 1355.7469 |
| currents | 12 | 1416.3778 | 1355.7227 |
| funding | 12 | 1291.9086 | 1327.8006 |
| dxy | 12 | 1297.9471 | 1161.4656 |
| spy | 12 | 1353.2482 | 1254.7739 |
| funding-vision | 12 | 1366.2712 | 1344.8833 |
| dxy-vision | 12 | 1423.6407 | 1366.8115 |
| spy-vision | 12 | 1390.3930 | 1358.6338 |

### Pairwise Diebold-Mariano

Negative statistic + small p-value means `config_a`'s loss is significantly lower (better) than `config_b`'s.

| config_a | config_b | statistic | p_value | n_common_origins | max_lag |
|---|---|---:|---:|---:|---:|
| currents | dxy | 1.0521 | 0.293 | 12 | 2 |
| currents | dxy-vision | -0.1171 | 0.907 | 12 | 2 |
| currents | funding | 2.1446 | 0.032 | 12 | 2 |
| currents | funding-vision | 0.8591 | 0.390 | 12 | 2 |
| currents | spy | 0.7683 | 0.442 | 12 | 2 |
| currents | spy-vision | 0.4031 | 0.687 | 12 | 2 |
| currents | unimodal | 0.3695 | 0.712 | 12 | 2 |
| dxy | dxy-vision | -1.4149 | 0.157 | 12 | 2 |
| dxy | funding | 0.0572 | 0.954 | 12 | 2 |
| dxy | funding-vision | -0.8019 | 0.423 | 12 | 2 |
| dxy | spy | -0.8704 | 0.384 | 12 | 2 |
| dxy | spy-vision | -0.9498 | 0.342 | 12 | 2 |
| dxy | unimodal | -0.8599 | 0.390 | 12 | 2 |
| dxy-vision | funding | 1.9502 | 0.051 | 12 | 2 |
| dxy-vision | funding-vision | 1.3413 | 0.180 | 12 | 2 |
| dxy-vision | spy | 1.3381 | 0.181 | 12 | 2 |
| dxy-vision | spy-vision | 0.8193 | 0.413 | 12 | 2 |
| dxy-vision | unimodal | 0.4789 | 0.632 | 12 | 2 |
| funding | funding-vision | -1.8787 | 0.060 | 12 | 2 |
| funding | spy | -0.6221 | 0.534 | 12 | 2 |
| funding | spy-vision | -1.5637 | 0.118 | 12 | 2 |
| funding | unimodal | -1.5993 | 0.110 | 12 | 2 |
| funding-vision | spy | 0.1803 | 0.857 | 12 | 2 |
| funding-vision | spy-vision | -0.7903 | 0.429 | 12 | 2 |
| funding-vision | unimodal | -0.4742 | 0.635 | 12 | 2 |
| spy | spy-vision | -0.4990 | 0.618 | 12 | 2 |
| spy | unimodal | -0.3314 | 0.740 | 12 | 2 |
| spy-vision | unimodal | 0.0602 | 0.952 | 12 | 2 |

### Configs with no scored ledger yet

- gdelt
- gdelt+currents