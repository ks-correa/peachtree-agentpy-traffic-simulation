# PEACHTREE-6 — final scenario experimentation

**A. SCENARIO_EXPERIMENTATION_COMPLETE**. Recommended within evaluated alternatives: **E1**. Exactly3 alternatives, BASE reference, two observed acquisition contexts; no optimizer or new timing search.

## 1–10. Frozen scenario design

BASE preserves each acquisition's observed schedule. E1 nominal Through green+10%, funded from same-cycle RED, with0.1s floor and RED>=0.1s feasibility constraint. GREEN onset/next GREEN onset (cycle) and YELLOW duration remain fixed. Partial cycles remain unchanged unless covered by complete experimental edge-extension cycles. All-red is not separately represented/observed; no independent all-red phase is altered. E1 is EXPERIMENTAL_RULE, never operational field timing.

E2 dominant B2 direction=SB; counts={'2': 121, '4': 153}. Progression median=19.870570s, n=41, P25=15.749255986871589, P75=33.23471817465128, IQR=17.48546218777969. Source B2 REAL no-stop complete Through trips between effective controls, contiguous tracking, operational<=0.1m/s exclusion; minimum10 trips predeclared. No B1 or SIM outcome selects the direction/time.

Upstream=3, downstream=2. BASE offset=41.200000s; E2 offset=19.870570s; reference cycle=100.100000s; single shift=-21.329430s. Translate the entire downstream intersection NB/SB timelines by that SAME shift, both contexts. Observed cycle/phase durations retained internally; nearest complete observed cycle repeats only outside original coverage to support horizon-edge translation. This edge assumption is explicit, never selected by outcome. E3 is exactly E1+the same E2 shift, no recalculation.

Design and score were hashed before first scenario rollout. Seeds7000–7029 paired for all4 modes and both contexts: **240 official runs**. Extra repeated seed7000 traces support rendering only, not statistical sample size or seed selection. All arrivals/snapshots/speed pools/physics/parameters/controls/lanes/FIFO/thresholds/scopes remain frozen; only signal inputs differ. No REAL_E1/E2/E3 data exist or are generated.

## 11–23. Results and directional tradeoffs

| context | metric | BASE | E1 | E2 | E3 |
| --- | --- | --- | --- | --- | --- |
| B1 | NB_operational_stopped | 0.3492 | 0.2615 | 0.4172 | 0.3832 |
| B1 | NB_travel_mean_s | 51.0079 | 41.2553 | 60.8841 | 54.5472 |
| B1 | SB_operational_stopped | 0.2681 | 0.2298 | 0.4181 | 0.3826 |
| B1 | SB_travel_mean_s | 39.0020 | 33.7789 | 52.8406 | 48.2145 |
| B1 | clearance_mean_s | 10.0371 | 8.8996 | 13.5578 | 13.8658 |
| B1 | departure_final_s | 894.9765 | 894.9750 | 951.8654 | 948.0562 |
| B1 | departure_t50_s | 485.4689 | 481.1721 | 482.3875 | 480.2099 |
| B1 | departure_t90_s | 793.0552 | 793.0552 | 844.2690 | 841.6282 |
| B1 | headway_mean_ft | 139.1980 | 161.5770 | 89.2264 | 94.9694 |
| B1 | mean_stopped_time_per_vehicle_s | 14.3591 | 9.3446 | 23.7141 | 19.6372 |
| B1 | operational_stopped | 0.3176 | 0.2487 | 0.4176 | 0.3830 |
| B1 | queue_mean | 0.7102 | 0.4982 | 1.2108 | 1.0486 |
| B1 | section_travel_mean_s | 25.5116 | 22.2122 | 25.5873 | 24.8472 |
| B1 | speed_mean_ft_s | 19.3349 | 23.2655 | 15.3922 | 17.0494 |
| B1 | stop_episodes_per_vehicle | 0.5687 | 0.4348 | 0.7121 | 0.6328 |
| B1 | travel_mean_s | 45.5595 | 37.8624 | 57.2338 | 51.6733 |
| B1 | vehicles_stopped_fraction | 0.5255 | 0.4113 | 0.7012 | 0.6231 |
| B2 | NB_operational_stopped | 0.3212 | 0.2197 | 0.3315 | 0.2671 |
| B2 | NB_travel_mean_s | 57.8534 | 43.6954 | 48.2381 | 41.3615 |
| B2 | SB_operational_stopped | 0.2007 | 0.1951 | 0.0944 | 0.0683 |
| B2 | SB_travel_mean_s | 49.6046 | 48.2872 | 32.2151 | 30.5985 |
| B2 | clearance_mean_s | 13.2427 | 12.2804 | 9.3726 | 8.6195 |
| B2 | departure_final_s | 906.6269 | 867.8891 | 855.1245 | 855.1245 |
| B2 | departure_t50_s | 451.6804 | 451.6804 | 431.3318 | 431.3318 |
| B2 | departure_t90_s | 764.3566 | 762.1453 | 743.0919 | 743.0919 |
| B2 | headway_mean_ft | 79.9230 | 84.7559 | 123.8452 | 131.6131 |
| B2 | mean_stopped_time_per_vehicle_s | 13.2131 | 9.2819 | 8.2661 | 5.7382 |
| B2 | operational_stopped | 0.2563 | 0.2050 | 0.2190 | 0.1679 |
| B2 | queue_mean | 0.7738 | 0.5767 | 0.5297 | 0.3843 |
| B2 | section_travel_mean_s | 36.2286 | 31.6408 | 20.3094 | 18.5778 |
| B2 | speed_mean_ft_s | 16.1326 | 18.3677 | 22.0361 | 24.3341 |
| B2 | stop_episodes_per_vehicle | 0.9107 | 0.7706 | 0.3881 | 0.3283 |
| B2 | travel_mean_s | 53.1258 | 46.3270 | 39.0550 | 35.1930 |
| B2 | vehicles_stopped_fraction | 0.7863 | 0.6835 | 0.3768 | 0.3202 |

Headway here reports all positive simulated leader spacing across the route, including interior, as SECONDARY_DIAGNOSTIC; it is not the cleaned road-CF absolute validation statistic and must not be compared to that value as a change of bias. Speed is contextual, never higher=automatically better. Queues have identical modeled populations across alternatives, so paired differences are informative; absolute REAL context remains different. Total throughput is fixed demand closure, never the primary improvement criterion. Departure50/90/final times use the full expected cohort; unfinished horizon-censored quantiles remain missing rather than use a smaller completed subset. Negative time differences improve progression; positive cumulative E−BASE departures indicate earlier discharge.

Stopped time equals sum of operational-stopped0.1s samples per vehicle, including zero-stop vehicles in the population mean. Total stopped-time exposure is separately retained. Initial-vehicle travel is censored and excluded from corridor mean, as in baseline. Section travel uses identical effective cuts/interpolation. NB/SB are reported separately so opposite-direction deterioration is explicit.

## 24–28. Paired effects, robustness, Pareto and score

| context | scenario | metric | mean | SD | CI95_low | CI95_high | median | P25 | P75 | mean_percentage_change | fraction_seeds_improved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | E1 | travel_mean_s | -7.6971 | 0.3142 | -7.8144 | -7.5797 | -7.7418 | -7.8596 | -7.5538 | -16.8934 | 1.0000 |
| B1 | E1 | section_travel_mean_s | -3.2994 | 0.2700 | -3.4002 | -3.1985 | -3.3188 | -3.5042 | -3.0981 | -12.9270 | 1.0000 |
| B1 | E1 | operational_stopped | -0.0689 | 0.0042 | -0.0705 | -0.0674 | -0.0690 | -0.0717 | -0.0669 | -21.7056 | 1.0000 |
| B1 | E1 | vehicles_stopped_fraction | -0.1142 | 0.0059 | -0.1164 | -0.1120 | -0.1155 | -0.1155 | -0.1116 | -21.7306 | 1.0000 |
| B1 | E1 | stop_episodes_per_vehicle | -0.1339 | 0.0075 | -0.1367 | -0.1311 | -0.1355 | -0.1384 | -0.1275 | -23.5323 | 1.0000 |
| B1 | E1 | departure_t50_s | -4.2968 | 5.0532 | -6.1837 | -2.4099 | -2.6407 | -2.6407 | -2.6407 | -0.8851 | 1.0000 |
| B1 | E1 | departure_t90_s | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| B1 | E1 | departure_final_s | -0.0015 | 0.0077 | -0.0044 | 0.0014 | 0.0000 | 0.0000 | 0.0000 | -0.0002 | 0.0667 |
| B1 | E1 | NB_travel_mean_s | -9.7526 | 0.4627 | -9.9254 | -9.5799 | -9.7777 | -10.0401 | -9.4514 | -19.1170 | 1.0000 |
| B1 | E1 | NB_operational_stopped | -0.0876 | 0.0055 | -0.0897 | -0.0856 | -0.0870 | -0.0918 | -0.0845 | -25.0974 | 1.0000 |
| B1 | E1 | SB_travel_mean_s | -5.2231 | 0.4376 | -5.3865 | -5.0597 | -5.2250 | -5.5431 | -5.0432 | -13.3873 | 1.0000 |
| B1 | E1 | SB_operational_stopped | -0.0383 | 0.0054 | -0.0403 | -0.0363 | -0.0380 | -0.0427 | -0.0346 | -14.2767 | 1.0000 |
| B1 | E2 | travel_mean_s | 11.6744 | 0.6256 | 11.4408 | 11.9080 | 11.6280 | 11.2514 | 12.0069 | 25.6274 | 0.0000 |
| B1 | E2 | section_travel_mean_s | 0.0757 | 0.2726 | -0.0261 | 0.1775 | 0.0518 | -0.1169 | 0.2825 | 0.3055 | 0.4000 |
| B1 | E2 | operational_stopped | 0.1000 | 0.0036 | 0.0986 | 0.1013 | 0.0995 | 0.0975 | 0.1034 | 31.4799 | 0.0000 |
| B1 | E2 | vehicles_stopped_fraction | 0.1757 | 0.0123 | 0.1711 | 0.1803 | 0.1773 | 0.1713 | 0.1833 | 33.4381 | 0.0000 |
| B1 | E2 | stop_episodes_per_vehicle | 0.1434 | 0.0117 | 0.1391 | 0.1478 | 0.1474 | 0.1365 | 0.1514 | 25.2269 | 0.0000 |
| B1 | E2 | departure_t50_s | -3.0814 | 0.4687 | -3.2564 | -2.9064 | -3.1772 | -3.4240 | -2.8447 | -0.6347 | 1.0000 |
| B1 | E2 | departure_t90_s | 51.2138 | 0.1926 | 51.1419 | 51.2857 | 51.2275 | 51.0852 | 51.3452 | 6.4578 | 0.0000 |
| B1 | E2 | departure_final_s | 56.8889 | 0.1936 | 56.8166 | 56.9612 | 56.9117 | 56.8031 | 57.0432 | 6.3565 | 0.0000 |
| B1 | E2 | NB_travel_mean_s | 9.8761 | 1.0254 | 9.4932 | 10.2590 | 9.8110 | 9.4342 | 10.5439 | 19.3676 | 0.0000 |
| B1 | E2 | NB_operational_stopped | 0.0680 | 0.0048 | 0.0662 | 0.0698 | 0.0674 | 0.0648 | 0.0710 | 19.4813 | 0.0000 |
| B1 | E2 | SB_travel_mean_s | 13.8386 | 0.4683 | 13.6638 | 14.0135 | 13.8214 | 13.7641 | 13.9152 | 35.4880 | 0.0000 |
| B1 | E2 | SB_operational_stopped | 0.1500 | 0.0057 | 0.1479 | 0.1521 | 0.1501 | 0.1462 | 0.1527 | 56.0158 | 0.0000 |
| B1 | E3 | travel_mean_s | 6.1139 | 0.6537 | 5.8698 | 6.3580 | 6.2479 | 5.4450 | 6.6272 | 13.4222 | 0.0000 |
| B1 | E3 | section_travel_mean_s | -0.6644 | 0.3874 | -0.8090 | -0.5197 | -0.7399 | -0.9434 | -0.3713 | -2.5914 | 0.9667 |
| B1 | E3 | operational_stopped | 0.0654 | 0.0041 | 0.0638 | 0.0669 | 0.0657 | 0.0629 | 0.0687 | 20.5819 | 0.0000 |
| B1 | E3 | vehicles_stopped_fraction | 0.0976 | 0.0125 | 0.0929 | 0.1023 | 0.0996 | 0.0876 | 0.1076 | 18.5821 | 0.0000 |
| B1 | E3 | stop_episodes_per_vehicle | 0.0641 | 0.0147 | 0.0587 | 0.0696 | 0.0677 | 0.0528 | 0.0747 | 11.2862 | 0.0000 |
| B1 | E3 | departure_t50_s | -5.2590 | 0.0001 | -5.2590 | -5.2590 | -5.2590 | -5.2590 | -5.2590 | -1.0833 | 1.0000 |
| B1 | E3 | departure_t90_s | 48.5731 | 0.1926 | 48.5012 | 48.6450 | 48.5868 | 48.4444 | 48.7045 | 6.1248 | 0.0000 |
| B1 | E3 | departure_final_s | 53.0797 | 0.1936 | 53.0074 | 53.1520 | 53.1025 | 52.9939 | 53.2340 | 5.9309 | 0.0000 |
| B1 | E3 | NB_travel_mean_s | 3.5393 | 1.0124 | 3.1612 | 3.9173 | 3.6273 | 3.0390 | 4.3591 | 6.9417 | 0.0000 |
| B1 | E3 | NB_operational_stopped | 0.0341 | 0.0052 | 0.0321 | 0.0360 | 0.0351 | 0.0316 | 0.0380 | 9.7634 | 0.0000 |
| B1 | E3 | SB_travel_mean_s | 9.2125 | 0.5520 | 9.0064 | 9.4187 | 9.2004 | 8.7994 | 9.7009 | 23.6300 | 0.0000 |
| B1 | E3 | SB_operational_stopped | 0.1145 | 0.0063 | 0.1121 | 0.1168 | 0.1143 | 0.1089 | 0.1192 | 42.7481 | 0.0000 |
| B2 | E1 | travel_mean_s | -6.7988 | 0.2830 | -6.9045 | -6.6931 | -6.7661 | -6.9034 | -6.6299 | -12.7953 | 1.0000 |
| B2 | E1 | section_travel_mean_s | -4.5878 | 0.1321 | -4.6371 | -4.5385 | -4.6148 | -4.6465 | -4.4660 | -12.6626 | 1.0000 |
| B2 | E1 | operational_stopped | -0.0513 | 0.0015 | -0.0518 | -0.0507 | -0.0512 | -0.0520 | -0.0504 | -20.0060 | 1.0000 |
| B2 | E1 | vehicles_stopped_fraction | -0.1028 | 0.0043 | -0.1044 | -0.1012 | -0.1022 | -0.1058 | -0.0985 | -13.0732 | 1.0000 |
| B2 | E1 | stop_episodes_per_vehicle | -0.1401 | 0.0065 | -0.1426 | -0.1377 | -0.1405 | -0.1451 | -0.1350 | -15.3850 | 1.0000 |
| B2 | E1 | departure_t50_s | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| B2 | E1 | departure_t90_s | -2.2112 | 0.0000 | -2.2112 | -2.2112 | -2.2112 | -2.2112 | -2.2112 | -0.2893 | 1.0000 |
| B2 | E1 | departure_final_s | -38.7377 | 0.0001 | -38.7378 | -38.7377 | -38.7377 | -38.7378 | -38.7376 | -4.2727 | 1.0000 |
| B2 | E1 | NB_travel_mean_s | -14.1580 | 0.4700 | -14.3335 | -13.9824 | -14.3345 | -14.5096 | -13.8751 | -24.4677 | 1.0000 |
| B2 | E1 | NB_operational_stopped | -0.1015 | 0.0026 | -0.1025 | -0.1005 | -0.1021 | -0.1026 | -0.1000 | -31.6026 | 1.0000 |
| B2 | E1 | SB_travel_mean_s | -1.3174 | 0.3189 | -1.4365 | -1.1984 | -1.2164 | -1.2525 | -1.1861 | -2.6519 | 1.0000 |
| B2 | E1 | SB_operational_stopped | -0.0055 | 0.0014 | -0.0061 | -0.0050 | -0.0049 | -0.0053 | -0.0048 | -2.7568 | 1.0000 |
| B2 | E2 | travel_mean_s | -14.0708 | 0.4608 | -14.2429 | -13.8988 | -14.0072 | -14.3273 | -13.7068 | -26.4835 | 1.0000 |
| B2 | E2 | section_travel_mean_s | -15.9192 | 0.3091 | -16.0346 | -15.8038 | -15.8617 | -16.1263 | -15.6464 | -43.9393 | 1.0000 |
| B2 | E2 | operational_stopped | -0.0372 | 0.0035 | -0.0386 | -0.0359 | -0.0363 | -0.0400 | -0.0347 | -14.5294 | 1.0000 |
| B2 | E2 | vehicles_stopped_fraction | -0.4095 | 0.0099 | -0.4132 | -0.4058 | -0.4088 | -0.4161 | -0.4051 | -52.0785 | 1.0000 |
| B2 | E2 | stop_episodes_per_vehicle | -0.5226 | 0.0097 | -0.5263 | -0.5190 | -0.5219 | -0.5292 | -0.5155 | -57.3868 | 1.0000 |
| B2 | E2 | departure_t50_s | -20.3486 | 0.0009 | -20.3489 | -20.3483 | -20.3486 | -20.3490 | -20.3483 | -4.5051 | 1.0000 |
| B2 | E2 | departure_t90_s | -21.2646 | 0.0000 | -21.2646 | -21.2646 | -21.2646 | -21.2646 | -21.2646 | -2.7820 | 1.0000 |
| B2 | E2 | departure_final_s | -51.5024 | 0.2425 | -51.5929 | -51.4118 | -51.5692 | -51.6931 | -51.3821 | -5.6807 | 1.0000 |
| B2 | E2 | NB_travel_mean_s | -9.6152 | 0.5378 | -9.8161 | -9.4144 | -9.5717 | -9.9982 | -9.2250 | -16.6172 | 1.0000 |
| B2 | E2 | NB_operational_stopped | 0.0103 | 0.0038 | 0.0089 | 0.0117 | 0.0111 | 0.0071 | 0.0128 | 3.2142 | 0.0000 |
| B2 | E2 | SB_travel_mean_s | -17.3895 | 0.5453 | -17.5931 | -17.1859 | -17.4332 | -17.4984 | -16.8498 | -35.0531 | 1.0000 |
| B2 | E2 | SB_operational_stopped | -0.1063 | 0.0055 | -0.1083 | -0.1042 | -0.1081 | -0.1089 | -0.1005 | -52.9639 | 1.0000 |
| B2 | E3 | travel_mean_s | -17.9328 | 0.3310 | -18.0564 | -17.8092 | -17.9091 | -18.2259 | -17.7709 | -33.7537 | 1.0000 |
| B2 | E3 | section_travel_mean_s | -17.6508 | 0.1425 | -17.7040 | -17.5976 | -17.6431 | -17.7329 | -17.5446 | -48.7201 | 1.0000 |
| B2 | E3 | operational_stopped | -0.0883 | 0.0032 | -0.0895 | -0.0872 | -0.0886 | -0.0908 | -0.0864 | -34.4720 | 1.0000 |
| B2 | E3 | vehicles_stopped_fraction | -0.4661 | 0.0099 | -0.4697 | -0.4624 | -0.4672 | -0.4708 | -0.4608 | -59.2733 | 1.0000 |
| B2 | E3 | stop_episodes_per_vehicle | -0.5824 | 0.0086 | -0.5856 | -0.5792 | -0.5803 | -0.5876 | -0.5776 | -63.9467 | 1.0000 |
| B2 | E3 | departure_t50_s | -20.3486 | 0.0009 | -20.3489 | -20.3483 | -20.3486 | -20.3490 | -20.3483 | -4.5051 | 1.0000 |
| B2 | E3 | departure_t90_s | -21.2646 | 0.0000 | -21.2646 | -21.2646 | -21.2646 | -21.2646 | -21.2646 | -2.7820 | 1.0000 |
| B2 | E3 | departure_final_s | -51.5024 | 0.2425 | -51.5929 | -51.4118 | -51.5692 | -51.6931 | -51.3821 | -5.6807 | 1.0000 |
| B2 | E3 | NB_travel_mean_s | -16.4919 | 0.5863 | -16.7108 | -16.2730 | -16.5849 | -16.8123 | -16.2443 | -28.5023 | 1.0000 |
| B2 | E3 | NB_operational_stopped | -0.0541 | 0.0053 | -0.0561 | -0.0521 | -0.0539 | -0.0582 | -0.0509 | -16.8339 | 1.0000 |
| B2 | E3 | SB_travel_mean_s | -19.0061 | 0.3278 | -19.1285 | -18.8837 | -18.9046 | -18.9449 | -18.8825 | -38.3129 | 1.0000 |
| B2 | E3 | SB_operational_stopped | -0.1324 | 0.0017 | -0.1330 | -0.1317 | -0.1320 | -0.1331 | -0.1315 | -65.9751 | 1.0000 |

| scenario | metric | classification | B2_effect | B1_effect |
| --- | --- | --- | --- | --- |
| E1 | NB_operational_stopped | ROBUST_IMPROVEMENT | -0.1015 | -0.0876 |
| E1 | NB_travel_mean_s | ROBUST_IMPROVEMENT | -14.1580 | -9.7526 |
| E1 | SB_operational_stopped | ROBUST_IMPROVEMENT | -0.0055 | -0.0383 |
| E1 | SB_travel_mean_s | ROBUST_IMPROVEMENT | -1.3174 | -5.2231 |
| E1 | departure_final_s | MIXED | -38.7377 | -0.0015 |
| E1 | departure_t50_s | MIXED | 0.0000 | -4.2968 |
| E1 | departure_t90_s | MIXED | -2.2112 | 0.0000 |
| E1 | operational_stopped | ROBUST_IMPROVEMENT | -0.0513 | -0.0689 |
| E1 | section_travel_mean_s | ROBUST_IMPROVEMENT | -4.5878 | -3.2994 |
| E1 | stop_episodes_per_vehicle | ROBUST_IMPROVEMENT | -0.1401 | -0.1339 |
| E1 | travel_mean_s | ROBUST_IMPROVEMENT | -6.7988 | -7.6971 |
| E1 | vehicles_stopped_fraction | ROBUST_IMPROVEMENT | -0.1028 | -0.1142 |
| E2 | NB_operational_stopped | ROBUST_WORSENING | 0.0103 | 0.0680 |
| E2 | NB_travel_mean_s | CONTEXT_DEPENDENT | -9.6152 | 9.8761 |
| E2 | SB_operational_stopped | CONTEXT_DEPENDENT | -0.1063 | 0.1500 |
| E2 | SB_travel_mean_s | CONTEXT_DEPENDENT | -17.3895 | 13.8386 |
| E2 | departure_final_s | CONTEXT_DEPENDENT | -51.5024 | 56.8889 |
| E2 | departure_t50_s | ROBUST_IMPROVEMENT | -20.3486 | -3.0814 |
| E2 | departure_t90_s | CONTEXT_DEPENDENT | -21.2646 | 51.2138 |
| E2 | operational_stopped | CONTEXT_DEPENDENT | -0.0372 | 0.1000 |
| E2 | section_travel_mean_s | CONTEXT_DEPENDENT | -15.9192 | 0.0757 |
| E2 | stop_episodes_per_vehicle | CONTEXT_DEPENDENT | -0.5226 | 0.1434 |
| E2 | travel_mean_s | CONTEXT_DEPENDENT | -14.0708 | 11.6744 |
| E2 | vehicles_stopped_fraction | CONTEXT_DEPENDENT | -0.4095 | 0.1757 |
| E3 | NB_operational_stopped | CONTEXT_DEPENDENT | -0.0541 | 0.0341 |
| E3 | NB_travel_mean_s | CONTEXT_DEPENDENT | -16.4919 | 3.5393 |
| E3 | SB_operational_stopped | CONTEXT_DEPENDENT | -0.1324 | 0.1145 |
| E3 | SB_travel_mean_s | CONTEXT_DEPENDENT | -19.0061 | 9.2125 |
| E3 | departure_final_s | CONTEXT_DEPENDENT | -51.5024 | 53.0797 |
| E3 | departure_t50_s | ROBUST_IMPROVEMENT | -20.3486 | -5.2590 |
| E3 | departure_t90_s | CONTEXT_DEPENDENT | -21.2646 | 48.5731 |
| E3 | operational_stopped | CONTEXT_DEPENDENT | -0.0883 | 0.0654 |
| E3 | section_travel_mean_s | ROBUST_IMPROVEMENT | -17.6508 | -0.6644 |
| E3 | stop_episodes_per_vehicle | CONTEXT_DEPENDENT | -0.5824 | 0.0641 |
| E3 | travel_mean_s | CONTEXT_DEPENDENT | -17.9328 | 6.1139 |
| E3 | vehicles_stopped_fraction | CONTEXT_DEPENDENT | -0.4661 | 0.0976 |

Pareto uses all predeclared primary metrics (including both directions), exact mean weak dominance plus one strict improvement; no p-values or post-hoc weights. Non-dominated alternatives must have a negative score in both contexts before the frozen equal-context score selects one; otherwise no alternative is recommended. Four score domains have equal25% weight: normalized corridor/section travel; normalized stopped fraction/incidence/time/episodes; departure50/90/final timing; worst-direction average relative travel/stopped change. Lower score is better. It is a secondary tie-break, not traffic timing optimization.

| context | scenario | other | dominates |
| --- | --- | --- | --- |
| B2 | E1 | BASE | True |
| B2 | E3 | BASE | True |
| B2 | E3 | E2 | True |
| B1 | E1 | BASE | True |
| B1 | E1 | E2 | True |
| B1 | E3 | E2 | True |

| context | scenario | TRAVEL | STOPPING | TEMPORAL_FLOW | DIRECTIONAL_BALANCE | DECISION_SCORE |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | E1 | -0.1491 | -0.2547 | -0.0030 | -0.1383 | -0.1363 |
| B1 | E2 | 0.1297 | 0.3883 | 0.0406 | 0.4575 | 0.2540 |
| B1 | E3 | 0.0542 | 0.2181 | 0.0366 | 0.3319 | 0.1602 |
| B2 | E1 | -0.1273 | -0.1955 | -0.0152 | -0.0270 | -0.0913 |
| B2 | E2 | -0.3521 | -0.4036 | -0.0432 | -0.0670 | -0.2165 |
| B2 | E3 | -0.4124 | -0.5356 | -0.0432 | -0.2267 | -0.3045 |

## 29–37. Emergence, interpretation, integrity, recommendation and UI

All configurations quantify queues under RED/GREEN, vehicle accumulation, collective speed variability, multiple-stop vehicles and GREEN discharge/clearance. Space-time figures separate NB/SB for predeclared B2 seed7000; the timelines show SB progression at both intersections. Results and conclusions use30 runs, not plots alone. Full per-seed queue/departure files and emergent_behavior.csv preserve collective evidence.

Recommended within scope: **E1**, derived by the frozen Pareto/score rule above. Read directional effects before interpreting global benefit. These are relative model effects under BASELINE_VALIDATED_WITH_LIMITATIONS: headway/stop episode/duration biases persist; turning/local/background/cross traffic and lateral-street effects are omitted; receiving cuts remain free; total demand is closed. This is not a field-ready plan, absolute capacity estimate, full Peachtree prediction or globally optimal timing.

All prior freezes and artifacts remain byte-identical. Experiment freeze=COMPLETED. No IDM/scope/baseline rules changed. Exactly3 alternatives. Tests preserve205 prior cases and add signal-only, cycle/yellow/offset/combination/paired-seed/invariant/UI/design checks; QA: 222 total, 196 passed, 26 skipped, zero failures/errors; details are in test_report.json. UI enables scenario/context/illustrative-seed controls, frozen IDM READ ONLY, live AgentPy scenario traces and explanatory progression overlay. Official statistics use the30 paired replicas. UI_IMPLEMENTED_NOT_BROWSER_VALIDATED.
