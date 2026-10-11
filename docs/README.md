# Documentación actual y evidencia histórica

## Uso actual

- [README principal](../README.md): instalación, estado científico, escenarios, datos locales y estructura.
- [Guía del dashboard](final_presentation_dashboard.md): controles, ventanas, interpretación y descargas.
- [Manifest académico](../presentation_assets/presentation_manifest.json): fuentes, figuras, tablas y notas de los 17 requisitos.

## Fuentes de verdad científicas

| Fase | Artefacto vigente | Informe |
|---|---|---|
| Estructura | [Freeze 3U](../outputs/peachtree3u/structural_model_freeze.json) | Artefactos 3U conservados. |
| Calibración | [Freeze 4](../outputs/peachtree4/calibration_freeze.json) | [Calibración final](peachtree4_final_calibration.md) |
| Validación | [Freeze 5](../outputs/peachtree5/validation_freeze.json) | [Validación B1](peachtree5_validation_report.md) |
| Escenarios | [Freeze 6](../outputs/peachtree6/experiment_freeze.json) | [Experimentación](peachtree6_scenario_experimentation.md) |
| Decisión | [Diseño congelado](../outputs/peachtree6/scenario_design_freeze.json) | [Decisión final](peachtree6_final_decision.md) |

La clasificación final es BASELINE_VALIDATED_WITH_LIMITATIONS y la experimentación está COMPLETED. E1 es la alternativa recomendada. B1 no se utilizó para ajustar parámetros ni rediseñar escenarios. La validación conserva la declaración:
TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.

## Verificación de interfaz

- [Reporte de Simulación](../presentation_assets/simulation_layout_report.json)
- [24 pruebas UI](../presentation_assets/simulation_test_report.json)
- [Ocho combinaciones en Chrome](../presentation_assets/simulation_browser_qa.json)
- [Auditoría de figuras](../presentation_assets/presentation_chart_audit.json)

El QA guardado de interfaz está aprobado. El reporte general de trabajo posterior [test_report.json](../outputs/peachtree6/test_report.json) registra 246 casos (212 aprobados, 26 omitidos, 2 fallos y 6 errores); no es evidencia de una suite completa aprobada. El reporte anterior de 222 casos sin fallos permanece en el historial Git.

Los documentos y outputs de PEACHTREE-3, 3R, 3S y otras fases previas son evidencia histórica. Sus estados LOCKED, NEEDS_REVISION o escenarios deshabilitados describen esas fases, no el dashboard actual. Sus comandos de calibración/experimentación no son instrucciones de arranque. No se reescriben informes históricos ni resultados científicos para cambiar retrospectivamente su estado.
