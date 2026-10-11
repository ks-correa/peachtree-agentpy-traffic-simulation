# Guía del dashboard actual

La fase científica está cerrada: estructura y parámetros congelados, validación con limitaciones y evaluación BASE/E1/E2/E3 completada. La recomendación dentro del alcance es E1. La UI lee resultados y estados guardados.

## Inicio

```bash
python -m pip install -r requirements-presentation.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8510
```

Abrir http://127.0.0.1:8510. PRESENTATION MODE es predeterminado. TECHNICAL MODE también utiliza tema claro y la misma estructura de Simulación.

## Navegación

Proyecto, Datos, Modelo, Simulación, Calibración, Validación, Escenarios, Resultados, Comportamiento emergente, Decisión, Limitaciones y Material para presentación. Participantes, docente y fecha son configurables; no se inventan datos personales.

## Demostrar la simulación

1. Abrir **Simulación** y seleccionar B1/B2 y BASE/E1/E2/E3.
2. Elegir ventana visual: 60, 120, 180 s o Completa. La seed ilustrativa es 7000.
3. Pulsar Iniciar. Pausar/Continuar conservan el avance; Reiniciar vuelve a cero.
4. Usar playback x0.5/x1/x2/x5/x10 según el tiempo disponible para exponer.
5. Observar progreso, demanda, ocho indicadores en vivo y Canvas.
6. Desplazarse hacia abajo para mostrar las gráficas de la corrida, luego resultados oficiales de 30 réplicas y comportamiento emergente.

**Por qué se detiene:** la ventana predeterminada termina a los 180 s (03:00) simulados. Es el final de la demostración. Seleccionar **Completa** permite cubrir 969,3 s (16:09.3) en B1 o 939,3 s (15:39.3) en B2.

El avance temporal es independiente del porcentaje de vehículos ingresados. Las salidas son un resultado del modelo, no una meta fija de finalización. B1 tiene 251 TARGET (2 iniciales + 249 llegadas); B2 tiene 274 (21 + 253).

El Canvas es claro, interpola posiciones mediante requestAnimationFrame y conserva dimensiones físicas. Mostrar referencias técnicas revela controles/cuts; el modo técnico amplía IDs, ticks y parámetros. Playback no cambia dt = 0,1 s ni ejecuta nuevos pasos AgentPy. Los snapshots tienen separación de 0,5 s; el tramo final sin snapshot conserva visualmente el último estado guardado.

## Qué representan las gráficas

- **Corrida actual:** velocidad/fracción detenida en paneles separados, cola, salidas y espacio–tiempo de la seed ilustrativa. Las series muestran toda la ventana visual, no se limitan al reloj reproducido.
- **Resultados oficiales:** medias de 30 réplicas por escenario, IC95, recorrido, fracción detenida, desempeño NB/SB e hitos t50/t90/tFinal.
- **Emergencia:** espacio–tiempo y cards oficiales de cola media, máxima, múltiples detenciones y máximo de activos, comparados con BASE.

Las figuras tienen títulos/unidades en español, valores esenciales sin hover, codificación consistente y fuente discreta. Las rutas completas están en metadata/manifest; las exportaciones no tienen toolbar.

## Descargar material

Cada gráfica de Simulación ofrece **Descargar PNG** y **Descargar CSV**. Los PNG se generan a 1920×1080. El CSV incluye `source_artifact`. Material para presentación ofrece el paquete completo y los 17 bloques de la guía, con mensaje, fuentes, figuras, tablas y notas.

- [ZIP](../presentation_assets/presentation_material.zip)
- [Manifest](../presentation_assets/presentation_manifest.json)
- [Auditoría de gráficas](../presentation_assets/presentation_chart_audit.json)
- [Reporte y QA de Simulación](../presentation_assets/simulation_layout_report.json)

## Evidencia de calidad y límites

El QA de interfaz guardado registra 24 pruebas aprobadas y 8 combinaciones contexto/escenario verificadas en Chrome, incluyendo señales/estados, playback y descargas. El reporte general de trabajo posterior registra 246 casos, con 2 fallos y 6 errores; no debe confundirse con ese QA de interfaz. Los resultados y freezes científicos siguen intactos. Permanecen visibles los sesgos de headway y detenciones, diferencias de distribución B1 y restricciones de demanda cerrada.

ALL 17 PRESENTATION REQUIREMENTS COVERED

SIMULATION SECTION PRESENTATION READY

CURRENT RUN AND OFFICIAL RESULTS CLEARLY SEPARATED

SCIENTIFIC RESULTS UNCHANGED
