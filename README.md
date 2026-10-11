# NGSIM Peachtree · AgentPy

Simulación basada en agentes del tráfico Through entre 11th y 12th Street, en Peachtree Street, Atlanta. Utiliza datos NGSIM, AgentPy e IDM, con **dt físico = 0,1 s**.

**Estado actual:** estructura y calibración congeladas, baseline validado con limitaciones y experimentación BASE/E1/E2/E3 completada. **E1 es la alternativa recomendada dentro del alcance evaluado.** El dashboard y el material académico están preparados para la sustentación.

## Iniciar Streamlit

Desde la raíz del repositorio, con Python 3.11:

```bash
python -m pip install -r requirements-presentation.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8510
```

Abrir **http://127.0.0.1:8510**. La exportación PNG con Kaleido requiere Chrome instalado. Las pruebas de navegador incluidas utilizan Chrome en Windows.

- **PRESENTATION MODE:** abre por defecto; incluye 12 secciones y cubre los 17 puntos de la guía académica.
- **TECHNICAL MODE:** tema claro y la misma vista completa de Simulación, con detalles ampliables de ticks, IDs, referencias, límites y parámetros.
- Entrada técnica directa: `python -m streamlit run technical_streamlit_app.py`.

## Simulación

La sección reúne configuración, contexto/escenario, progreso temporal, demanda, Canvas claro, métricas en vivo, dinámica temporal, resultados oficiales, comportamiento emergente e interpretación.

| Contexto | Uso | Horizonte oficial | TARGET | Iniciales | Llegadas |
|---|---|---|---:|---:|---:|
| B1 | Validación | 969,3 s · 16:09.3 | 251 | 2 | 249 |
| B2 | Calibración / TRAIN | 939,3 s · 15:39.3 | 274 | 21 | 253 |

La **ventana visual predeterminada es de 180 s**. Al llegar a 03:00 termina la demostración. Para observar todo el horizonte, seleccionar **Completa** y pulsar **Iniciar**. También están disponibles ventanas de 60 y 120 s, Pausar, Continuar, Reiniciar y playback x0.5/x1/x2/x5/x10.

La UI reproduce **estados AgentPy oficiales guardados de la seed ilustrativa 7000**. Playback e interpolación visual no cambian dt ni ejecutan nuevos experimentos. Los snapshots tienen separación de 0,5 s; la fracción final de 0,3 s sin snapshot conserva el último estado guardado.

Las métricas de esta corrida están separadas de los **resultados oficiales de 30 réplicas**. Debajo del Canvas se muestran velocidad/detenciones, cola, salidas, comparación por escenario, resultados NB/SB y espacio–tiempo. Las gráficas ofrecen PNG 1920×1080 y CSV con `source_artifact`.

## Escenarios y decisión

| Escenario | Intervención |
|---|---|
| BASE | Condiciones semafóricas observadas de cada adquisición. |
| E1 | +10% nominal de verde Through, descontado del rojo; ciclo y amarillo conservados. |
| E2 | Coordinación para progresión SB, 12th → 11th: 19,87 s; desplazamiento del offset −21,33 s. |
| E3 | Combinación de E1 y el mismo desplazamiento E2. |

Se completaron **240 corridas oficiales**: 2 contextos × 4 configuraciones × 30 seeds. E1 mejora recorrido y detenciones en ambos contextos. E2/E3 mejoran B2, pero deterioran B1; su efecto depende del contexto.

La validación se denomina **TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE**. B1 estuvo autorizado para validación y evaluación de escenarios; sigue excluido de calibración, selección de parámetros y diseño de intervenciones.

Persisten sesgos de headway y episodios de detención, diferencias de distribución B1 y omisiones del alcance Through. La demanda cerrada no permite interpretar throughput total como capacidad. La recomendación no es un plan semafórico listo para aplicación en campo.

## Material de presentación

- [Paquete completo](presentation_assets/presentation_material.zip).
- [Presentación PowerPoint local](SBA_agentpy_trafico_urbano.pptx).
- [Manifest de los 17 puntos](presentation_assets/presentation_manifest.json).
- [Auditoría de gráficas](presentation_assets/presentation_chart_audit.json).
- [Reporte de Simulación](presentation_assets/simulation_layout_report.json).
- PNG y tablas: `presentation_assets/` y `presentation_assets/tables/`.
- Descargas verificadas desde Simulación: `presentation_assets/simulation_exports/`.
- [Guía actual del dashboard](docs/final_presentation_dashboard.md).
- [Índice de documentación y evidencias](docs/README.md).

## Verificación y conservación de resultados

Para comprobar la interfaz sin repetir física, calibración o experimentos:

```bash
python -m scripts.qa_simulation_layout
```

QA de interfaz guardado: **24/24 pruebas UI aprobadas**, **8 combinaciones B1/B2 × BASE/E1/E2/E3** comprobadas en Chrome y descargas PNG/CSV verificadas. La verificación de esa entrega conservó los hashes de 2.305 archivos científicos.

El reporte científico archivado en el historial Git tiene 222 casos: 196 aprobados, 26 omitidos, sin fallos. El archivo de trabajo actual [outputs/peachtree6/test_report.json](outputs/peachtree6/test_report.json) registra una ejecución posterior de **246 casos: 212 aprobados, 26 omitidos, 2 fallos y 6 errores**. Esa ejecución no equivale al QA específico de interfaz guardado; la suite completa no está aprobada en ese reporte.

No ejecutar fixtures históricas sin filtrar ni scripts de fases anteriores como procedimiento de inicio del dashboard. Conservar freezes, resultados e informes históricos.

## Archivos grandes y Git

Los originales `data/I-80-Emeryville-CA.zip`, `data/export.csv` y `data/peachtree_full.csv` se conservan localmente y están excluidos de Git. No se distribuyen en este repositorio ni en el ZIP de presentación. El dashboard utiliza artefactos procesados y resultados guardados; regenerar la investigación requiere los datos y su protocolo original.

## Organización

| Directorio | Contenido |
|---|---|
| `simulation/` | Motor AgentPy, agentes, señales, demanda, IDM y métricas. |
| `calibration/` | Estimación/calibración TRAIN y evaluación científica histórica. |
| `ui/` | Streamlit, Canvas, gráficas y lectura de resultados congelados. |
| `outputs/peachtree3u/` | Estructura final congelada. |
| `outputs/peachtree4/` | Calibración final congelada. |
| `outputs/peachtree5/` | Validación B1 y limitaciones. |
| `outputs/peachtree6/` | Escenarios, réplicas, trazas y decisión final. |
| `presentation_assets/` | Material académico, exportaciones y QA de interfaz. |
| `tests/`, `scripts/`, `docs/` | Verificación, utilidades y documentación. |
