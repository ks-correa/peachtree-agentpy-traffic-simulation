# PEACHTREE-3R — diagnóstico estructural TRAIN-only

El diagnóstico es **G: combinación de semántica de medición, contexto de recepción
no representado, salida al verde e inserción de frontera**. No se asumió esta causa
antes de analizar B2. AgentPy, dt 0,1 s, el subcorredor y el snapshot se conservan.
Hay 276 vehículos elegibles;274 participan en la ventana93,4–1032,7 s porque dos
ya habían salido. Se analizan21 iniciales y253 arrivals.

## Medición de stopped

B2 reporta velocidad con precisión de 0,01 ft/s; mínimo positivo observado0,03 ft/s,
con una masa exacta en0 y abundante velocidad positiva muy baja. No hay separación
natural clara entre creep y rest. No se eligió un umbral para minimizar el error.
Se congela **OPERATIONAL_STOPPED: v≤0,1 m/s (0.32808333 ft/s)** mediante la
[convención operacional de espera de SUMO](https://sumo.dlr.de/docs/Simulation/Output/TripInfo.html).
Se usa solo como definición de medición; no sustituye AgentPy ni su física.
**EXACT_ZERO_STOPPED: v==0** queda como métrica secundaria literal.
La antigua tolerancia numérica≤1e-6 m/s NO era literal zero. Sus resultados
originales se preservan, pero no se renombra esa cifra como exact-zero.

| series | upper_ft_s | exact_zero_fraction | positive_to_upper_fraction | cumulative_fraction |
| --- | --- | --- | --- | --- |
| REAL_B2 | 0.00000 | 0.09916 | 0.00000 | 0.09916 |
| REAL_B2 | 0.10000 | 0.09916 | 0.09418 | 0.19333 |
| REAL_B2 | 0.25000 | 0.09916 | 0.16459 | 0.26374 |
| REAL_B2 | 0.50000 | 0.09916 | 0.19268 | 0.29184 |
| REAL_B2 | 1.00000 | 0.09916 | 0.21673 | 0.31588 |
| REAL_B2 | 2.00000 | 0.09916 | 0.23797 | 0.33713 |
| REAL_B2 | 3.00000 | 0.09916 | 0.25195 | 0.35111 |
| OLD_BASELINE | 0.00000 | 0.00064 | 0.00000 | 0.00064 |
| OLD_BASELINE | 0.10000 | 0.00064 | 0.14545 | 0.14609 |
| OLD_BASELINE | 0.25000 | 0.00064 | 0.17695 | 0.17759 |
| OLD_BASELINE | 0.50000 | 0.00064 | 0.20604 | 0.20668 |
| OLD_BASELINE | 1.00000 | 0.00064 | 0.24124 | 0.24188 |
| OLD_BASELINE | 2.00000 | 0.00064 | 0.28368 | 0.28432 |
| OLD_BASELINE | 3.00000 | 0.00064 | 0.31280 | 0.31344 |
| REVISED_BASELINE | 0.00000 | 0.00559 | 0.00000 | 0.00559 |
| REVISED_BASELINE | 0.10000 | 0.00559 | 0.14696 | 0.15255 |
| REVISED_BASELINE | 0.25000 | 0.00559 | 0.17974 | 0.18533 |
| REVISED_BASELINE | 0.50000 | 0.00559 | 0.20990 | 0.21549 |
| REVISED_BASELINE | 1.00000 | 0.00559 | 0.24623 | 0.25182 |
| REVISED_BASELINE | 2.00000 | 0.00559 | 0.28952 | 0.29511 |
| REVISED_BASELINE | 3.00000 | 0.00559 | 0.31945 | 0.32504 |

Un operador diagnóstico de observación, redondear a la precisión reportada0,01 ft/s,
produce zero fractions9,9158% REAL,7,7386% OLD y8,2018% REVISED de referencia.
Así, buena parte del déficit aparente de exact-zero procede de comparar continuo
con discretizado. Este operador NO cambia la definición operacional congelada,
no modifica física y no se presenta como el filtro interno conocido de NGSIM.
Además, el audit de desplazamiento detecta jitter: entre 0<reported v≤0,1 ft/s,
20,36% de pasos REAL tienen Y constante y18,20% retroceso aparente; el simulator
no retrocede. No se inventa un modelo de measurement noise a partir de eso.

| series | literal_zero_fraction | rounded_to_source_0_01_ft_s_zero_fraction | reported_precision_ft_s |
| --- | --- | --- | --- |
| REAL_B2 | 0.09916 | 0.09916 | 0.01000 |
| OLD_BASELINE | 0.00064 | 0.07739 | 0.01000 |
| REVISED_BASELINE | 0.00559 | 0.08202 | 0.01000 |

La comparación operacional no resuelve el fallo: REAL 27,4785%, OLD 18,7767%.
Tras la última línea controlada de cada sentido, el exposure operacional es
6.4092% de TODOS los frames REAL y0.0006% OLD.
Ese tramo explica73.65% de la discrepancia operacional OLD. Esto localiza
el problema; no identifica causalmente qué restricción externa, prioridad o
interacción produce cada stop. No se usaron salidas reales como calendario de
servicio, bloqueos falsos, posiciones históricas ni otros mecanismos de replay.

## Episodios y señalización

Un episodio es una secuencia máxima de ticks contiguos clasificados stopped.
Gaps de frame lo separan. Censura izquierda/derecha explícita; las duraciones
comparadas excluyen episodios truncados, pero se conserva su conteo. No se impone
una duración mínima elegida por ajuste. Onset/release registran fase y distancia.

| series | vehicles_stopped | episodes | complete_episodes | duration_mean_s | duration_median_s | duration_P25_s | duration_P75_s | duration_max_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REAL_B2 | 218 | 334 | 321 | 13.51340 | 11.60000 | 1.90000 | 20.20000 | 56.60000 |
| OLD_BASELINE | 186 | 219 | 205 | 14.68829 | 12.60000 | 7.90000 | 19.00000 | 48.10000 |
| REVISED_BASELINE | 196 | 232 | 216 | 15.00463 | 13.85000 | 7.87500 | 19.82500 | 48.20000 |

| series | intersection | direction | phase | n | operational_stopped_fraction |
| --- | --- | --- | --- | --- | --- |
| OLD_BASELINE | 2 | 2 | GREEN | 8337 | 0.03862 |
| OLD_BASELINE | 2 | 2 | RED | 12796 | 0.61199 |
| OLD_BASELINE | 2 | 2 | YELLOW | 292 | 0.00000 |
| OLD_BASELINE | 2 | 4 | GREEN | 20781 | 0.06184 |
| OLD_BASELINE | 2 | 4 | RED | 35678 | 0.19959 |
| OLD_BASELINE | 3 | 2 | GREEN | 16648 | 0.10686 |
| OLD_BASELINE | 3 | 2 | RED | 25362 | 0.40088 |
| OLD_BASELINE | 3 | 2 | YELLOW | 1541 | 0.00000 |
| OLD_BASELINE | 3 | 4 | GREEN | 8306 | 0.00891 |
| OLD_BASELINE | 3 | 4 | RED | 4947 | 0.33455 |
| OLD_BASELINE | 3 | 4 | YELLOW | 64 | 0.00000 |
| REAL_B2 | 2 | 2 | GREEN | 8483 | 0.04032 |
| REAL_B2 | 2 | 2 | RED | 6103 | 0.41488 |
| REAL_B2 | 2 | 2 | YELLOW | 270 | 0.00000 |
| REAL_B2 | 2 | 4 | GREEN | 15634 | 0.19969 |
| REAL_B2 | 2 | 4 | RED | 33931 | 0.28685 |
| REAL_B2 | 3 | 2 | GREEN | 20770 | 0.34954 |
| REAL_B2 | 3 | 2 | RED | 19311 | 0.44653 |
| REAL_B2 | 3 | 2 | YELLOW | 1552 | 0.00000 |
| REAL_B2 | 3 | 4 | GREEN | 9524 | 0.06552 |
| REAL_B2 | 3 | 4 | RED | 4766 | 0.37935 |
| REAL_B2 | 3 | 4 | YELLOW | 49 | 0.00000 |
| REVISED_BASELINE | 2 | 2 | GREEN | 9070 | 0.07784 |
| REVISED_BASELINE | 2 | 2 | RED | 12313 | 0.59799 |
| REVISED_BASELINE | 2 | 2 | YELLOW | 318 | 0.00314 |
| REVISED_BASELINE | 2 | 4 | GREEN | 23017 | 0.11869 |
| REVISED_BASELINE | 2 | 4 | RED | 35214 | 0.19086 |
| REVISED_BASELINE | 2 | 4 | YELLOW | 6 | 0.00000 |
| REVISED_BASELINE | 3 | 2 | GREEN | 17879 | 0.16595 |
| REVISED_BASELINE | 3 | 2 | RED | 26070 | 0.38918 |
| REVISED_BASELINE | 3 | 2 | YELLOW | 1618 | 0.00000 |
| REVISED_BASELINE | 3 | 4 | GREEN | 8781 | 0.03086 |
| REVISED_BASELINE | 3 | 4 | RED | 5245 | 0.31039 |
| REVISED_BASELINE | 3 | 4 | YELLOW | 66 | 0.00000 |

El modelo RESPETA rojo y forma colas. Por ejemplo I2 NB OLD tiene61,20% operational
stopping en RED frente41,49% REAL. No es ausencia de respuesta al rojo. En cambio
hay detenciones reales importantes en GREEN y después de la última señal que no
se reproducen. Falta una distribución espacial/temporal correcta de las colas.
Cuando no hay observaciones de una fase, el indicador es no estimable, no cero.
Bandas físicas congeladas0–50,50–100,100–200,200+ft se exportan por separado.

## Stop-lines y sincronización

| intersection | direction | OLD_STOPLINE | NEW_STOPLINE | distance_median_ft | distance_P25_ft | distance_P75_ft | distance_P95_ft |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 632.53950 | 632.53950 | 11.63650 | 9.91550 | 15.30100 | 30.28260 |
| 2 | 4 | 777.26200 | 777.26200 | 6.68600 | 2.09925 | 21.96550 | 335.30000 |
| 3 | 2 | 1168.91550 | 1168.91550 | 8.60950 | 5.28900 | 13.25250 | 15.35805 |
| 3 | 4 | 1240.77750 | 1240.77750 | 10.16350 | 7.52350 | 16.62950 | 31.96350 |

Las referencias permanecen632,5395/777,262 ft en 11th y1168,9155/1240,7775 ft en 12th.
Medianas de cabezas en rojo a6,69–11,64 ft de los proxies, contra6,84–6,86 ft OLD.
Estas cabezas no son un levantamiento de painted stop bars. Las colas muy alejadas
y los gaps no justifican mover la geometría por ajuste. OLD_STOPLINE=NEW_STOPLINE.

| intersection | direction | GREEN_crossings | RED_crossings | YELLOW_crossings | UNKNOWN_crossings | unknown_clock_ticks | OLD_OFFSET_s | NEW_OFFSET_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 91 | 15 | 3 | 0 | 0.00000 | 0.00000 | 0.00000 |
| 2 | 4 | 145 | 8 | 0 | 0 | 0.00000 | 0.00000 | 0.00000 |
| 3 | 2 | 87 | 20 | 13 | 0 | 0.00000 | 0.00000 | 0.00000 |
| 3 | 4 | 148 | 3 | 2 | 0 | 0.00000 | 0.00000 | 0.00000 |

No se identificó con documentación una inversión de dirección/fase, pérdida de
cobertura ni offset corregible. Se conservan clocks, dirección y schedules.
Los cruces reales en rojo respecto a mouths aproximados quedan registrados;
no prueban por sí mismos un offset ni que la referencia sea una painted bar.
Las cuatro figuras superponen fases, stopped count y crossings en el mismo reloj.
Correlación RED/count es descriptiva, no optimización de timing.

## Líderes e interacciones omitidas

Referencia usable requiere presencia same-frame, dirección/lane/section coherentes,
leader longitudinalmente delante y bumper gap positivo. Se distingue versión
geométrica y versión STRICT_ROAD con lane1/2,int_id0; no se confunde con el CF limpio
para calibración. El8.015% del seguimiento STRICT_ROAD tiene líder fuera
del target;8,8336% de los frames exact-zero válidos y8,8091% operational stopped.
Se exportan denominadores y categorías A/B/C/D, incluida referencia no utilizable.

| subset | category | frames | denominator | fraction |
| --- | --- | --- | --- | --- |
| STRICT_ROAD_VALID_FOLLOWING | D_UNUSABLE | 0 | 89872 | 0.00000 |
| STRICT_ROAD_VALID_FOLLOWING | A_TARGET | 82669 | 89872 | 0.91985 |
| STRICT_ROAD_VALID_FOLLOWING | B_EXCLUDED_CLASS23_IN_BAND | 6860 | 89872 | 0.07633 |
| STRICT_ROAD_VALID_FOLLOWING | C_OTHER_OBSERVED | 343 | 89872 | 0.00382 |
| STRICT_ROAD_EXACT_ZERO_FOLLOWING | D_UNUSABLE | 0 | 8728 | 0.00000 |
| STRICT_ROAD_EXACT_ZERO_FOLLOWING | A_TARGET | 7957 | 8728 | 0.91166 |
| STRICT_ROAD_EXACT_ZERO_FOLLOWING | B_EXCLUDED_CLASS23_IN_BAND | 771 | 8728 | 0.08834 |
| STRICT_ROAD_EXACT_ZERO_FOLLOWING | C_OTHER_OBSERVED | 0 | 8728 | 0.00000 |
| STRICT_ROAD_OPERATIONAL_FOLLOWING | D_UNUSABLE | 0 | 23998 | 0.00000 |
| STRICT_ROAD_OPERATIONAL_FOLLOWING | A_TARGET | 21884 | 23998 | 0.91191 |
| STRICT_ROAD_OPERATIONAL_FOLLOWING | B_EXCLUDED_CLASS23_IN_BAND | 2114 | 23998 | 0.08809 |
| STRICT_ROAD_OPERATIONAL_FOLLOWING | C_OTHER_OBSERVED | 0 | 23998 | 0.00000 |

| interaction | target_frames | target_vehicles | background_vehicles | interpretation |
| --- | --- | --- | --- | --- |
| same_lane_geometric_predecessor | 11074 | 109 | 90 | geometric interaction opportunity; not independent causal effect |
| operationally_stopped_queue_predecessor | 1913 | 12 | 11 | observed adjacent queued predecessor outside target cohort |
| adjacent_lane_overlap | 5848 | 91 | 42 | spatial proximity proxy only; no assertion of conflict or influence |
| nearby_turning_50ft | 16840 | 233 | 83 | spatial proximity proxy only; no assertion of conflict or influence |

La omisión existe; proximidad lateral/turning NO equivale a conflicto causal.
La confianza de su contribución contrafactual al fallo global es MEDIUM, no HIGH.
No se añadieron background agents: no se sustentó una red completa de movimientos,
permisos y receiving constraints para ellos. Añadir turning agents arbitrarios
para producir colas sería una corrección sin evidencia. El rol TARGET/BACKGROUND
está soportado y probado sintéticamente; en los experimentos hay 274 TARGET y0 BG.
Los primeros vehículos reales para geometría/release incluyen todo el contexto
arterial observado, y las colas físicas se exportan además de las target-only.

## Frontera, inicialización y salida al verde

| series | n | mean_s | median_s | P95_s | max_s | same_lane_order_inversion_pairs | percentage_delayed_beyond_one_tick | phase_changed_count | phase_changed_fraction | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OLD_BASELINE | 253 | 0.96867 | 0.05845 | 6.30001 | 37.02266 | 24 | 18.97233 | 12 | 0.04743 | Sub-tick clock rounding is not unsafe insertion delay; up to one tick expected |
| REVISED_BASELINE | 253 | 0.83508 | 0.06001 | 6.47020 | 13.72163 | 0 | 21.34387 | 7 | 0.02767 | Sub-tick clock rounding is not unsafe insertion delay; up to one tick expected |

La frontera OLD permitía overtaking de arrivals dentro del mismo carril:24 pares
de scheduled order invertido. Es un error de implementación verificable. FIFO
por dirección/lane elimina esas inversiones sin alterar la condición de gap,
deceleración segura o crear solapamiento. No se fuerza entrada a su hora prevista.
Scheduled y actual time, phase change y cola pendiente siguen registrados.

El snapshot original conserva21 vehículos, velocidad media2,4543 ft/s y 12 ya
operationally stopped. No es artificialmente fluido en t0. La evolución posterior
sí pierde restricciones no representadas; eso no autoriza mover el snapshot.
Posiciones, leaders, phase, clearance y transient0–10/10–60 s están exportados.

Se estimó SIGNAL_RELEASE_DELAY desde 37 primeras cabezas Through reales, normales,
dentro100ft antes del verde, con contexto completo observado para identificar
quién era realmente primero. Mediana 1,6 s,IQR1,2–2,7 s. La muestra es heterogénea
entre aproximaciones y no demuestra un parámetro cognitivo universal. Se usa
UNA mediana pooled, DATASET_DERIVED, congelada antes de revised rollouts. El pooling
constante es una simplificación explícita. Hold=mediana−dt para contar el tick
físico hasta cruzar el threshold de movimiento. Solo se retiene la primera cabeza;
los followers responden por IDM. No se añade delay individual a toda la cola.

| series | count | mean | median |
| --- | --- | --- | --- |
| OLD_BASELINE | 147 | 6.08994 | 3.14660 |
| REAL_B2 | 42 | 5.53476 | 2.82557 |
| REVISED_BASELINE | 142 | 5.90140 | 3.14330 |

Estos discharge intervals usan TARGET ya queued antes de green dentro100ft.
Se exporta también todo green crossing headway. No son garantía de saturación:
hay demanda discontinua y background omitido. OLD median 3,147 s vs REAL 2,826 s no
sustenta una descarga excesivamente rápida entre vehículos. No se añadió otro
parámetro de saturation headway.

## Queue, temporalidad y headway

Queue: cadena de operationally stopped desde la cabeza más próxima al control,
misma lane, adyacencia limitada por B2 standstill-gap P90. Métrica target-only y
contexto arterial completo se etiquetan explícitamente; excluir una cabeza BG
puede romper una cadena target-only. No se interpreta su máximo como toda la cola.

| series | intersection | direction | mean | median | P90 | max | duration_above_zero_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| REAL_B2 | 2 | 2 | 0.22344 | 0.00000 | 1.00000 | 2 | 142.20000 |
| REAL_B2 | 2 | 4 | 0.66638 | 0.00000 | 3.00000 | 9 | 173.90000 |
| REAL_B2 | 3 | 2 | 0.96157 | 0.00000 | 2.00000 | 9 | 360.90000 |
| REAL_B2 | 3 | 4 | 0.18938 | 0.00000 | 1.00000 | 4 | 119.60000 |
| OLD_BASELINE | 2 | 2 | 0.83681 | 0.00000 | 3.00000 | 7 | 303.80000 |
| OLD_BASELINE | 2 | 4 | 0.76655 | 0.00000 | 4.00000 | 10 | 153.10000 |
| OLD_BASELINE | 3 | 2 | 1.08463 | 0.00000 | 5.00000 | 15 | 232.60000 |
| OLD_BASELINE | 3 | 4 | 0.17809 | 0.00000 | 1.00000 | 4 | 99.70000 |
| REVISED_BASELINE | 2 | 2 | 0.83319 | 0.00000 | 3.00000 | 6 | 311.80000 |
| REVISED_BASELINE | 2 | 4 | 0.84927 | 0.00000 | 4.00000 | 10 | 163.40000 |
| REVISED_BASELINE | 3 | 2 | 1.19108 | 0.00000 | 5.00000 | 14 | 246.70000 |
| REVISED_BASELINE | 3 | 4 | 0.19587 | 0.00000 | 1.00000 | 4 | 107.40000 |
| REAL_B2_ALL_OBSERVED_ARTERIAL | 2 | 2 | 0.34330 | 0.00000 | 2.00000 | 4 | 163.30000 |
| REAL_B2_ALL_OBSERVED_ARTERIAL | 2 | 4 | 0.70981 | 0.00000 | 3.00000 | 9 | 191.30000 |
| REAL_B2_ALL_OBSERVED_ARTERIAL | 3 | 2 | 1.06302 | 0.00000 | 2.00000 | 14 | 354.60000 |
| REAL_B2_ALL_OBSERVED_ARTERIAL | 3 | 4 | 0.19821 | 0.00000 | 1.00000 | 4 | 124.50000 |

Bins10/30/60 s se alinean por tick 0,1 s. Occupancy sin vehículos es0; velocidad y
stopped fraction sin observaciones son indefinidas. No se rellenan como velocidad0.
Se reporta número de bins comparables para no esconder ventanas vacías.

| series | bin_s | metric | RMSE | bias | correlation | MAE | bins_compared |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OLD_BASELINE | 10.00000 | speed | 3.81684 | -0.03991 | 0.91532 | 2.90859 | 87 |
| OLD_BASELINE | 10.00000 | stopped | 0.14599 | -0.08806 | 0.86875 | 0.10280 | 87 |
| OLD_BASELINE | 10.00000 | active | 2.20879 | -0.05926 | 0.96227 | 1.43053 | 94 |
| OLD_BASELINE | 10.00000 | throughput | 1.81600 | 0.00000 | 0.86459 | 1.25532 | 94 |
| OLD_BASELINE | 30.00000 | speed | 2.65738 | -0.02315 | 0.91315 | 1.78554 | 29 |
| OLD_BASELINE | 30.00000 | stopped | 0.12082 | -0.08821 | 0.82064 | 0.09140 | 29 |
| OLD_BASELINE | 30.00000 | active | 1.92952 | -0.05802 | 0.97048 | 1.30115 | 32 |
| OLD_BASELINE | 30.00000 | throughput | 2.51247 | 0.00000 | 0.91279 | 1.68750 | 32 |
| OLD_BASELINE | 60.00000 | speed | 3.97302 | -0.82815 | 0.36043 | 2.08942 | 15 |
| OLD_BASELINE | 60.00000 | stopped | 0.14746 | -0.05933 | -0.22624 | 0.11203 | 15 |
| OLD_BASELINE | 60.00000 | active | 1.63490 | -0.05399 | 0.97451 | 1.19934 | 16 |
| OLD_BASELINE | 60.00000 | throughput | 2.47487 | 0.00000 | 0.94366 | 1.75000 | 16 |
| REVISED_BASELINE | 10.00000 | speed | 3.94369 | -0.48877 | 0.91242 | 3.05475 | 87 |
| REVISED_BASELINE | 10.00000 | stopped | 0.14648 | -0.07972 | 0.85295 | 0.10281 | 87 |
| REVISED_BASELINE | 10.00000 | active | 2.50537 | 0.46223 | 0.95327 | 1.75500 | 94 |
| REVISED_BASELINE | 10.00000 | throughput | 1.88499 | 0.00000 | 0.85389 | 1.36170 | 94 |
| REVISED_BASELINE | 30.00000 | speed | 2.97573 | -0.47201 | 0.89060 | 1.96965 | 29 |
| REVISED_BASELINE | 30.00000 | stopped | 0.11627 | -0.07987 | 0.81091 | 0.08727 | 29 |
| REVISED_BASELINE | 30.00000 | active | 2.17834 | 0.45260 | 0.96429 | 1.55740 | 32 |
| REVISED_BASELINE | 30.00000 | throughput | 3.17214 | 0.00000 | 0.85931 | 2.25000 | 32 |
| REVISED_BASELINE | 60.00000 | speed | 4.24162 | -1.25439 | 0.30652 | 2.20390 | 15 |
| REVISED_BASELINE | 60.00000 | stopped | 0.14832 | -0.05064 | -0.24695 | 0.10801 | 15 |
| REVISED_BASELINE | 60.00000 | active | 1.83161 | 0.46404 | 0.97039 | 1.43008 | 16 |
| REVISED_BASELINE | 60.00000 | throughput | 2.89396 | 0.00000 | 0.92203 | 2.12500 | 16 |

| series | bin_s | maximum_cumulative_departure_deviation | maximum_cumulative_departure_deviation_event_times | MAE_per_bin | timing_bias_s | real_total | simulated_total | timing_bias_definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OLD_BASELINE | 10.00000 | 8 | 8.00000 | 1.25532 | 0.73862 | 274 | 274 | sorted departures, not paired vehicle trajectories |
| OLD_BASELINE | 30.00000 | 7 | 8.00000 | 1.68750 | 0.73862 | 274 | 274 | sorted departures, not paired vehicle trajectories |
| OLD_BASELINE | 60.00000 | 6 | 8.00000 | 1.75000 | 0.73862 | 274 | 274 | sorted departures, not paired vehicle trajectories |
| REVISED_BASELINE | 10.00000 | 7 | 9.00000 | 1.36170 | 2.40397 | 274 | 274 | sorted departures, not paired vehicle trajectories |
| REVISED_BASELINE | 30.00000 | 7 | 9.00000 | 2.25000 | 2.40397 | 274 | 274 | sorted departures, not paired vehicle trajectories |
| REVISED_BASELINE | 60.00000 | 6 | 9.00000 | 2.12500 | 2.40397 | 274 | 274 | sorted departures, not paired vehicle trajectories |

El máximo acumulado en event times es8 vehículos OLD y9 REVISED; evaluar solo
edges de 10 s daría8 y7 y ocultaría ese empeoramiento. MAE30s1,6875→2,25 veh/bin;
timing bias0,739→2,404 s en referencias prefijadas. Total274=274 no prueba fidelity.
Condicionales de headway por estado/fase/distancia se exportan; headway sin líder
es indefinido, no0. Primary headway compara CF REAL limpio con leaders simulados
en la misma sección vial. No son muestras individualmente emparejadas y la selección
de calidad puede influir. KS es distancia descriptiva, no inferencia iid de frames.

## Orden de causas y decisión previa al cambio

| cause | evidence | effect_on_stopping | effect_on_headway | confidence | requires_model_change |
| --- | --- | --- | --- | --- | --- |
| STOP_METRIC_SEMANTICS | Literal zero: B2 9.9158%, OLD 0.0640%; prior simulator stopped used <=1e-6 m/s, not literal zero. Operational0.1 m/s:27.4785% vs18.7767%.; diagnostic round-to-reported0.01 ft/s yields9.916%REAL,7.739%OLD,8.202%REVISED reference, illustrating continuous/discrete comparison. Primary operational threshold unchanged. | Changes reported states, does not eliminate absolute discrepancy | Changes conditional headway sample | HIGH | True |
| UNMODELED_DOWNSTREAM_RECEIVING_CONTEXT | 6.4092% of all real target frames are operationally stopped after last included controlled line vs0.0006% in OLD; accounts for73.65% of operational global gap. | Dominant residual location; downstream cause is not causally identified | Uncontrolled target trajectories contribute different following conditions | HIGH | True |
| SIGNAL_ALIGNMENT | Most crossing events GREEN, no UNKNOWN; no official alternate offset/direction assignment identified | RED respected; residual RED crossings in source cannot justify arbitrary offset | No identified change | LOW | False |
| STOPLINE_GEOMETRY | Observed RED head medians6.69-11.64 ft before proxy vs simulated6.84-6.86 ft; tails include non-head/omitted-context effects | No independently surveyed bar correction identified | Geometry uncertainty retained | LOW | False |
| SAFE_INSERTION_DELAY | OLD seed10 mean 0.969 s P95~6.3 s max 37.02 s;12/253 changed first-signal phase; actual insertion has24 same-lane scheduled-order inversion pairs: implementation defect corrected with FIFO. | Material for some arrivals; not dominant global state gap | Can alter platoon composition | HIGH | True |
| OMITTED_BACKGROUND_TRAFFIC | 8.11% usable Preceding-following frames external to target;8.83% exact-zero valid following.11 excluded queue predecessors for12 targets; geometric opportunity larger. | Observed omitted interaction; magnitude/causal counterfactual uncertain | Can affect conditional headway | MEDIUM | False |
| GREEN_RELEASE | 37 confirmed Through first-head observations in band:median 1.6 s,IQR1.2-2.7 s; OLDfirst-head0.1 s. | Observable delayed release missing from model | Changes discharge and queue following | HIGH | True |
| DISCHARGE_DYNAMICS | Lane-specific green crossing intervals exported; include demand gaps, not identifiable pure saturation | Linked to release but no new saturation parameter identified | No independent new parameter | MEDIUM | False |
| IDM_PARAMETERS | Good global speed/travel, stop episode occurrence low while complete mean duration14.69 s vs13.51 s | Not identified as primary cause; fitting would risk compensating missing downstream context | T not automatically recalibrated | LOW | False |
| LANE_CHANGE_SIMPLIFICATION | Sparse21 confirmed TRAIN changes; adjacent-lane proximity is not proven conflict | Remaining unmodeled interaction | Possible contributor | MEDIUM | False |

Los5 IDM permanecen fijos. Internal section travel OLD 37,741 s vs REAL 34,214 s ya
difiere, aunque el total coincide; esto sugiere compensación entre componentes,
no identificación de un error de parámetro aislado. No se recalibró T ni se
alteraron pesos para forzar stopped_fraction. La estructura de receiving sigue
sin identificarse; optimizar ahora podría ocultarla.

Clasificación final: **B. BASELINE_NEEDS_REVISION**. B1 LOCKED. E1/E2/E3 DISABLED.
