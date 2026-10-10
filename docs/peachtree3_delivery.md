# PEACHTREE-3 — entrega en24 puntos

1. Arquitectura: simulation/, calibration/, ui/, tests/ separan datos, física,
   búsqueda, métricas e interfaz. AgentPy es el motor real.
2. VehicleAgent: ap.Agent conID sintético, clase, dimensiones, estado cinemático,
   ruta, líder/seguidor y tiempos de entrada/salida.
3. Estados: ENTERING, FREE_FLOW, FOLLOWING, STOPPED_SIGNAL, LANE_CHANGING, EXITED.
4. Entorno: Through clases2/3, Y400–1400ft, dos carriles por sentido,11th/12th;
   stop lines son proxies de mouths, lateral esquemático.
5. Señales: cuatro series B2 Through confirmadas I2/I3 NB/SB, sin modificar tiempos.
6. dt:0,1s por step AgentPy; reproducción visual independiente.
7. Arrivals:253 eventos exógenos B2; velocidades de frontera muestreadas por
   dirección con RNG semillado, inserción segura y retrasos registrados.
8. Inicialización:21 vehículos en frame936,93,4s. Primer snapshot sin overlap
   tras estar conocidas todas las señales; enmienda explícita, original conservado.
9. Car-following: IDM agrupado, integración balística y rojo como líder virtual;
   amarillo conservador ASSUMPTION; sin replay después de inicializar.
10. Parámetros CALIBRATED B2: v0=12.511825m/s; T=2.356183s;
    s0=2.086210m; a=2.621727m/s²; b=2.625115m/s². δ=4 literatura.
11. Calibración: estimaciones empíricas,16 LHC, Powell40 evaluaciones;57 candidatos
    ×seeds10/11/12. Objetivo normalizado explícito, sin ajustar posiciones.
12. TRAIN final:30 réplicas1000–1029 conmean/SD/IC95. Desarrollo, no validación.

| Indicator | Real B2 | Simulated mean (30 seeds) | SD | IC95 mean |
|---|---:|---:|---:|---|
| mean_speed_ft_s | 16.486892 | 16.439338 | 0.063178 | [16.415747, 16.462929] |
| mean_headway_ft | 48.563698 | 54.600038 | 0.207653 | [54.522499, 54.677576] |
| mean_travel_time_s | 60.758256 | 60.786095 | 0.244366 | [60.694847, 60.877343] |
| stopped_fraction | 0.099158 | 0.012859 | 0.000427 | [0.012700, 0.013019] |
| vehicles_exited | 274.000000 | 274.000000 | 0.000000 | [274.000000, 274.000000] |

13. Speed: referencia seed10 real 16.487 vs sim 16.433ft/s;
    KS=0.0985; W1=1.0751ft/s.
14. Headway: real 48.564 vs sim 54.576ft;
    KS=0.1073; W1=6.7631ft. Muestra observada limpia, sin
    correspondencia individual ni garantía de idéntica selección.
15. Travel cut-to-cut: 60.758 vs 60.810s;
    W1=3.239s. Sección interna:34,214 vs37,741s, diagnóstico aparte.
16. Throughput:274 salidas reales/simuladas; errores temporales persisten.
    Series acumuladas por frontera y bins30s disponibles.
17. Detenidos: real9,916% vs referencia1,317%; fallo principal de compatibilidad.
18. Verificación: nooverlap, nonegative speed, rojo/verde, salidas, conservación,
    reproducibilidad, orden de agentes, dt/unidades y barreras TRAIN comprobados.
19. Emergencia: máximos35 activos,8 detenidos, cola5; series de frenado/señal/velocidad
    colectiva. No atribuir causalidad de ondas por una animación.
20. UI: Streamlit oscuro, Canvas conrequestAnimationFrame, Plotly, tarjetas en
    reproducción, Run/Pause/Reset, seed y parámetros de sololectura; E1/E2/E3 disabled.
    AppTest/JS pasan; QA visual real pendiente por navegador no disponible.
21. Pruebas:87 totales;61 pasan;26 seomiten (20 lockB1+6 heredadas I80);0 errores.
    Se conservan las50 pruebas previamente aprobadas.
22. B1=LOCKED para calibración, selección y UI. Incidencia de lectura accidental
    de cabecera de filtros legados revelada enverification_report.md; no uso enfit.
23. Clasificación: **B. BASELINE_NEEDS_REVISION** por detención/headway/residuos.
24. Recomendación: corregir modelo de observación/dwell y auditar residuos soloB2;
    reevaluar readiness antes de la fase holdout. No B1 ni escenarios enesta fase.

Inicio: `python -m streamlit run streamlit_app.py`.
Tests: `python -m scripts.run_train_tests`.
