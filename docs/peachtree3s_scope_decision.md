# PEACHTREE-3S — decisión de scope

Decisión exacta: **B. FREEZE_REDUCED_SCOPE**.
Readiness: **B. NEEDS_ONE_MORE_STRUCTURAL_REVISION**.

No se extendió Peachtree ni se añadió física receiving especulativa. No hay un mecanismo
externo conconfianzaHIGH ytodos sus parámetros/interacciones esenciales identificados.
Sí existen cortes físicos defendibles anteriores aese contexto. La reducción es
direccional yconserva los ingress observados: no elimina lasaproximaciones necesarias.

| Sentido | Entrada conservada(ft) | Salida anterior(ft) | Salida congelada(ft) | Longitud ruta(ft) |
|---|---:|---:|---:|---:|
| NB |400|1400|1346.452|946.452|
| SB |1400|400|597.878|802.122|

No se expresa como un único intervalo común: NB400→1346,452 ySB1400→597,878.
Ambas rutas conservan11th/12th y su link. Se mantiene espacio después de la
intersección completa:100 ft NB,50 ft SB. NB no tiene stopped TARGET en ese buffer;
SB tampoco. Se contrastaron candidatos comunes25/50/100 ft y se conservaron entradas
originales para no truncar anticipación/frenado ni alterar arrivals porun cut nuevo.

Selección **ANTES deSIM fit**: mayor buffer predeclarado con separación física.
EnSB el receiving stopped vehicle BODY observado llega aY558,089. El candidato
100 ft dejaría exit547,878 e invadiría esa carrocería; se rechaza. Exit597,878 deja
39,789 ft frente astandstill-gapB2 P90+nominal4ft deallowance. Este último no es
garantía universal deseguridad ni deindependencia contrafactual. Fuente: B2 y
geometría, no elmenor error. Scenario relevance es11th/12th dentro deestas fronteras
condicionales; no beneficios full-network ni predicciones de10th/14th. Future queues
fuera delrégimen observado puedeninvalidar receiving libre ydeben declararse.

No se presenta el corte como libre deanticipación de otros vehículos en todo futuro. El chequeo adicional
de retained_buffer_external_leader_audit.csv encuentra16 frames deun targetSB
(1,6 s;0,664% delbuffer) siguiendo a un líder externo detenido, y0 enNB. Esa pequeña
exposición de borde estádocumentada; no seafirma independencia absoluta delreceiving.

| candidate | north_entry_ft | north_exit_ft | south_entry_ft | south_exit_ft | vehicles_observed | complete_route_vehicles | selected | physical_interpretability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FULL_CURRENT_SCOPE | NA | NA | NA | NA | 274 | 253 | False | Existing S2/S4 arbitrary mid-section cuts |
| EXTENDED_TO_NEXT_CONTROLS | NA | NA | NA | NA | 276 | 102 | False | Contains10th and13th; STOP priority/receiving supply unresolved |
| REDUCED_JUNCTION_ENVELOPE_PLUS_25FT | NA | NA | NA | NA | 274 | 259 | False | Observed full I2/I3 envelopes plus prespecified physical discharge buffer; no fit-based selection |
| REDUCED_JUNCTION_ENVELOPE_PLUS_50FT | NA | NA | NA | NA | 274 | 258 | False | Observed full I2/I3 envelopes plus prespecified physical discharge buffer; no fit-based selection |
| REDUCED_JUNCTION_ENVELOPE_PLUS_100FT | NA | NA | NA | NA | 274 | 254 | False | Observed full I2/I3 envelopes plus prespecified physical discharge buffer; no fit-based selection |
| REDUCED_DIRECTIONAL_DISCHARGE | 400.00000 | 1346.45200 | 1400.00000 | 597.87800 | 274 | 253 | True | Preserve observed ingress approaches; terminate afterfull junction bylargest physically separated candidate buffer per direction |

## Implementación y sameness de métricas

Modo separadoNEW_REDUCED_SCOPE, subclass deDiagnosticModel/ap.Model. Seheredan
VehicleAgent, IDM, signals, FIFO, release y dt. Solo se altera salida: natural
crossing detectado delpaso balístico, timestamp interpolado yEXITED. No posición
histórica, cambio develocidad ni teleport. Cinco IDM, threshold0,1m/s, stop-lines
y offsets permanecencongelados. Ningún agente adicional; TARGET sigueigual.

Source ySIM usan losmismos cortes por dirección ylas mismas métricasoperacionales.
274 targets enventana;253 viajes completos medidos desde entradas originales;
21 iniciales excluidos deTT completo. OLD/REVISED se evalúan en los mismos cortes,
aunque susagentes continúan fuera; NEW losretira físicamente allí. No se comparan
viajes de longitudes diferentes como si fueran iguales. Eventos EXITED tienen
ledger explícito: la últimamuestra deun agente antes del cut no basta para inferir
su salida. Una primera evaluación falló por usar crossing desde snapshots truncados;
se corrigió aledger deeventos y se repitió la evaluación, sin tuning.

90 corridas: OLD/REVISED/NEW con las mismas30 seeds3000–3029. No optimization,
no recalibration. Mean/SD/IC95 de media enpre_recalibration_metrics.csv cubren RNG,
no discrepancy ni source uncertainty. Reference210 prefijado, no best seed.

| metric | REAL_B2_same_boundaries | OLD | REVISED | NEW_REDUCED_SCOPE |
| --- | --- | --- | --- | --- |
| speed_mean_ft_s | 15.91886 | 15.06070 | 14.56923 | 14.75878 |
| speed_KS | 0.00000 | 0.09955 | 0.09421 | 0.09413 |
| speed_W1_ft_s | 0.00000 | 1.18163 | 1.54292 | 1.32845 |
| headway_mean_ft | 48.56370 | 57.43110 | 55.97475 | 53.25288 |
| headway_KS | 0.00000 | 0.10944 | 0.09673 | 0.09562 |
| headway_W1_ft | 0.00000 | 9.22392 | 8.06784 | 5.92359 |
| travel_mean_s | 54.16188 | 57.19205 | 59.15466 | 58.39269 |
| travel_W1_s | 0.00000 | 3.19719 | 4.99440 | 4.23490 |
| operational_stopped | 0.27354 | 0.19933 | 0.21086 | 0.21360 |
| stop_episodes | 319.00000 | 217.83333 | 233.60000 | 233.60000 |
| complete_stop_duration_mean_s | 12.59479 | 14.70806 | 15.20113 | 15.20114 |
| stop_duration_W1_s | 0.00000 | 2.55616 | 2.79047 | 2.79049 |
| queue_proxy_mean | 2.23126 | 2.98527 | 3.23224 | 3.23224 |
| queue_proxy_max | 13.00000 | 16.66667 | 17.06667 | 17.06667 |
| throughput_total | 274.00000 | 274.00000 | 274.00000 | 274.00000 |
| throughput_temporal_L1_normalized | 0.00000 | 0.23041 | 0.25742 | 0.25012 |
| section_travel_mean_s | 34.21369 | 37.76029 | 39.14195 | 38.98252 |

Enesas fronteras REALspeed15,9189 ft/s,TT54,1619 s,operational stop27,3543%.
NEWmean speed14,7588,TT58,3927,stop21,3595%; error/residuo persiste y se reporta.
Todos losmodos conservan274 exits,remaining0,pending0. Elgran receiving SB observado
se excluye físicamente, pero eldiagnósticoNB muestra una representación pendiente
del propio control: fuente B2 se detiene después del proxy dentro de12th.
La asociación decontrolled envelope/first queue head/stop reference debe auditarse
antes deajustar IDM. No se deduce una painted bar desde elmejor fit ni se mueve aquí.
Ésa es lacorrección concreta adicional deconfianza fuerte, no receiving aleatorio.

## Preservación, tests yUI

145 hashes pre-revisión coinciden; no sobrescritura dePEACHTREE-3/3R. Nueva fuente
y artefactos solo enpeachtree3s; mapas/metadata oficiales B2 separados. B1 permanece
inaccesible alectores ymodel selection. Incidencia: lectura inicial demarkdown legado
mixto mostró resúmenesB1 previamenteexpuestos; no seaccedió datasets/schedules B1 ni
seusó eso para decisiones. Se declara en vez deafirmar exposición absolutamente cero.

Tests: 122 total,96 passed,26 skipped.
Las fixtures anteriores de fuentes mixtas/B1 siguenomitidas antes de setUpClass;
los métodos sintéticos sí se ejecutan. Nuevos tests validan direcciones, clasificación,
bins, episodes, leaders,block detection,next control,B1 guard,scope consistency,
conservación/exit ledger,no replay,scenario relevance ypreservación/preprocessing.

UI originalOLD/REVISED conservada; no rediseño ni activación silenciosa delnuevo
scope. Trace técnico preparado; límites se activarán trasaprobar lafrontera y
resolver larepresentación del control. E1/E2/E3 disabled,TESTLOCKED.
UI_IMPLEMENTED_NOT_BROWSER_VALIDATED. No se afirma QA visual deunbrowser.

Siguiente paso: revisiónB2 del controlled envelope/lane-specific front reference
ycondicionamiento de la primera cabeza decola. Mantener boundaries seleccionados
congelados; no recalibrar todavía ni abrir B1. Nombre futuro devalidación:
TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.
