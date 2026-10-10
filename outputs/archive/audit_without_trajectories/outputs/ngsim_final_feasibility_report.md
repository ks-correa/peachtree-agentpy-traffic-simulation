# Factibilidad NGSIM I-80 con los archivos locales

**C. NOT_VIABLE_FOR_AGENTPY con esta copia local. Decisión: DESCARTAR NGSIM en su estado disponible.** Esto no demuestra que el conjunto NGSIM I-80 completo sea inadecuado: demuestra que los archivos entregados no contienen las trayectorias necesarias para el proyecto propuesto.

No se implementó AgentPy, ABM, interfaz, escenarios ni reproducción de trayectorias. No se descargaron fuentes sustitutas ni se usó conocimiento externo para completar metadata.

## 1. Inventario y fuentes

Se inspeccionaron el ZIP exterior y todos sus ZIP internos sin extraer imágenes, videos o CAD. El inventario contiene 79 entradas, incluyendo carpetas y los contenedores ZIP; no son 79 datasets. La lista completa con tamaños y formatos está en `outputs/dataset_inventory.csv`.

| ZIP interno | Bytes sin comprimir en el ZIP exterior | Contenido relevante |
|---|---:|---|
| i-80-aerial-ortho-photos.zip | 219388619 | Dos TIFF, TFW, AUX y Thumbs.db |
| i-80-cad-diagram.zip | 2325117 | DWG, SHX, leyenda JPG |
| i-80-data-analysis.zip | 993031 | Tres informes PDF agregados |
| i-80-detector-data.zip | 9009868 | detector-data.csv y detector-data.txt |
| i-80-gis-files.zip | 104234 | SHP, SHX, DBF, MXD y plano JPG |
| i-80-signal-timing.zip | 113008 | Tres PDF de programación de señales |
| i-80-signs.zip | 937810 | Fotografías JPG de señales |
| i-80-weather-data.zip | 6077 | Dos HTML meteorológicos |

**No existe un archivo de trayectorias dentro de estos contenedores.** Los dos archivos tabulares son datos de detectores. Sus hashes difieren: no se presume que TXT y CSV sean duplicados equivalentes, y se procesa únicamente CSV, sin sumarlos.

`I-80 Metadata Documentation.pdf` no está en el proyecto. El único PDF externo es `data/1-_US_101_Metadata_Documentation.pdf`; su texto describe US-101, Los Ángeles, junio de 2005. No se transfiere su diccionario, carriles, unidades ni geometría a I-80. Los informes de I-80 tienen una codificación de fuentes que produce caracteres de control al extraer texto; se renderizó e inspeccionó la portada del primer informe, que confirma I-80 y 4:00–4:15 p.m. No se presentan sus tablas como resultados calculados desde trayectorias.

## 2. Estructura real

El CSV tiene **172800 observaciones de detector, 38 columnas, seis estaciones** (`1,3,4,5,6,7`) y 28800 timestamps globales distintos. No tiene `Vehicle_ID`, `Frame_ID`, `Total_Frames`, `Local_X`, `Local_Y`, `Global_X`, `Global_Y`, dimensiones/clase de vehículo, aceleración, `Lane_ID`, `Preceding`, `Following`, `Space_Headway` o `Time_Headway`.

Columnas reales: `Station_Id`, `Local_Time`, `Global_Time`; para cada carril numerado 1–5: `Vup_LaneN`, `Vdn_LaneN`, `Oup_LaneN`, `Odn_LaneN`, `Sp_LaneN`; y `MaxV_Lane1`–`MaxV_Lane5`, `AdjustedV_Lane1`–`AdjustedV_Lane5`.

Los nombres de columna sugieren mediciones agregadas por carril; sin el diccionario I-80 no se certifican unidades, significado de ceros, ocupación ni tratamiento de datos imputados. Una columna de velocidad de detector no equivale a velocidad individual. Los números 1–5 en nombres no identifican carriles de una trayectoria ni la rampa.

**Filas de trayectoria disponibles: 0. Vehículos únicos: no calculable**, no cero vehículos reales. Frames y clases: no disponibles.

Global_Time observado: `1112857200000` a `1114066770000`. Diferencias entre timestamps distintos: 30000 y 172830000 unidades numéricas. Sin metadata I-80 no se certifica aquí una conversión a fecha, zona horaria o frecuencia de trayectorias. El intervalo menor es compatible con 30 segundos si Global_Time usa milisegundos; esto es una interpretación condicionada, no la frecuencia vehicular de 0.1 s.

## 3. Periodos

Los nombres de los informes identifican exactamente:

1. `0400pm-0415pm` (16:00–16:15).
2. `0500pm-0515pm` (17:00–17:15).
3. `0515pm-0530pm` (17:15–17:30).

Son periodos de **informes agregados**, no tres archivos de trayectorias disponibles. Hay una separación de 45 minutos entre el final de P1 y el inicio de P2; P2 y P3 son contiguos. No se puede inferir independencia de vehículos a partir de los nombres. Los HTML meteorológicos no certifican la fecha de cada trayectoria ausente.

## 4. Calidad, trayectorias e interacciones (fases 4–9)

CSV de detectores: cero celdas vacías, cero filas de ancho incorrecto, cero claves repetidas `(Station_Id, Global_Time)` y cero tiempos no crecientes en el orden original por estación. Esto certifica sólo esas comprobaciones estructurales; no certifica exactitud física ni calidad vehicular. No se comprobó igualdad semántica con TXT ni duplicación exacta de filas independiente de la clave.

Todos los controles vehiculares solicitados quedan **NOT_EVALUABLE**, con valor nulo y causa explícita en JSON: duplicados vehículo/frame, continuidad, posiciones imposibles, velocidades negativas individuales, aceleraciones extremas, headways negativos, referencias inexistentes, carriles inesperados, saltos de carril/posición, errores de seguimiento, suavizado e identidad entre periodos. No se corrigió ningún dato.

No pueden reconstruirse entrada/salida, duración, posición/velocidad/carril inicial y final por vehículo. No pueden medirse líderes/seguidores válidos, reciprocidad, correlaciones, bins de aceleración frente a gap/velocidad relativa, decisiones de seguimiento ni distribuciones de headway individuales. **Cambios de carril e incorporaciones: no calculables**, no cero eventos. GIS/CAD y señales constituyen material geométrico auxiliar, pero no aportan por sí solos relaciones entre vehículos.

## 5. Congestión y comportamiento emergente (fases 10, 21)

No se demuestra aquí formación de congestión, colas, ondas de frenado o concentración de cambios de carril. Las velocidades agregadas podrían ayudar a describir evolución macroscópica tras documentar unidades, estaciones y ceros; no identifican cadenas de frenado entre agentes. No se fabrican gráficos de speed/headway/lane changes a partir de variables inexistentes. Los cuatro PNG solicitados quedan pendientes por ausencia de las observaciones relevantes; `outputs/figures/README.md` registra el motivo.

## 6. TRAIN/TEST (fases 11–13, 24)

**Ninguna estrategia puede ejecutarse con las fuentes actuales.** A (P1+P2 → P3), B (P1 → P2) y C (ventana expansiva P1 → P2, después P1+P2 → P3) se comparan como diseños condicionales en el CSV. Filas, vehículos, duración efectiva, condiciones y distribution shift son desconocidos. No se recomienda una partición operativa sin los datos.

Si se obtienen las trayectorias, A es un candidato inicial: P1/P2 para desarrollo y P3 como evaluación final, congelado antes de ajustar reglas o limpieza. B puede funcionar como evaluación intermedia en TRAIN; reutilizar P3 para elegir modelos destruiría su condición de TEST final. La ventana expansiva debe mantener un último holdout intacto. Se deben comprobar identidad física, continuidad en la frontera y alcance del identificador; IDs reiniciados por periodo pueden coincidir sin ser el mismo vehículo. Un namespace por archivo soluciona colisiones de claves, pero no demuestra ausencia de leakage. Vehículos que atraviesen una frontera deben asignarse completos a una sola partición o excluirse de ambas con una regla previa documentada. Nunca repartir filas aleatoriamente.

**PRE-MODEL TRANSFERABILITY CHECK: NOT_RUN_NO_TRAIN_TEST_TRAJECTORIES.** No hay medias, medianas, KS ni Wasserstein válidos para velocidad/aceleración/headway/clase/frecuencia de cambios individuales. No se inventaron umbrales. En una evaluación posterior KS/Wasserstein son descriptores para variables continuas; clases requieren proporciones/distancias categóricas, y dependencia temporal exige evitar interpretar millones de filas como muestras independientes. Este check tampoco sería validación final del ABM.

Los candidatos PRIMARY son velocidad media/distribución, Space_Headway, flujo, densidad, recorrido y throughput. SECONDARY: aceleración, Time_Headway, cambios de carril, colas y ondas. Las categorías son una propuesta futura; **ninguno tiene TEST vehicular disponible ahora**. Recorrido necesita trayectorias completas; flujo/throughput necesitan cruces de una sección fija; densidad necesita geometría y ocupación espacial; colas requieren una definición operacional previa. Las tablas agregadas pueden ser DESCRIPTIVE_ONLY para este diagnóstico, y no sustituyen observaciones reservadas individuales.

## 7. Agentes, entorno y parámetros (fases 14–17)

`VehicleAgent` es conceptualmente coherente, pero no identificable empíricamente con los archivos disponibles. No se pueden parametrizar sus dimensiones, clases, estado, posición, velocidad individual, líder o seguidor. FREE_FLOW, FOLLOWING, LANE_CHANGING y MERGING no se etiquetan sin evidencia. `HighwayEnvironment` tiene candidatos de fuente GIS/CAD/ortofotos, pero longitud, carriles, límites de rampa y alineamiento con coordenadas vehiculares no se certificaron. Resolverlos exige metadata I-80 y revisión geométrica; asumirlos ahora sería ASSUMPTION.

Desired speed, reaction time y safe gap no equivalen automáticamente a velocidad observada o headway. Requerirían CALIBRATED, con identificabilidad evaluada y supuestos explícitos; la velocidad deseada puede no observarse en tráfico restringido. Distribuciones de aceleración/frenado, clases, llegadas, flujo y tasas de cambios serían DATASET_DERIVED sólo después de disponer de fuentes compatibles. Intención de cambio, aceptación de gaps y reacción son decisiones latentes, no columnas observadas. Ningún valor numérico fue inventado. Las clasificaciones de `parameter_identifiability.csv` describen el método futuro, no parámetros ya estimados.

Una futura regla observar líder → acelerar/frenar → cambiar carril → actualizar posición sería ABM, si se estima desde TRAIN y genera dinámicas autónomas. Copiar `real_position[t]` sería replay y no resolvería la pregunta. Esta auditoría no implementa ninguno.

## 8. Escenarios y aporte (fases 18–20)

E1 puede conceptualmente cambiar tiempos/frecuencia de llegada por rampa; intervalo de metering sería EXPERIMENTAL y se medirían cola de rampa, throughput y recorrido. Necesita demanda de rampa, almacenamiento/cola fuera del área, regla de incorporación y baseline validado. E2 cambiaría objetivo/regla de velocidad; objetivo y cumplimiento serían EXPERIMENTAL; se medirían velocidad, variabilidad y recorrido. E3 combinaría ambos, midiendo también interacciones entre controles. No hay evidencia local suficiente para afirmar que puedan evaluarse correctamente en este proyecto.

Los PDF de señales existentes **no demuestran** observaciones de E1/E2/E3 ni efectos causales en trayectorias. Los escenarios son contrafactuales futuros; no deben confundirse con validación del baseline ni prometer validación real de intervenciones. Los rangos y respuesta de conductores requieren justificación adicional.

La formulación académica propuesta no se acepta todavía. Pregunta condicionada a obtener fuentes completas: **¿Cómo cambian velocidad, flujo, tiempos de recorrido y colas bajo control de incorporación, armonización de velocidad y su combinación en un modelo basado en agentes del corredor I-80, parametrizado con periodos históricos y validado en un periodo temporal reservado?** Hoy no puede ejecutarse con rigor.

## 9. Rendimiento, reproducción y pruebas (fases 22–23)

Ejecutar desde la raíz: `python scripts/evaluate_local.py`; pruebas: `python -m unittest discover -s tests -v`. El script usa biblioteca estándar, conserva fuentes, genera hashes SHA-256 e inventario determinista, y no muestrea trayectorias ni procesa videos. La lectura del ZIP de ortofotos usa un spool temporal en disco para evitar cargarlo en RAM. La dependencia PDF de la inspección fue pypdf/PyMuPDF; no es necesaria para repetir la auditoría tabular.

Tiempo y máximo working set del proceso se registran en `outputs/data_quality_audit.json`; no incluyen la lectura manual de PDF, instalación ni toda la sesión. Procesar detectores es cómodo, pero **no permite concluir rendimiento del dataset de trayectorias ausente**. Hay pruebas estructurales reales y pruebas vehiculares marcadas SKIP por fuentes ausentes, sin falsos pases.

Riesgos principales: falta de trayectorias/metadata correcta; confundir detectores con vehículos; usar diccionario US-101 para I-80; asumir independencia temporal/identidades; usar tablas agregadas para inferir decisiones; declarar congestión sin indicadores; atribuir intención al cambio de carril; geometría y fronteras desconocidas; error de seguimiento/suavizado/ruido no auditables. Incluso con datos completos se requeriría fijar preprocessing con TRAIN, separar métricas observacionales de parámetros latentes y evaluar distribution shift.

## 10. Decisión final (fase 25)

**C. NOT_VIABLE_FOR_AGENTPY — DESCARTAR NGSIM con los archivos locales actuales.** No se puede construir, calibrar y validar el ABM vehicular solicitado con una separación defendible TRAIN/TEST: faltan agentes observados e interacciones fundamentales. No se rechaza científicamente NGSIM I-80 completo. Para reabrir la decisión hacen falta archivos de trayectorias individuales por periodo y metadata específica de I-80; entonces debe repetirse el análisis antes de implementar el modelo. Se detiene el trabajo en factibilidad.

Resultados de ejecución: 172800 filas de detector; 0 filas de trayectoria; 1.156 segundos; 71.62 MB de working set máximo. Pruebas: 13 descubiertas, 7 aprobadas y 6 SKIP por ausencia de fuentes vehiculares.
