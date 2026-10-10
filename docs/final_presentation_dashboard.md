# Dashboard final de presentación

PRESENTATION MODE abre por defecto; TECHNICAL MODE conserva la interfaz avanzada.

Inicio: `python -m streamlit run streamlit_app.py`.

Navegación: Proyecto, Datos, Modelo, Simulación, Calibración, Validación, Escenarios, Resultados, Comportamiento emergente, Decisión, Limitaciones, Material para presentación.

Los17 puntos de la guía están mapeados en presentation_assets/presentation_manifest.json. Cada bloque contiene mensaje, nota de exposición, fuente, PNG y CSV. El centro de exportación permite descargar imágenes1920×1080, tablas numéricas con source_artifact y ZIP completo. Datos de integrantes/docente/fecha quedan en campos configurables, sin información inventada.

El Canvas reproduce estados AgentPy oficiales guardados, con Run/Pause/Resume/Reset y playback0.5/1/2/5/10. No ejecuta nueva experimentación ni reproduce trayectorias reales NGSIM. Los indicadores oficiales provienen de las30 réplicas de cada configuración, separados de la animación ilustrativa seed7000.

QA:12 pruebas nuevas de presentación aprobadas, incluidas12 secciones sin AgentPy.run y reconciliación estadística. Se preserva el reporte científico222 casos,196 aprobados,26 omitidos, sin repetir física/calibración/validación. Chrome headless verifica navegación, dibujo real de Canvas y descarga ZIP; capturas en presentation_assets/screenshots/. Limitaciones y sesgos científicos permanecen visibles.

ALL 17 PRESENTATION REQUIREMENTS COVERED

VISUAL PRESENTATION DASHBOARD READY

Los freezes, métricas y archivos científicos permanecen byte-identical. No nuevos escenarios, parámetros o resultados oficiales.
