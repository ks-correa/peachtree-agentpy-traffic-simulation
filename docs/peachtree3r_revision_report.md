# PEACHTREE-3R — informe de revisión

**B. BASELINE_NEEDS_REVISION**. Se corrigieron mecanismos concretos y medibles;
el fallo residual impide abrir B1. No se reemplazó AgentPy ni se rehizo la red.

## Cambios mínimos implementados

1. Operational stopped≤0,1 m/s compartido REAL/OLD/REVISED; exact zero literal aparte.
2. Episodios con continuidad/censura y contexto de señales/distancias.
3. SIGNAL_RELEASE_DELAY pooled1,6 s desde 37 cabezas B2; hold solo al primer vehículo.
4. FIFO en safe insertion: no overtaking same-lane, sin eliminar seguridad.
5. Bins físicos y NaN de speed en ventanas sin vehículos; conservación de occupancy0.
6. Instrumentación de roles, inputs de revisión separados, guards B1, UI de revisión.

Geometría, offsets, arrivals programados, snapshot, clases, dt e IDM no cambiaron.
No se añadieron BG porque la evidencia causal para esa corrección es MEDIUM y
su movimiento/conflicto/receiving no estaba identificado. No hubo replay ni
animación falsa. No se ejecutó optimizer ni selección por seed: la estructura
recibió cambios directos fundamentados, y conservar IDM permite aislar el efecto.
Se difiere recalibración hasta resolver el contexto de recepción; no se presenta
esa recalibración como completada.

## OLD / REVISED / REAL

Referencias prefijadas OLDseed10 y REVISEDseed210, no escogidas por fit:

| metric | REAL_B2 | OLD_BASELINE | REVISED_BASELINE | population |
| --- | --- | --- | --- | --- |
| speed_mean | 16.48689 | 16.43300 | 15.94815 | TARGET |
| speed_KS | 0.00000 | 0.09852 | 0.09357 | TARGET |
| speed_W1 | 0.00000 | 1.07507 | 1.00857 | TARGET |
| headway_mean | 48.56370 | 54.57551 | 53.39280 | TARGET |
| headway_KS | 0.00000 | 0.10734 | 0.09648 | TARGET |
| headway_W1 | 0.00000 | 6.76311 | 5.95032 | TARGET |
| travel_time_mean | 60.75826 | 60.80966 | 62.69348 | TARGET |
| travel_time_KS | 0.00000 | 0.11067 | 0.16601 | TARGET |
| travel_time_W1 | 0.00000 | 3.23852 | 3.44951 | TARGET |
| exact_zero_stopped | 0.09916 | 0.00064 | 0.00559 | TARGET vehicle-time |
| operational_stopped | 0.27478 | 0.18777 | 0.19609 | TARGET vehicle-time |
| duration_mean_s | 13.51340 | 14.68829 | 15.00463 | TARGET; complete episodes for durations |
| duration_median_s | 11.60000 | 12.60000 | 13.85000 | TARGET; complete episodes for durations |
| episodes | 334.00000 | 219.00000 | 232.00000 | TARGET; complete episodes for durations |
| fraction_vehicles_stopped | 0.79562 | 0.67883 | 0.71533 | TARGET; complete episodes for durations |
| section_travel_time_mean | 34.21369 | 37.74084 | 39.18893 | TARGET complete same-reference cut pairs |
| throughput_total | 274.00000 | 274.00000 | 274.00000 | TARGET including initial |

Controles pareados OLD/REVISED con las mismas30 seeds3000–3029:

| metric | OLD_mean | REVISED_mean | paired_delta_mean | paired_delta_SD | CI95_delta_low | CI95_delta_high |
| --- | --- | --- | --- | --- | --- | --- |
| mean_speed_ft_s | 16.42341 | 15.91908 | -0.50433 | 0.03712 | -0.51819 | -0.49047 |
| mean_headway_ft | 54.52612 | 53.21238 | -1.31374 | 0.14201 | -1.36677 | -1.26072 |
| mean_travel_time_s | 60.84807 | 62.81212 | 1.96405 | 0.14705 | 1.90914 | 2.01896 |
| operational_stopped_fraction | 0.18714 | 0.19836 | 0.01122 | 0.00122 | 0.01076 | 0.01167 |
| fraction_vehicles_stopped | 0.67920 | 0.71253 | 0.03333 | 0.00496 | 0.03148 | 0.03518 |
| stop_duration_W1_s | 2.87535 | 2.81413 | -0.06122 | 0.05079 | -0.08018 | -0.04225 |
| throughput_temporal_normalized_error | 0.20122 | 0.26277 | 0.06156 | 0.00457 | 0.05985 | 0.06326 |
| max_cumulative_deviation_10s | 8.00000 | 7.00000 | -1.00000 | 0.00000 | -1.00000 | -1.00000 |
| throughput_MAE_10s | 1.24752 | 1.36170 | 0.11418 | 0.01308 | 0.10930 | 0.11907 |

Hay mejora de headway y stopped incidence, pero no readiness global. En30 réplicas
operational stopping18,7141% OLD→19,8358% revised frente27,4785% REAL. Literal
exact zero revised0,5661% frente9,9158% REAL. Medio travel60,848→62,812 s;
source60,758 s. Speed16,423→15,919 ft/s, source16,487. El error temporal30s normalizado
sube20,12%→26,28%. Internal section travel empeora37,741→39,189 s vs34,214 s real.
Estos tradeoffs se reportan, no se esconden tras un score agregado.

## Réplicas, verificación y preservación

Development210/211/212; final3000–3029 congeladas antes de revised rollouts.
30 revised +30 paired OLD controls; archivo anterior1000–1029 intacto. Una versión
intermedia release-only se conserva en archive_release_only; FIFO se decidió
por inversión física del orden, no porque mejorara un score. IC95 Student-t
de media cubre solo RNG de boundary speed, no discrepancy ni source uncertainty.

| metric | n | mean | SD | CI95_low | CI95_high |
| --- | --- | --- | --- | --- | --- |
| mean_speed_ft_s | 30 | 15.91908 | 0.07237 | 15.89206 | 15.94610 |
| mean_headway_ft | 30 | 53.21238 | 0.22871 | 53.12697 | 53.29778 |
| mean_travel_time_s | 30 | 62.81212 | 0.29794 | 62.70087 | 62.92337 |
| fraction_vehicles_stopped | 30 | 0.71253 | 0.00466 | 0.71079 | 0.71427 |
| duration_mean_s | 30 | 15.20113 | 0.11089 | 15.15972 | 15.24253 |
| duration_median_s | 30 | 13.76333 | 0.06687 | 13.73836 | 13.78830 |
| operational_stopped_fraction | 30 | 0.19836 | 0.00162 | 0.19775 | 0.19896 |
| exact_zero_fraction_literal | 30 | 0.00566 | 0.00003 | 0.00565 | 0.00567 |
| stop_duration_W1_s | 30 | 2.81413 | 0.04710 | 2.79654 | 2.83172 |
| throughput_temporal_normalized_error | 30 | 0.26277 | 0.00000 | 0.26277 | 0.26277 |

Todos los30 revised conservan21 inicial+253 entered=274 exited, sin pendientes,
sin negative speeds ni invalid overlap. OLD mode también reproduce las magnitudes
físicas originales a10 decimales. Todos los hashes originales y el scope/data
freeze coinciden. El runner guarda su reporte actual en peachtree3r y preserva
el reporte original PEACHTREE-3. El exportador legado de parámetros se bloquea
para impedir sobrescribir los resultados originales.

Tests: **108 total, 82 passed, 26 skipped,
0 failures/errors**. Los26 skips siguen siendo20 fixtures reales/mixtas bloqueadas
por B1 y 6 casos históricos I80 sin datos. Los métodos con registros sintéticos
sí se ejecutan. Las pruebas nuevas cubren classifier, episodes, conditioned metrics,
geometry, clock/crossing alignment, omitted leader categories, roles/interactions,
FIFO/safe insertion, release, discharge, queues, bins/empty occupancy, B1 guards,
no source replay y preservación/regresión del modo OLD.

## Streamlit y QA

OLD/REVISED seleccionables; params read only; revised engine recibe solo initial,
boundary arrivals y reglas congeladas. Canvas consume estados AgentPy, roles y
signal states; browser requestAnimationFrame interpola sin modificar dt. Plotly
muestra queue timelines, episodes, phase metrics y comparación pareada. No se
programó una cola artificial. Run/Pause/Reset, seed y speed visual pasan AppTest.
Canvas pasa un test JS conDOM/2D mocks. E1/E2/E3 siguen disabled y TEST LOCKED.

Estado obligatorio: **UI_IMPLEMENTED_NOT_BROWSER_VALIDATED**. Se verificaron
estructura/layout estático, tamaños de Canvas, IDs, JavaScript y controles.
No hubo navegador automatizado disponible; no se declara validación visual.
Las figuras científicas standalone permiten inspección sin afirmar browser QA.

## Respuestas finales

1. Stopped final:≤0,1 m/s, external operational convention, frozen before B1.
2. Literal exact zero y numerical-rest legacy se distinguen, no se renombra el pasado.
   Redondeo diagnóstico a la precisión reportada da9,916/7,739/8,202% REAL/OLD/REV;
   no es el clasificador operacional ni una regla física.
3. Episodios:334 REAL,219 OLD,232 revised de referencia; medianas11,6/12,6/13,85 s.
4. Stopping por fase y banda está exportado; el modelo respeta rojo, no reproduce
   suficiente detención GREEN/no-next-control.
5. Stop-lines auditadas y conservadas; no evidencia independiente de painted bars.
6. Schedules/offsets sin cambios; coverage UNKNOWN0 y cruces RED documentados.
7. Líderes omitidos:8,0147% seguimiento vial válido,8,8336% exact-zero following.
8. Background queue predecessors/proximidades se cuantificaron, sin llamar toda
   proximidad un conflicto ni inventar rutas de turning.
9. Safe insertion: FIFO elimina24 inversiones; referencia revisedmean0,835 s,
   P95 6,470 s,max 13,722 s,7/253 phase changes.
10. Release observed:37 primeras cabezas Through,median 1,6 s,IQR1,2–2,7 s; no cognitivo.
11. Queued discharge median REAL 2,826 vs OLD 3,147 vs revised3,143 s; no descarga
   demasiado rápida demostrada ni otro delay impuesto.
12. Queue por señal reporta mean/median/P90/max/duration, target y contexto completo.
13. Speed temporal10/30/60 s no mejora uniformemente; RMSE30s2,657→2,976 ft/s.
14. Throughput total274 todos, pero MAE30s1,6875→2,25 y event-time cumulative8→9.
15. Headway mejora de 54,526→53,212 ft enpaired means, real48,564 ft; queda sesgo.
16. Causa G: medición + receiving context no representado + release + fronteraFIFO.
17. Correcciones mínimas descritas arriba, sin free params ajustados por una métrica.
18. Background agents añadidos:0; roles soportados, incorporación no sustentadaHIGH.
19. 5 IDM conservados: v0=12,511825,T=2,356183,s0=2,086210,a=2,621727,b=2,625115;
   release1,6 s dataset-derived, threshold0,1 m/s measurement-only.
20. OLD/REVISED/REAL y controles pareados disponibles en old_vs_revised/paired CSVs.
21. 30 revised finales y susmean/SD/IC95 exportados; no mejorseed.
22. Tests 108/82/26,0 errores.
23. B1 LOCKED en esta fase; no speed/position/headway/travel/stopping/throughput B1.
24. Clasificación **B. BASELINE_NEEDS_REVISION**.
25. Siguiente paso: identificar receiving constraints de los cortes con B2/documentación
   o delimitar observabilidad sin modificar silenciosamente scope. No B1 ni E1/E2/E3.

Futuro nombre de validación: TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR
FEASIBILITY SUMMARY EXPOSURE. No se declara validación plenamente ciega.

Comandos: `python -m calibration.run_revision`, `python -m scripts.finish_peachtree3r`,
`python -m scripts.plot_peachtree3r`, `python -m scripts.run_train_tests`,
`python -m streamlit run streamlit_app.py`.
