# Reevaluación de factibilidad NGSIM I-80 con export.csv

**C. NOT_VIABLE_FOR_AGENTPY para las fuentes locales actuales.**

La decisión se recalculó tras leer todas las filas de export.csv. El archivo sí contiene registros con estructura de trayectorias, pero sus únicas ubicaciones son peachtree y us-101. No contiene I-80. El nuevo motivo es NO_I80_ROWS_IN_EXPORT, no la ausencia general de un archivo de trayectorias.

## Fuente, alcance y preservación

Archivo: `data/export.csv`, 137,010,173 bytes, SHA-256 `565945bc482de02ea6857b9f8aab7c87a319dfdc0d5e953d0e6a9b36ede09a40`. La procedencia oficial es declarada por el usuario; no se verificó una URL o checksum remoto. Se auditó el archivo local íntegro, sin muestreo ni modificación.

La auditoría anterior SIN trayectorias está conservada en `outputs/archive/audit_without_trajectories/`, con manifest.json y hashes. Los CSV/JSON antiguos permanecen en outputs como resultados históricos; los resultados vigentes usan el prefijo i80_.

El ZIP de apoyo ya inventariado no contiene trayectorias. Su integridad frente al hash anterior se comprobó. Falta I-80 Metadata Documentation.pdf. El PDF de US-101 no se utilizó para interpretar I-80. Su ausencia por sí sola no determinaría una clasificación negativa si hubiera trayectorias I-80.

## 1. Inspección completa del CSV

1,048,575 filas de datos; 25 columnas; separador `;`; 0 filas con ancho incorrecto. Los tipos son perfiles léxicos del CSV, sin coerción numérica destructiva.

| Location exacto | Filas | Vehicle_ID literales distintos | Frame_ID literales distintos | Global_Time literales distintos |
|---|---:|---:|---:|---:|
| peachtree | 873887 | 1545 | 10328 | 10442 |
| us-101 | 174688 | 2827 | 9568 | 1 |

IDs distintos no equivalen a vehículos físicos únicos si hay reinicios de IDs entre periodos. No se mezclaron ubicaciones ni se analizaron sus interacciones como sustituto de I-80.

| Columna exacta | Tipos léxicos y conteos | Faltantes (vacío/NA/N/A/NULL/NAN) |
|---|---|---:|
| Vehicle_ID | integer_literal: 1048575 | 0 |
| Frame_ID | integer_literal: 1048575 | 0 |
| Total_Frames | comma_grouped_candidate: 510392, integer_literal: 481939, text_or_other: 56244 | 0 |
| Global_Time | integer_literal: 873887, comma_decimal_scientific: 174688 | 0 |
| Local_X | dot_decimal_literal: 1047664, integer_literal: 911 | 0 |
| Local_Y | integer_literal: 393, dot_decimal_literal: 473775, comma_grouped_candidate: 574357, text_or_other: 50 | 0 |
| Global_X | multiple_dot_groups_ambiguous: 942629, dot_decimal_literal: 104900, integer_literal: 1046 | 0 |
| Global_Y | multiple_dot_groups_ambiguous: 944335, dot_decimal_literal: 102259, integer_literal: 1981 | 0 |
| v_length | integer_literal: 486152, dot_decimal_literal: 562423 | 0 |
| v_Width | dot_decimal_literal: 482349, integer_literal: 566226 | 0 |
| v_Class | integer_literal: 1048575 | 0 |
| v_Vel | dot_decimal_literal: 842785, integer_literal: 205790 | 0 |
| v_Acc | integer_literal: 521993, dot_decimal_literal: 526582 | 0 |
| Lane_ID | integer_literal: 1047434, comma_grouped_candidate: 1141 | 0 |
| O_Zone | integer_literal: 873887, missing: 174688 | 174688 |
| D_Zone | integer_literal: 873887, missing: 174688 | 174688 |
| Int_ID | integer_literal: 873887, missing: 174688 | 174688 |
| Section_ID | integer_literal: 873887, missing: 174688 | 174688 |
| Direction | integer_literal: 873887, missing: 174688 | 174688 |
| Movement | integer_literal: 873887, missing: 174688 | 174688 |
| Preceding | integer_literal: 834437, comma_grouped_candidate: 192056, text_or_other: 22082 | 0 |
| Following | integer_literal: 753132, comma_grouped_candidate: 266826, text_or_other: 28617 | 0 |
| Space_Headway | integer_literal: 513868, dot_decimal_literal: 526744, comma_grouped_candidate: 7951, text_or_other: 12 | 0 |
| Time_Headway | integer_literal: 514413, dot_decimal_literal: 449675, comma_grouped_candidate: 84482, text_or_other: 5 | 0 |
| Location | text_or_other: 1048575 | 0 |

Equivalencias por nombre presentes: `v_length` → Vehicle_Length; `v_Width` → Vehicle_Width; `v_Class` → Vehicle_Class; `v_Vel` → Velocity; `v_Acc` → Acceleration. Las demás variables solicitadas tienen su nombre esperado. Esto confirma esquema, no unidades o calidad.

### Tiempo y riesgos del formato

Se conservan tokens como `1,11885E+12`, `1,156`, `2,195.462` y `2.230.502.921`. Hay mezcla de notación científica con coma, agrupación con comas y múltiples puntos. No se eliminaron separadores ni se reconstruyeron dígitos perdidos.

El número de filas más cabecera es exactamente 1.048.576, y los formatos son compatibles con una transformación mediante hoja de cálculo. Es una señal de posible límite/truncamiento y transformación, no prueba de qué programa o proceso lo causó. No se certifica esta copia como exportación completa o fiel del recurso oficial.

**peachtree:** Frame_ID enteros literales entre 2 y 10329; Global_Time enteros literales entre 1163019100 y 1164063200; otros ejemplos: []. Tokens temporales más frecuentes: [['1163327500', 122], ['1163347600', 121], ['1163347700', 121], ['1163326900', 121], ['1163327000', 121]]. Diferencias más frecuentes entre valores enteros distintos: [[100, 10441]] (unidades crudas, no Hz).

**us-101:** Frame_ID enteros literales entre 433 y 10000; Global_Time enteros literales entre None y None; otros ejemplos: ['1,11885E+12']. Tokens temporales más frecuentes: [['1,11885E+12', 174688]]. Diferencias más frecuentes entre valores enteros distintos: [] (unidades crudas, no Hz).

No puede certificarse un rango calendario ni frecuencia vehicular física desde estos tiempos transformados. En particular, un timestamp constante o abreviado no permite reconstruir subsegundos; Frame_ID por sí solo tampoco certifica una tasa física. Ningún tiempo de otra ubicación se presenta como periodo I-80.

## 2–3. Filtro I-80 y periodos

Filtro reproducible: Location.strip().casefold() == "i-80". Los únicos valores reales son peachtree y us-101. Resultado: **0 filas y 0 identificadores I-80 en este archivo**. Se escribió `outputs/working/i80_trajectories_raw.csv` con cabecera y cero filas, junto con un manifiesto explícito de subconjunto vacío. No se identificó ningún valor que represente I-80.

No se detectaron periodos I-80. Los nombres 16:00–16:15, 17:00–17:15 y 17:15–17:30 del ZIP son referencias de informes históricos, no bloques observados en export.csv. No se asignaron cortes temporales ficticios.

## 4–9. Trayectorias, interacciones y dinámica I-80

Duplicados Vehicle_ID+Frame_ID, monotonicidad, gaps, posiciones, duraciones, aceleración, carriles, cambios de carril, reciprocidad y referencias leader/follower: NOT_EVALUABLE para I-80. Observaciones por vehículo y porcentaje de trayectorias con gaps son nulos, no cero. Las columnas Preceding/Following y headways existen globalmente, pero no hay población I-80 sobre la cual calcular porcentajes.

Interacciones utilizables: no calculable (denominador I-80 = 0), no 0 %. Correlaciones Pearson/Spearman, bins y distribuciones car-following no se ejecutaron. Cambios de carril: no calculables; no se afirma ausencia de eventos reales.

Incorporación: sin evidencia vehicular I-80; geometría e interpretación de rampa PENDING_I80_METADATA, adicionalmente bloqueadas por NO_I80_ROWS_IN_EXPORT. Los archivos CAD/GIS no bastan para inventar eventos.

Congestión: velocidad media/mediana/P10/P90, headways, vehículos activos, flujo, densidad, frenadas, colas y cambios de carril I-80 no calculables. No se asignan etiquetas free flow/transición/congestión.

## 10–11. TRAIN/TEST y transferibilidad

A: P1+P2 → P3; B: P1 → P2; C: bloques tempranos → bloque posterior. Ninguna puede materializarse: no hay periodos I-80. Los conteos de particiones y solapamiento son desconocidos/no aplicables, no resultados de una partición exitosa. No se efectuó random split ni se usó otro sitio como TRAIN o TEST.

A queda como candidato condicional si se obtienen los tres bloques completos. Antes de elegirlo, comprobar identidad física/IDs entre periodos y posibles trayectorias en la frontera, asignando cada trayectoria íntegra a una sola partición o excluyendo las que crucen fronteras según una regla previa. Prefijar IDs por periodo no demuestra independencia física. No puede recomendarse una estrategia efectiva hoy.

PRE-MODEL TRANSFERABILITY CHECK: NOT_RUN. Diferencias de media/mediana, KS y Wasserstein vacíos para speed, acceleration, space_headway, time_headway, vehicle_class y lane_change_frequency. Clase vehicular requeriría comparar proporciones categóricas; no corresponde tratar sus códigos como magnitudes continuas. No se fijaron umbrales de aceptación.

## 12–14. Parámetros, validación y escenarios

No se estimó ningún parámetro I-80. Con TRAIN adecuado, distribuciones de aceleración/frenado/headway, clases, llegadas en fronteras y tasas de cambios serían DATASET_DERIVED. Desired/free speed, respuesta a gap/velocidad relativa y aceptación de incorporaciones requerirían CALIBRATED, con identificabilidad explícita. Headway observado no equivale a tiempo de reacción; velocidad en congestión no equivale a velocidad deseada. Unidades, geometría o respuesta latente sin evidencia serían ASSUMPTION, no valores inventados.

Ningún indicador tiene TEST I-80 disponible. Candidatos PRIMARY futuros: velocidad/distribución, flujo por sección, headway, tiempo de recorrido entre fronteras y throughput. SECONDARY: aceleración, cambios de carril, densidad y congestión/cola. Se aceptarían sólo con medición equivalente en simulación y datos; recorrido requiere cobertura de ambas fronteras, densidad exige longitud/carriles y colas una definición operacional.

E1 modificaría ingreso por rampa; E2 reglas/objetivos de velocidad; E3 ambos. Sus parámetros serían EXPERIMENTAL y sus resultados contrafactuales sobre un baseline primero calibrado con TRAIN y validado con TEST. No se afirma validación directa de estas intervenciones con NGSIM histórico. Aquí son posibilidades conceptuales, no escenarios implementables con evidencia suficiente.

## Pruebas y reproducción

Ejecutar desde la raíz: `python -m scripts.audit_export`; pruebas: `python -m unittest discover -s tests -v`. El auditor usa biblioteca estándar, conserva tokens originales y hashes, recorre todas las filas y crea sólo resultados de factibilidad. Los tests verifican parser, clasificación de formatos, filtro de ubicación, exclusión de otros sitios, nulos en métricas bloqueadas, preservación histórica, integridad y resultados reproducibles. Las pruebas sobre interacciones/periodos reales I-80 permanecen pendientes por ausencia de esa población.

Resultados de la suite ejecutada: `outputs/i80_test_summary.json`; detalle: `outputs/i80_test_results.txt`. Las pruebas omitidas pertenecen a la auditoría histórica y no certifican interacciones I-80. La verificación independiente de ubicación vuelve a recorrer el CSV completo.

Rendimiento de esta ejecución: 14.587 s, 23.44 MB de peak working set del proceso; 1048575 filas inspeccionadas. No representa rendimiento del futuro ABM.

## 15. Decisión

**C. NOT_VIABLE_FOR_AGENTPY — DESCARTAR NGSIM con la copia local actual para el proyecto I-80.** Se reabrió la evaluación y se obtuvo evidencia nueva: export.csv contiene otros sitios y señales de transformación numérica. Esta conclusión no rechaza el conjunto oficial completo ni determina la viabilidad de un proyecto distinto con US-101/Peachtree.

Para reabrir la factibilidad I-80 hace falta una descarga que incluya explícitamente Location=i-80, sin límite de filas ni conversión por hoja de cálculo, preservando timestamps completos. La metadata I-80 sigue pendiente y debe documentar unidades/rampa. No se construyeron AgentPy, escenarios, modelos de seguimiento ni interfaz.
