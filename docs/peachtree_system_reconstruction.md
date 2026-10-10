# PEACHTREE-2: reconstrucción y contrato propuesto

**B. SYSTEM_RECONSTRUCTION_PARTIAL — AJUSTAR A SUBCORREDOR.** Se reconstruyen tiempo relativo, topología y control semafórico de las corrientes arteriales. Se recomienda un alcance reducido de trayectos pasantes entre dos cortes medidos alrededor de 11th/12th. No se aprueba calibración de todo Peachtree ni se declara cerrada la demanda de todas las calles laterales.

**Estado: DRAFT, NO TEST FREEZE, NO CALIBRATION, NO AGENTPY, NO SIGNAL OPTIMIZATION.** B2→B1 permanece como propuesta de evaluación retrospectiva entre adquisiciones, condicionada a aprobar el alcance poblacional y los efectos de interacciones externas. No es aprobación de un modelo ni garantía de que el baseline valide.

## Fuentes y evidencia

Se usa exclusivamente `data/peachtree_full.csv` como fuente vehicular. No se leyó otro dataset de trayectorias ni se modificó el CSV. SHA-256: `9769b819a1c0a010fa16cafa06a50bc7bc352f8e14303222f64a00c5e65b6702`. Inventario Peachtree en peachtree_source_inventory.csv, incluyendo metadata, cinco ZIP locales de apoyo, sus miembros, hashes y los adjuntos remotos no procesados.

`data-analysis-report-1245pm-0100pm.pdf` y `data-analysis-report-0400pm-0415pm.pdf`: p9 explica extensión del seguimiento; p10 documenta IDs/control; p11 Fig4 documenta topología y zonas; p12 Table1 identifica adquisiciones. Metadata Peachtree p7–9 documenta estados referidos a frames; p13–15 define variables. Hojas int51/int52/int53/int73 p1–2 documentan controladores.

GIS: camera-coverage tiene ocho polígonos de cobertura de cámara, no una red de carriles. CAD: Atlanta-Peachtree.dwg está disponible; no se simuló haber leído sus entidades sin un lector DWG. La topología se reconstruyó a partir del esquema oficial y los códigos observados. Las longitudes son aproximaciones de Local_Y, no levantamientos de bordillos/stop bars. Se inspeccionaron 30 TXT de tube data: fechas, columnas y pasos de 15 minutos; el encabezado dice Volume(veh/hr). No aportan timestamps de entradas individuales ni se desagregaron inventando arrivals.

## 1–3. Adquisiciones, identidad y reloj

B1 coincide exactamente con los 1115 vehículos del informe 12:45–13:00: 1092 autos y 23 pesados. B2 coincide con los 1222 de 16:00–16:15: una motocicleta, 1199 autos y 22 pesados. La cola de seguimiento hasta frames 10208/10329 concuerda con la extensión documental hasta 13:02:01/16:17:13. Esto fundamenta la asociación a archivos originales, sin decodificar o corregir Global_Time.

El reloj operativo es `t_relative = (frame_id - min_frame_of_acquisition) * 0.1`. B1: frame5→10208, 0→1020.3s; B2: frame2→10329, 0→1032.7s. Todas las trayectorias tienen frames consecutivas y 0.1s. La diferencia con la hora inicial nominal refleja los primeros frames disponibles y el origen definido; no se presenta t=0 como una hora civil exacta certificada. Global_Time queda intacto y fuera del reloj del modelo.

Identidad única: `(acquisition_id, vehicle_id)`; trayectoria_key serializada B1:ID/B2:ID. Todas las búsquedas de líder/seguidor añaden frame_id. Los 792 IDs numéricos compartidos nunca se unen como un mismo agente. La coincidencia de algunos atributos no identifica físicamente un vehículo entre horas; el contrato valida por adquisición, sin afirmar independencia cognitiva de todos los conductores.

## 4–5. Red lógica y códigos

Topología documentada: `S1 – I1/10th – S2 – I2/11th – S3 – I3/12th – S4 – I4/13th – S5 – I5/14th – S6`. I1/I2/I3/I5 corresponden a 51/52/53/73; I4 es un cruce con STOP, no un semáforo que deba inventarse. Eso no demuestra que todos los sentidos de Peachtree deban detenerse allí: prioridad/STOP por aproximación no se asignaron sin evidencia. La longitud del área se describe como unos 2100 pies. Los accesos adicionales impiden asumir sólo dos entradas extremas.

| section_id | south_intersection | north_intersection | observed_y_min_ft | observed_y_max_ft | observed_extent_length_ft |
|---|---|---|---|---|---|
| 1 | nan | 1 | 0 | 143.62 | 143.62 |
| 2 | 1 | 2 | 216.36 | 648.99 | 432.63 |
| 3 | 2 | 3 | 756.61 | 1185.6 | 429.03 |
| 4 | 3 | 4 | 1218.8 | 1587.7 | 368.88 |
| 5 | 4 | 5 | 1633.8 | 1994 | 360.21 |
| 6 | 5 | nan | 2067.1 | 2113 | 45.923 |

Movements: 1 through, 2 left, 3 right. Direction: 1 EB, 2 NB, 3 WB, 4 SB. Carriles numerados desde la mediana, 11=bahía izquierda ("bahía" sin interpretar el salto numérico como diez cambios); los códigos 0,4,1061,1131,1201,2081,9999 quedan sin asignación de carril normal confirmada en este alcance. Los códigos 1/2/3 tienen respaldo del esquema, aunque su disponibilidad cambia por sección/sentido. Diccionario documentado en peachtree_code_dictionary.csv, no basado sólo en frecuencias.

Origins/destinations se asocian al esquema: 101/201 extremo sur; 114/214 extremo norte; pares de calles laterales en 10th/11th/12th/13th/14th; accesos adicionales en S3/S4/S5. Se conserva la diferencia entre control IDs y int_id. La metadata resumida tiene inconsistencias de recuento de zonas; para topología se prioriza Fig4 del informe específico.

Las posiciones de boca de intersección se derivan de transiciones observadas section↔int, por sentido. Se publican mediana/P5/P95. Son límites de anotación y detectores de paso; no se etiquetan como líneas pintadas de STOP ni como dimensiones perfectas de un polígono de conflicto.

## 6–8. Señales y sincronización

Se analizaron 32 TXT originales (16 por adquisición), sus CSV equivalentes y cuatro hojas PDF. BG/BY/BR señalan inicios de verde/amarillo/rojo referidos a frame de trayectoria. Los archivos se asocian a adquisición mediante fingerprint documental; a intersección mediante el mapa de IDs; y a dirección por el nombre. Se construyeron intervalos de estado conservando UNKNOWN antes del primer evento; no se rellenaron fases iniciales, ceros dudosos o valores ausentes.

Cycle length, green/yellow/red y primera referencia de verde están en peachtree_signal_inventory.csv. El offset publicado es una referencia observable de fase, no un parámetro fijo de controlador descubierto. Hay actuación/variación y eventos posteriores al último frame de trayectoria; se utiliza sólo el tramo solapado y se documenta el resto. Para izquierdas sin fase Left explícita, Through no prueba permiso protegido; giro derecho en rojo tampoco se inventa.

Se revisaron visualmente las ocho páginas de hojas controller. La transcripción documentada de phase bank1 (min initial, max limit, yellow y red clear) y los nueve planes de coordinación está en peachtree_controller_pdf_parameters.csv. Las hojas se capturaron el 27/01/2006; muestran planes de 95/100s y referencias TOD/offset, pero no se presume que ese programa estuviera activo sin cambios el 08/11/2006. Un max-green de la hoja no se sustituyó por el verde observado del video.

| acquisition_id | intersection_id | direction | status | red_mean_speed_ft_s | green_mean_speed_ft_s | entries_green | entries_red |
|---|---|---|---|---|---|---|---|
| B1 | 1 | 2 | SIGNAL_SYNC_CONFIRMED | 0.90441 | 16.387 | 111 | 2 |
| B1 | 1 | 4 | SIGNAL_SYNC_CONFIRMED | 3.1055 | 21.49 | 88 | 7 |
| B1 | 2 | 2 | SIGNAL_SYNC_CONFIRMED | 2.6902 | 19.745 | 134 | 8 |
| B1 | 2 | 4 | SIGNAL_SYNC_CONFIRMED | 10.384 | 24.234 | 103 | 16 |
| B1 | 3 | 2 | SIGNAL_SYNC_CONFIRMED | 3.4947 | 23.086 | 122 | 6 |
| B1 | 3 | 4 | SIGNAL_SYNC_CONFIRMED | 12.996 | 30.924 | 112 | 10 |
| B1 | 5 | 2 | SIGNAL_SYNC_CONFIRMED | 2.9909 | 12.6 | 104 | 14 |
| B1 | 5 | 4 | SIGNAL_SYNC_UNRESOLVED | nan | nan | 0 | 0 |
| B2 | 1 | 2 | SIGNAL_SYNC_CONFIRMED | 3.3356 | 11.703 | 82 | 3 |
| B2 | 1 | 4 | SIGNAL_SYNC_CONFIRMED | 2.1424 | 9.419 | 91 | 21 |
| B2 | 2 | 2 | SIGNAL_SYNC_CONFIRMED | 7.1282 | 18.166 | 124 | 9 |
| B2 | 2 | 4 | SIGNAL_SYNC_CONFIRMED | 6.2112 | 12.195 | 148 | 17 |
| B2 | 3 | 2 | SIGNAL_SYNC_CONFIRMED | 4.9935 | 13.092 | 97 | 14 |
| B2 | 3 | 4 | SIGNAL_SYNC_CONFIRMED | 9.4949 | 18.138 | 155 | 6 |
| B2 | 5 | 2 | SIGNAL_SYNC_CONFIRMED | 3.6497 | 11.291 | 116 | 12 |
| B2 | 5 | 4 | SIGNAL_SYNC_UNRESOLVED | nan | nan | 0 | 0 |

Confirmación operacional: hay correspondencia documental directa y, en la misma referencia de frames sin optimizar escala/desfase, las velocidades medias son mayores en verde, las detenciones son más frecuentes en rojo y predominan cruces de boca durante verde. No se exigió perfección ni se ajustó un offset para aumentar concordancia. Los cruces de una boca anotada durante rojo no equivalen automáticamente a infracciones de una línea de parada situada antes.

I1/I2/I3 tienen confirmación para aproximaciones arteriales NB/SB en ambas adquisiciones. I5 queda PROBABLE en conjunto: NB aporta evidencia, pero no hay aproximación SB anterior identificable suficiente. Las ramas EB/WB tienen asociación documental, pero el seguimiento suele comenzar dentro del cruce y no valida su cola previa; se mantienen PROBABLE, no se extrapola confirmación arterial a todas sus fases. I4 es STOP_CONTROLLED, no SIGNAL_SYNC_UNRESOLVED por faltar un semáforo inexistente.

En el alcance de I2/I3, las cuatro series Through NB/SB ya tienen estado documentado desde t=50.5s en B1 y t=92.9s en B2. Antes de esos momentos hay fase incompleta y no se considera una evaluación con señal conocida.

## 9–11. Cobertura, observaciones cortas y travel time

De 2337 claves de adquisición, 1345 duran menos de 5s. Direcciones iniciales de esas observaciones: {1: 617, 3: 488, 4: 172, 2: 68}. Predominan viajes locales/transversales dentro del área visible. Todos los registros por clave coinciden con Total_Frames y no tienen gaps; esto respalda continuidad de transcripción, no evidencia de un viaje de extremo a extremo.

No hay evidencia de fragmentación temporal interna. Se buscaron posibles relevos entre el último registro de un ID y el primero de otro en 0.1–1s, con clase/dirección iguales, dimensiones compatibles y distancia dentro de un presupuesto nominal de posición/movimiento: 0 candidatos compatibles, ninguno confirmado ni unido. Son coincidencias posibles, no identificación física; no hay placa persistente para probar que nunca cambió un ID. La causa demostrable de buena parte de la mediana corta es alcance local, no la suposición de pérdida.

| acquisition_id | trajectory_class | vehicles | percentage |
|---|---|---|---|
| B1 | CORRIDOR_TRAVERSAL_FIXED_CUTS | 76 | 6.8161 |
| B1 | LOCAL_OBSERVATION_NOT_PROVEN_FRAGMENT | 742 | 66.547 |
| B1 | MULTI_SECTION_OBSERVED | 263 | 23.587 |
| B1 | SECTION_COMPLETE_OBSERVED_BOUNDARIES | 34 | 3.0493 |
| B2 | CORRIDOR_TRAVERSAL_FIXED_CUTS | 56 | 4.5827 |
| B2 | INTERSECTION_CROSSING_OBSERVED_BOUNDARIES | 1 | 0.081833 |
| B2 | LOCAL_OBSERVATION_NOT_PROVEN_FRAGMENT | 780 | 63.83 |
| B2 | MULTI_SECTION_OBSERVED | 306 | 25.041 |
| B2 | SECTION_COMPLETE_OBSERVED_BOUNDARIES | 79 | 6.4648 |

Categorías objetivas: MULTI_SECTION_OBSERVED exige dos secciones distintas; SECTION_COMPLETE requiere observar ambas transiciones limítrofes; INTERSECTION_CROSSING exige entrada y salida de int; CORRIDOR_TRAVERSAL_FIXED_CUTS exige dos cortes opuestos observados, no sólo O/D nominal. Los restantes son LOCAL_OBSERVATION_NOT_PROVEN_FRAGMENT; no se les llama pérdida ni viaje completo.

Travel time ya no es last-first del ID. Se prepararon: section_travel_time por cruces de anotación; intersection_traversal_time por entrada/salida observadas; route_travel_time entre los cortes fijos Local_Y=400 y 1400. Cada evento usa dos frames consecutivas y cruce frontal interpolado en ≤0.1s. Las fronteras de ruta están en el interior de S2/S4, no se confunden con entradas de la detección original. Longitud longitudinal definida: 1000 pies; distancia de ruta exacta por carril no se afirma.

Los candidatos de sección/intersección basados en códigos tienen fronteras dependientes de aproximación; para validación geométrica exacta habría que fijar detectores por carril antes del freeze. Duraciones de un ID que empieza/termina dentro de una zona siguen siendo residencia parcial y no traversal time.

## 12–15. Frontera recomendada y conservación

**Alcance recomendado: subcorredor arterial pasante de clases 2/3 entre Local_Y=400–1400 pies, con I2/11th e I3/12th.** Se representan corrientes NB/SB through con recorrido completo observado, no toda la población mixta que aparece en esa banda. La restricción es parte sustantiva de la pregunta y del contrato; no un filtro para mejorar el error de un modelo.

| acquisition_id | scope_vehicles | scope_rows | physical_entries_cohort | physical_exits_cohort | route_travel_time_median_s | cf_rows_kept | confirmed_lane_changes_in_scope |
|---|---|---|---|---|---|---|---|
| B1 | 251 | 124253 | 251 | 251 | 48.722 | 30489 | 37 |
| B2 | 276 | 169831 | 276 | 276 | 61.112 | 61733 | 21 |

Corredor completo y región mixta tienen entradas laterales, primeras detecciones internas, I4 STOP y cobertura limitada de aproximaciones. No se reemplazó una primera aparición por una entrada física. El archivo de comparación publica todas esas primeras/últimas apariciones y candidatos de cruce; no se certifica cierre de masa para la región mixta.

Entradas de la cohorte: cruce ascendente de Y400 en NB, descendente de Y1400 en SB. Salidas: Y1400 NB y Y400 SB. Cada medición exige dos muestras consecutivas y se marca cualquier discontinuidad cinemática; no se contabiliza un salto erróneo como entrada real. La cohorte seleccionada tiene pares completos de entrada/salida. Esa conservación retrospectiva de la cohorte no es conservación de todo Peachtree ni prueba de que no existan flujos laterales.

**Limitación de alcance:** los vehículos locales/que giran omitidos pueden influir sobre los pasantes reales. Por eso la validación se limita a una abstracción condicional y no permite atribuir efectos de red completa. Se excluyen respuestas a líderes fuera de la población elegida en la preparación CF; esto reduce la muestra y no elimina físicamente esa influencia del mundo real. Si se exige toda la corriente arterial, habrá que cerrar puertos de giros/detección y representar sus interacciones antes de calibrar. No se resuelve esa limitación introduciendo posiciones históricas como ghost agents.

Throughput es cruces de una frontera, agrupados en 30s y distinguiendo entrada/salida, no número de registros. El total de salidas de una cohorte completa está casi determinado por demanda; se propone comparar la distribución temporal de salidas, no presentar el total como una validación independiente poderosa.

## 16. Cola: candidatos sin threshold fijado

FHWA describe una cola como vehículos que esperan servicio y subraya que la cola puede avanzar; no establece un único umbral universal. Referencias primarias: [Signal Timing Manual, ch3](https://ops.fhwa.dot.gov/publications/fhwahop08024/chapter3.htm), [MOE field measurement](https://ops.fhwa.dot.gov/publications/fhwahop08054/sect3.htm) y [tool definitions](https://ops.fhwa.dot.gov/publications/fhwahop08054/sect4.htm). No se fijó un threshold final ni se utilizó B1 para ajustar uno.

Propuestas a revisar sólo con TRAIN potencial: (a) cadena contigua de líderes/seguidores exactamente detenidos en una aproximación; (b) cadena de avance muy lento con hysteresis de entrada/salida y separación coherente, usando sensibilidad de velocidades ya publicadas en PEACHTREE-1; (c) posición del último vehículo de una cadena conectada a la boca durante rojo. Longitud física requiere stop bar validado; hasta entonces se denomina queue proxy y se reporta la distancia a boca de anotación, no una cola pintada de precisión inexistente.

## 17–19. Preparación y calidad, sin calibración

Parquet separados por adquisición contienen ego_speed, leader_speed, relative_speed, gap libre, acceleration, lane, movement, section, signal_state y distance_to_intersection, además de clave canónica/frame/unidades. Distance usa la boca observada, no una stop bar supuesta. B2 es potencial TRAIN; B1 está disponible sólo en esta reconstrucción y no debe usarse para fitting después de un freeze aprobado. Los archivos/manifiestos tienen hashes.

Filtros propuestos antes de calibración: líder inexistente o fuera de población/banda; contexto distinto; gap≤0; discontinuidad espacial; saturación ±12.27; transición de carril ±1s; fase/carril/intersección ambiguos; discrepancia de headway con posición. Los límites cinemáticos usan nominalmente dos errores de posición de 2/4 pies documentados, sin afirmar que sean intervalos de confianza. Las reglas, razones, afectados y porcentajes se publican por adquisición y se solapan: no se deben sumar.

CONFIRMED_LANE_CHANGE es operacional: carriles normales adyacentes, misma sección/sentido, fuera de int/bahías, sin excursión A→B→A, ≥5 frames estables antes/después y desplazamiento lateral consistente >4 pies entre medianas de 10 frames, sin discontinuidad cinemática en ±1s. Es más estricto que PEACHTREE-1 y no equivale a revisión manual de video. Las transiciones crudas se conservan. Conteos globales: {"B1": 66, "B2": 46}.

## 20–23. Baseline y contrato propuesto

VehicleAgent mínimo para el alcance reducido: position, speed, acceleration, lane, through_route, leader y class. Reglas autónomas de ingreso por cortes medidos, seguimiento, respuesta a control semafórico, cambios normales de carril y salida. No se implementa personalidad, agresividad ni estados cognitivos. Los calendarios semafóricos son forzamiento externo del baseline; no constituyen replay de posiciones vehiculares.

**B2 TRAIN → B1 TEST sigue siendo una propuesta**, con clases 2/3, misma región y protocolo. No es prospectiva porque B2 es tarde y B1 mediodía; valida transferencia entre adquisiciones. Los 792 IDs compartidos se tratan como claves distintas. Fuente, geometría, población, filtros, señales y mediciones se deben aprobar antes de freeze. La selección de una cohorte completa usa cobertura retrospectiva: no se presenta como demanda total ni como predicción de qué vehículos conseguirán completar el viaje.

El contrato borrador separa input exógeno de output: entradas/clase/velocidad inicial y fases B1 pueden darse a un baseline condicionado, pero los tiempos de salida/velocidad interior/travel times reales de B1 sólo sirven para scoring. Si se da throughput de salida como suministro impuesto, no puede luego presentarse como output validado. Los vehículos simulados que no salgan no se descartan por no completar, y las fallas del baseline se deben contar.

## 24–26. Escenarios y pregunta

E1 green split, E2 coordinación/desfase entre I2/I3 y E3 combinación son técnicamente representables para el subcorredor pasante, porque esas señales existen y su referencia está sustentada. No se programaron ni optimizaron. Cambiar un verde debe conservar conflictos, mínimos peatonales, amarillos/all-red y servicio de movimientos competidores: las hojas controller y evidencia externa deberán definir rangos. No se infiere demanda de calles laterales no observada ni beneficio global.

El baseline se validaría con TEST real condicionado a entradas/fases; los escenarios serían contrafactuales. No se exige observar intervenciones reales, pero sí validar el baseline dentro del alcance autorizado y explicitar efectos externos omitidos. E1 mantiene referencia de coordinación y ciclo elegido; E2 cambia referencia de fase manteniendo splits/clearance; E3 modifica ambos. Documento detallado: peachtree_scenario_design_draft.md.

Pregunta orientadora ajustada: **¿Cómo afectan cambios de green split, desfase entre los semáforos de 11th y 12th y su combinación al tiempo de cruce entre cortes, velocidad y descarga temporal del tráfico arterial pasante, mediante un ABM parametrizado con B2 y evaluado con B1, para comparar estrategias bajo demanda y límites de operación explícitos?** No se anticipa una estrategia ganadora ni se generaliza a toda la red urbana.

## 27. Decisión, pruebas y próximos límites

**SYSTEM_RECONSTRUCTION_PARTIAL — AJUSTAR A SUBCORREDOR.** La parte temporal/topológica/semafórica de I2/I3 está sustentada y hay pares de entrada/salida, tiempos geométricos y datos CF preparados. La frontera de toda la población mixta no está cerrada, por lo que no se autoriza pasar directamente a calibrar el corredor completo.

Antes de la siguiente fase se necesita aprobar explícitamente si el proyecto acepta la abstracción de corrientes pasantes y sus interacciones omitidas, o exige añadir puertos/giros dentro de Peachtree. No se buscó otro dataset. Este resultado no constituye freeze y la recomendación B2→B1 no está aprobada automáticamente.

Reproducir: `python -m scripts.reconstruct_peachtree`; tests: `python -m unittest discover -s tests -v`. Se mantienen pruebas anteriores. Resultado de suite: peachtree_system_test_summary.json / peachtree_system_test_results.txt. El CSV fuente y los archivos de apoyo quedan íntegros; outputs se generan de forma determinista y no contienen ajustes de modelos.

Croquis agregado de coordenadas/cortes: outputs/figures/peachtree_reconstructed_scope.png. Es una vista del área arterial ±60 pies, no un mapa de bordillos; no se muestrearon trayectorias para construir sus conteos.

Tiempo de reconstrucción numérica: 17.499s; peak working set aproximado: 904.09MB. No incluye inspección manual de PDF ni red.
