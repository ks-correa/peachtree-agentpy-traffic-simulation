# NGSIM Peachtree · AgentPy

Estado actual: **PEACHTREE-3R · B. BASELINE_NEEDS_REVISION**.
La revisión conserva PEACHTREE-3, añade medición operacional y SIGNAL_RELEASE_DELAY
B2, y corrige FIFO de inserción. B1 LOCKED. UI_IMPLEMENTED_NOT_BROWSER_VALIDATED.

Para repetir el experimento congelado actual:

```powershell
python -m calibration.run_revision
python -m scripts.finish_peachtree3r
python -m scripts.plot_peachtree3r
python -m scripts.run_train_tests --report outputs/peachtree3r/test_report.json
python -m streamlit run streamlit_app.py
```

Consulte [diagnóstico estructural](docs/peachtree3r_structural_diagnosis.md) y
[revisión](docs/peachtree3r_revision_report.md). No ejecute el calibrador legado
para esta revisión: sus exports originales están preservados. Los comandos
siguientes documentan PEACHTREE-3, no son el procedimiento actual de revisión.

PEACHTREE-3: baseline arterial Through, clases2/3, Local_Y400–1400ft,
11th–12th Street. TRAIN=B2. TEST=B1 LOCKED. Escenarios E1/E2/E3 deshabilitados.

## Ejecutar

```powershell
python -m pip install -r requirements-baseline.txt
python -m streamlit run streamlit_app.py
```

La interfaz consume resultados B2 ya generados. Run usa parámetros calibrados;
Pause/Reset y velocidad visual solo controlan reproducción. Cambiar seed ejecuta
AgentPy nuevamente. No hay ajustes manuales de parámetros.

## Reproducir TRAIN

```powershell
python -m scripts.prepare_baseline
python -m calibration.calibrate
python -m scripts.b2_diagnostics
python -m scripts.run_train_tests
```

El freeze original y su enmienda explícita se conservan. El proyecto requiere
los datos B2 y auxiliares locales previamente reconstruidos. No ejecute la suite
legada sin el runner TRAIN: fixtures históricas abrirían fuentes/métricas mixtas
incluyendo B1. El runner conserva todas las pruebas y omite esas fixtures antes
de setUpClass. Las pruebas de método con registros sintéticos sí se ejecutan.

Dependencias baseline usan pyarrow25.0.1, compatible con Streamlit1.65.0;
requirements-audit.txt conserva la especificación de la fase anterior. Para este
baseline use requirements-baseline.txt. AgentPy usa SALib1.4.7.

## Arquitectura

`simulation/`: agentes, red, señales, demanda, IDM, métricas y acceso TRAIN.
`calibration/`: estimación B2, objetivos explícitos y búsqueda con seeds fijas.
`ui/`: Streamlit, Plotly y Canvas requestAnimationFrame; sin física.
`tests/`: pruebas históricas, motor, aislamiento TRAIN, interfaz y Canvas.
`outputs/b2_*`: resultados TRAIN; `docs/`: metodología y verificación.

Consulte [verificación](docs/verification_report.md) y
[entrega PEACHTREE-3](docs/peachtree3_delivery.md). Esta fase no abre B1 ni habilita
experimentos. La siguiente decisión depende de corregir discrepancias TRAIN.
