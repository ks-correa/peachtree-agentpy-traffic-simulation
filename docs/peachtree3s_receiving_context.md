# PEACHTREE-3S — contexto de recepción

El rótulo antiguo “post-control” confundía pasar un proxy con haber salido de una
intersección. B2 completo cambia la interpretación: **NB no tiene detenciones
TARGET después de la salida completa de12th y antes deY1400**. Los 4304 frames
stopped NB del bucket viejo están entreY1174–1192, en la aproximación/interior de
12th;4064 ocurren enRED deesa misma señal. No prueban una receiving queue externa.
La cifra anterior73,65% no debe interpretarse ahora como atribución causal de
receiving desconocido: incluía esta clasificación espacial incorrecta.

EnSB sí hay4948 stopped frames TARGET en la carretera después de salir de11th,
con onset hastaY514,535 y posiciones hasta514,676. El siguiente control es10th,
aprox 166,46 ft después del exit actualY400. Líderes detenidos sustentan seguimiento
en esa región. Más allá de1400NB, losonsets se concentran cerca de14th, no13th.

## Física observada por dirección

| direction | last_control_intersection | last_stopline_ft | current_exit | last_control_to_exit_ft | next_section | section_after_next_intersection | next_intersection | next_street | control_type | next_control_mouth_B2_ft | lane_count_before | lane_count_after | lane_labels_before | lane_labels_after | distance_ft | next_signal_intersection | evidence_source | confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 3 | 1168.91550 | 1400.00000 | 231.08450 | 4 | 5 | 4 | 13th | STOP_INTERSECTION_APPROACH_PRIORITY_UNASSIGNED | 1589.10400 | 2 | 2 | [1, 2] | [1, 2] | 189.10400 | 5 | B2 annotation transitions + official afternoon report Fig4,p11 and control description,p10; GIS camera polygons not lane geometry; DWG available not decoded | HIGH_PHYSICAL_LOCATION; CONTROL_DIRECTION_PRIORITY_PARTIAL |
| 4 | 2 | 777.26200 | 400.00000 | 377.26200 | 2 | 1 | 1 | 10th | SIGNAL_51 | 233.53750 | 2 | 2 | [1, 2] | [1, 2] | 166.46250 | 1 | B2 annotation transitions + official afternoon report Fig4,p11 and control description,p10; GIS camera polygons not lane geometry; DWG available not decoded | HIGH_LOCATION_AND_RECORDED_SIGNAL |

NB: última señal12th, proxy1168,9155, exit1400;231,0845 ft después del proxy.
SigueS4, luego13th/I4 conSTOP documentado a aprox1589,104 yS5 hasta14th/I5.
SB: última señal11th, proxy777,262, exit400;377,262 ft después del proxy.
SigueS2, luego10th/I1 semaforizada a aprox233,5375 yS1. Dos carriles normales
observados antes/después; lane11 esbahía, no tercer carril de capacidad probado.
No se identificó lane drop. Local_Y esproyección longitudinal, no arclength exacta.

Fuentes: metadata oficial Peachtree; informe oficial **0400pm–0415pm**, Fig4 p11
(página impresa6), descripción decontroles p10; B2 section/int/O-D/direction/movement,
posiciones globales y locales; TXT **0400-0415** de10thSB y14thNB. La figura oficial
se renderizó comoofficial_schematic.png. GIS existente tiene8 polígonos decámaras,
no topología de carriles. DWG disponible pero no decodificado: no se inventó una
lectura deentidades. Tube detectors sonagregados15min, no arrivals ni gap events.

## Stops, clusters y líderes

| direction | onset_region | episodes | vehicles | median_onset_y | median_duration_s |
| --- | --- | --- | --- | --- | --- |
| 2 | BEYOND_CURRENT_EXIT | 150 | 87 | 1894.04900 | 10.80000 |
| 2 | POST_CONTROL_REGION | 21 | 18 | 1181.70500 | 23.50000 |
| 4 | BEYOND_CURRENT_EXIT | 204 | 98 | 273.80850 | 16.10000 |
| 4 | POST_CONTROL_REGION | 26 | 17 | 489.47050 | 22.90000 |

| direction | center_ft | vehicles | episodes | associated_section | associated_intersection | known_control_nearby | classification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 1181.70500 | 18 | 21 | 3 | 0 | 3.00000 | PHYSICAL_CONTROL_MATCH |
| 2 | 1741.93100 | 2 | 3 | 5 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 2 | 1758.73550 | 1 | 2 | 5 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 2 | 1814.12100 | 4 | 9 | 5 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 2 | 1843.25600 | 9 | 31 | 5 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 2 | 1860.84300 | 8 | 11 | 5 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 2 | 1886.45800 | 12 | 19 | 5 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 2 | 1912.60050 | 14 | 14 | 5 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 2 | 1930.93700 | 13 | 15 | 5 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 2 | 1952.00350 | 16 | 18 | 5 | 0 | 5.00000 | PHYSICAL_CONTROL_MATCH |
| 2 | 1975.05700 | 14 | 24 | 0 | 5 | 5.00000 | PHYSICAL_CONTROL_MATCH |
| 2 | 2018.15200 | 1 | 1 | 0 | 5 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 2 | 2022.87800 | 1 | 3 | 0 | 5 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 773.81900 | 6 | 11 | 0 | 2 | 2.00000 | PHYSICAL_CONTROL_MATCH |
| 4 | 514.53500 | 1 | 1 | 2 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 489.47050 | 1 | 2 | 2 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 462.10500 | 1 | 1 | 2 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 441.23300 | 2 | 3 | 2 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 415.44700 | 5 | 7 | 2 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 385.69750 | 5 | 8 | 2 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 370.53450 | 9 | 12 | 2 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 340.01900 | 14 | 16 | 2 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 309.22600 | 16 | 31 | 2 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 285.88700 | 17 | 31 | 2 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 262.60800 | 22 | 39 | 2 | 0 | NA | UNKNOWN_RECEIVING_CONSTRAINT |
| 4 | 242.02100 | 25 | 61 | 2 | 0 | 1.00000 | PHYSICAL_CONTROL_MATCH |
| 4 | 224.10400 | 2 | 6 | 0 | 1 | 1.00000 | PHYSICAL_CONTROL_MATCH |
| 4 | 198.64300 | 1 | 1 | 0 | 1 | NA | UNKNOWN_RECEIVING_CONSTRAINT |

Bins10/25/50 ft verifican sensibilidad; losgrupos25ft son descriptivos yno descubren
intersecciones automáticamente. Hayposición deonset/release, censura, track end,
O-D, movimiento y time since last control. Censura no equivale aobservation artifact;
un stop conrelease observado es distinto de una terminación de seguimiento. No se
asume que todos losstops seancongestión. Loscambios depath después delscope original
limitan observabilidad longitudinal y se retienen como advertencia.

| direction | region | valid_following_frames | omitted_leader_share | stopped_frames | vehicles_stopped | stopped_with_valid_stopped_leader_fraction |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | CONTROLLED_REGION | 33185 | 0.11023 | 18757 | 87 | 0.55526 |
| 2 | POST_CONTROL_REGION | 4469 | 0.01320 | 4304 | 18 | 0.00000 |
| 2 | BEYOND_CURRENT_EXIT | 35595 | 0.11027 | 24670 | 87 | 0.57219 |
| 4 | CONTROLLED_REGION | 38029 | 0.07639 | 15287 | 114 | 0.40446 |
| 4 | POST_CONTROL_REGION | 16381 | 0.05158 | 6052 | 18 | 0.76454 |
| 4 | BEYOND_CURRENT_EXIT | 42522 | 0.05781 | 45338 | 98 | 0.61434 |

Enelbucket POST nominal, omitted leader share válidoNB1,32%,SB5,16%; dentro del
CONTROLLED actualNB11,02%,SB7,64%. No aumenta claramente downstream dentro del
scope actual. Más allá deexits:NB11,03%,SB5,78%. Enstopped POST nominal, NB0% tiene
leader válido detenido ySB76,45% sí. LoNB es compatible concontrol directo propio
yreferencias ambiguas enint/lane0, no prueba de ausencia deun líder físico.
Las categorías A/B/C/D/E sonexclusivas; referencias cross/local incoherentes para
CF seconsideran inutilizables, no un conflicto longitudinal inventado.
A significa pertenencia a la cohorte Through de11th/12th; fuera de ese alcance
el mismo target puede girar. No seinterpreta esa pertenencia como Through en10th/14th.

## Receiving ycontroles posteriores

| direction | intersection | street | mouth_B2_ft | control_type | observability | signal_schedule_available | unknown_clock_ticks | priority_identified | essential_gap_acceptance_identified | evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 1 | 10th | 233.53750 | SIGNAL | PARTIALLY_OBSERVED | True | 0.00000 | NA | NA | Official B2 report: intersection4 STOP; signalTXT for10thSB/14thNB. Fig4 does not assign arterial approach priority/conflicts. Schedules alone do not identify receiving supply. |
| 2 | 4 | 13th | 1589.10400 | STOP_INTERSECTION | KNOWN_BUT_UNPARAMETERIZED | False | NA | False | False | Official B2 report: intersection4 STOP; signalTXT for10thSB/14thNB. Fig4 does not assign arterial approach priority/conflicts. Schedules alone do not identify receiving supply. |
| 2 | 5 | 14th | 1975.08500 | SIGNAL | PARTIALLY_OBSERVED | True | 0.00000 | NA | NA | Official B2 report: intersection4 STOP; signalTXT for10thSB/14thNB. Fig4 does not assign arterial approach priority/conflicts. Schedules alone do not identify receiving supply. |

13th sí estágeométricamente aguas abajo del exitNB. **No escausa sustentada del
residual TARGET**: cero stopped TARGET NB enY1500–1678; no observación demuestre
que todos losarteriales deban parar. STOP deprioridad porapproach/gap acceptance
no está parametrizado. El siguiente14th y10th tienen schedules B2 conocidos,
pero schedules no cierran turning paths, permissive conflicts ni background demand.
No se puedeimplementar una extensión autónoma completaHIGH sin inventar reglas.

El chequeo adicional de fases de siguiente control, según movimiento futuro
observado solo paradiagnóstico, refuerza esa distinción: NBPOST tiene4174 stopped
frames mientras14th estáGREEN, aunque4064 deesos frames coinciden conRED propio
de12th. Más allá de1400,21286/24670 stopped frames NB coinciden conRED siguiente;
enSB fuera de400 son40493/45338. Hay228 frames NB deleft-phase sin estado conocido.
Esto es asociación condicionada, no prueba de una supply law ni replay. Detalles
en next_signal_conditioned_stops.csv. Thru schedules completos no significan que
todas laspermisiones/conflictos de turning estén completamente observados.

| direction | start_s | end_s | duration_s | upstream_stopped_mean | downstream_stopped_mean | downstream_occupancy_mean | definition | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 76.70000 | 77.00000 | 0.30000 | 1.00000 | 11.00000 | 15.00000 | GREEN last control + stopped targets upstream of exit + observed stopped class23 arterial downstream + no crossing during contiguous0.1 s ticks | OBSERVED_RECEIVING_BLOCK_CANDIDATE, not identified service capacity/priority law |
| 4 | 77.10000 | 82.10000 | 5.00000 | 1.92000 | 12.08000 | 15.82000 | GREEN last control + stopped targets upstream of exit + observed stopped class23 arterial downstream + no crossing during contiguous0.1 s ticks | OBSERVED_RECEIVING_BLOCK_CANDIDATE, not identified service capacity/priority law |
| 4 | 275.10000 | 276.60000 | 1.50000 | 1.00000 | 6.13333 | 15.00000 | GREEN last control + stopped targets upstream of exit + observed stopped class23 arterial downstream + no crossing during contiguous0.1 s ticks | OBSERVED_RECEIVING_BLOCK_CANDIDATE, not identified service capacity/priority law |
| 4 | 276.80000 | 276.90000 | 0.10000 | 1.00000 | 10.00000 | 15.00000 | GREEN last control + stopped targets upstream of exit + observed stopped class23 arterial downstream + no crossing during contiguous0.1 s ticks | OBSERVED_RECEIVING_BLOCK_CANDIDATE, not identified service capacity/priority law |
| 4 | 277.00000 | 277.20000 | 0.20000 | 1.00000 | 10.00000 | 16.00000 | GREEN last control + stopped targets upstream of exit + observed stopped class23 arterial downstream + no crossing during contiguous0.1 s ticks | OBSERVED_RECEIVING_BLOCK_CANDIDATE, not identified service capacity/priority law |
| 4 | 280.20000 | 282.20000 | 2.00000 | 1.00000 | 9.95000 | 16.00000 | GREEN last control + stopped targets upstream of exit + observed stopped class23 arterial downstream + no crossing during contiguous0.1 s ticks | OBSERVED_RECEIVING_BLOCK_CANDIDATE, not identified service capacity/priority law |

Los 6 candidatosSB deblocking suman9,1 s;mediana0,9 s,máximo5s. Exigen simultáneamente
targets stopped100ft upstream, class23 stopped200ft downstream, último control
GREEN yningún crossing en tickscontiguos0,1 s. Soncondiciones observadas necesarias,
no identificación de una supply law ni prueba de backward shockwave. Se exportan
occupancy, stopped counts, crossings5/10/30/60 s y flujo observado demand-conditioned.
No se introdujo capacity fija niservice slots copiados deexits reales.

| mechanism | evidence | counterevidence | parameters_identifiable | data_source | confidence | complexity | agent_based_interaction_required |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NEXT_SIGNAL | 10thSB/14thNB schedules and target stop clusters observed | NB has zero receiving stops inside current exit;10thSB future turning/context demand is not closed | Schedule yes; full receiving-agent system no | B2 full + afternoon report + signalTXT | MEDIUM | Multiple movements/context agents | True |
| STOP_CONTROL | 13th atNB1589.104,189.104 ft beyond current1400 | No targetNB operational stops in1500..1678; STOP sign/priority by approach not assigned | No essential arterial priority/gap law | Official report intersection4 STOP + B2 | LOW | Priority/conflict interactions | True |
| FINITE_RECEIVING_CAPACITY | Conditional stopped upstream/downstream and discharge gaps observed SB | Observed exits confound demand/control; cannot estimate supply by copying outflow | No capacity/service law identified | B2 current boundary flow and frame observations | MEDIUM | Needs independent supply or downstream model | True |
| QUEUE_SPILLBACK | SB stopped followers with stopped leaders near400 and10th | NB proxy-post stops are own12th, not13th spillback; no causal backward-wave identification | Footprint observable; external rule not identified | B2 leaders/speeds/positions | MEDIUM | Downstream controls plus exogenous context | True |
| LANE_DROP | Two normal lanes before/afternext intersections | No supported lane drop; bays distinct from normal lanes | No identified drop | B2 lane labels + official schematic | LOW | Unneeded topology | False |
| TURNING_INTERACTION | Target paths may turn after original exits; lane11/context seen | Proximity is not causal conflict or identifiable gap acceptance | Routes partly observed; complete conflict priorities no | B2 movement/O-D/lane | MEDIUM | Turning paths/conflicts | True |
| BACKGROUND_LEADER | SB post-region omitted references measurable | Omitted share does not materially rise inside current post region; NBvalid-stopped-leader0 | Arrivals/context not closed for full downstream system | B2 same-frame references | MEDIUM | Additional autonomous routes | True |
| BOUNDARY_OBSERVATION_ARTIFACT | Some stop episodes right-censored; rawspeed precision/jitter | Many complete stop/release episodes nearknown control, cannot call them tracking artifacts | Observation state, not new physics | B2 full track endpoints | MEDIUM | Measurement/censoring | False |
| OTHER_OWN_CONTROL_REGION_MISCLASSIFICATION | 4304NB proxy-post stopped frames allY1174..1192;4064RED12th; zero afterfullI3 to1400 | Annotation mouths are not surveyed bars; do not derive new paintedbar solely fromstops | Region classification identifiable; lane-specific physical stop reference still uncertain | B2 intersection labels + frozen I3proxy | HIGH | Correct interpretation/controlled-area audit | False |

HIGH: reclasificación de stops ligadosal propio12th, ubicación física documentada
de controles. MEDIUM: siguiente signal como sistema receptor completo, spillback,
finite capacity, turning/background, artifact deobservación. LOW: STOP13th como
causa delresidual ylane drop. Existencia HIGH de una señal no convierte sus
interacciones incompletas enun mecanismoHIGH implementable.
