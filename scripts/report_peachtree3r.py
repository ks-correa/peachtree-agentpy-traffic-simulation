"""Publish measured diagnosis and revision, preserving all original results."""
import json,hashlib,re
import numpy as np
import pandas as pd
from calibration.structural import OUT
from simulation.training_data import ROOT,require_train
from scripts.evaluate_local import digest

def table(d):
    # No optional tabulate dependency required.
    def value(x):
        if isinstance(x,(float,np.floating)):return '—' if not np.isfinite(x) else f'{x:.5f}'
        return str(x).replace('|','/').replace('\n',' ')
    return '| '+' | '.join(d.columns)+' |\n| '+' | '.join(['---']*len(d.columns))+' |\n'+'\n'.join('| '+' | '.join(value(x) for x in row)+' |' for row in d.itertuples(index=False,name=None))

def tidy(s):
    s=re.sub(r'\b(REAL|OLD|REVISED|TARGET|BG|Tests|Tests:|median|Mediana|mediana|mean|P95|max|con|sin|de|desde|entre|hay|Hay|operational|dt)(?=\d)',r'\1 ',s)
    s=re.sub(r'\b(\d+(?:[.,]\d+)?)(ft/s|ft|m/s²|m/s2|m/s|veh/bin|veh|s)\b',r'\1 \2',s)
    s=re.sub(r'\b(\d+)(vehicles|vehículos|iniciales|arrivals|frames|pares|seeds|casos|réplicas|fixtures|ticks|cabezas|TARGET|failures|errors|passed|skipped)\b',r'\1 \2',s)
    for old,new in [('19.5 IDM','19. 5 IDM'),('21.30 revised','21. 30 revised'),('conlas','con las'),('conB2','con B2'),('conlane','con lane'),('y12 ya','y 12 ya'),('en11th','en 11th'),('en12th','en 12th'),('por B1 y6','por B1 y 6'),('por tick0','por tick 0'),('enpeachtree3r','en peachtree3r'),('enold_vs','en old_vs'),('enarchive_release_only','en archive_release_only'),('sololectura','solo lectura'),('su mean','su mean')]:s=s.replace(old,new)
    return s

def main(acquisition='B2'):
    require_train(acquisition);docs=ROOT/'docs'
    freeze=json.loads((OUT/'revision_freeze.json').read_text());measure=json.loads((OUT/'measurement_freeze.json').read_text())
    decision=json.loads((OUT/'decision.json').read_text());tests=json.loads((OUT/'test_report.json').read_text())
    if tests['errors'] or tests['failures']:raise RuntimeError('Unresolved tests')
    comparison=pd.read_csv(OUT/'old_vs_revised.csv');summary=pd.read_csv(OUT/'revised_30_replica_summary.csv')
    paired=pd.read_csv(OUT/'paired_old_vs_revised.csv');rep=pd.read_csv(OUT/'revised_replicates.csv')
    if not rep.conservation_verified.all() or not rep.vehicles_exited.eq(274).all() or rep.vehicles_remaining.gt(0).any():raise RuntimeError('Conservation/incomplete rollouts')
    old_manifest=json.loads((OUT/'old_baseline_manifest.json').read_text());old_checks={p:digest(ROOT/p)==sha for p,sha in old_manifest['hashes'].items()}
    original_freeze=json.loads((ROOT/'outputs/baseline_scope_freeze.json').read_text());source_checks={p:digest(ROOT/p)==sha for p,sha in original_freeze['hashes'].items()}
    if not all(old_checks.values()) or not all(source_checks.values()):raise RuntimeError('Original/source integrity changed')
    real=pd.read_parquet(OUT/'real_observations.parquet');old=pd.read_parquet(OUT/'old_observations.parquet');rev=pd.read_parquet(OUT/'revised_observations.parquet')
    threshold=measure['stopped_speed_max_ft_s'];r_uncontrolled=((real.intersection==0)&(real.speed<=threshold)).mean();o_uncontrolled=((old.intersection==0)&(old.speed<=threshold)).mean()
    old_gap=(real.speed<=threshold).mean()-(old.speed<=threshold).mean();share=(r_uncontrolled-o_uncontrolled)/old_gap
    phases=pd.read_csv(OUT/'signal_conditioned_stopping.csv');phases['weighted']=phases.n*phases.operational_stopped_fraction
    phase=phases.groupby(['series','intersection','direction','phase']).agg(n=('n','sum'),weighted=('weighted','sum')).reset_index();phase['operational_stopped_fraction']=phase.weighted/phase.n;phase=phase.drop(columns='weighted')
    phase.to_csv(OUT/'signal_conditioned_summary.csv',index=False)
    episodes=pd.read_csv(OUT/'stop_episode_real_vs_sim.csv');lines=pd.read_csv(OUT/'stopline_audit.csv');alignment=pd.read_csv(OUT/'signal_alignment_audit.csv')
    leaders=pd.read_csv(OUT/'omitted_leader_audit.csv');strict=leaders[leaders.subset.eq('STRICT_ROAD_VALID_FOLLOWING')];omitted=1-strict[strict.category.eq('A_TARGET')].fraction.iloc[0]
    queue=pd.read_csv(OUT/'queue_real_vs_sim.csv');delay=pd.read_csv(OUT/'safe_insertion_summary.csv');release=pd.read_csv(OUT/'release_estimation_sample.csv');discharge=pd.read_csv(OUT/'queued_discharge_headway.csv')
    temporal=pd.read_csv(OUT/'temporal_speed_comparison.csv');flow=pd.read_csv(OUT/'temporal_throughput_comparison.csv');causes=pd.read_csv(OUT/'cause_ranking.csv')
    # High confidence identifies a residual LOCATION, not the exact off-domain mechanism.
    diagnosis=f'''# PEACHTREE-3R — diagnóstico estructural TRAIN-only

El diagnóstico es **G: combinación de semántica de medición, contexto de recepción
no representado, salida al verde e inserción de frontera**. No se asumió esta causa
antes de analizar B2. AgentPy, dt0,1s, el subcorredor y el snapshot se conservan.
Hay276 vehículos elegibles;274 participan en la ventana93,4–1032,7s porque dos
ya habían salido. Se analizan21 iniciales y253 arrivals.

## Medición de stopped

B2 reporta velocidad con precisión de0,01ft/s; mínimo positivo observado0,03ft/s,
con una masa exacta en0 y abundante velocidad positiva muy baja. No hay separación
natural clara entre creep y rest. No se eligió un umbral para minimizar el error.
Se congela **OPERATIONAL_STOPPED: v≤0,1m/s ({threshold:.8f}ft/s)** mediante la
[convención operacional de espera de SUMO](https://sumo.dlr.de/docs/Simulation/Output/TripInfo.html).
Se usa solo como definición de medición; no sustituye AgentPy ni su física.
**EXACT_ZERO_STOPPED: v==0** queda como métrica secundaria literal.
La antigua tolerancia numérica≤1e-6m/s NO era literal zero. Sus resultados
originales se preservan, pero no se renombra esa cifra como exact-zero.

{table(pd.read_csv(OUT/'stop_speed_semantics.csv')[['series','upper_ft_s','exact_zero_fraction','positive_to_upper_fraction','cumulative_fraction']])}

Un operador diagnóstico de observación, redondear a la precisión reportada0,01ft/s,
produce zero fractions9,9158% REAL,7,7386% OLD y8,2018% REVISED de referencia.
Así, buena parte del déficit aparente de exact-zero procede de comparar continuo
con discretizado. Este operador NO cambia la definición operacional congelada,
no modifica física y no se presenta como el filtro interno conocido de NGSIM.
Además, el audit de desplazamiento detecta jitter: entre0<reported v≤0,1ft/s,
20,36% de pasos REAL tienen Y constante y18,20% retroceso aparente; el simulator
no retrocede. No se inventa un modelo de measurement noise a partir de eso.

{table(pd.read_csv(OUT/'observation_precision_audit.csv')[['series','literal_zero_fraction','rounded_to_source_0_01_ft_s_zero_fraction','reported_precision_ft_s']])}

La comparación operacional no resuelve el fallo: REAL27,4785%, OLD18,7767%.
Tras la última línea controlada de cada sentido, el exposure operacional es
{r_uncontrolled*100:.4f}% de TODOS los frames REAL y{o_uncontrolled*100:.4f}% OLD.
Ese tramo explica{share*100:.2f}% de la discrepancia operacional OLD. Esto localiza
el problema; no identifica causalmente qué restricción externa, prioridad o
interacción produce cada stop. No se usaron salidas reales como calendario de
servicio, bloqueos falsos, posiciones históricas ni otros mecanismos de replay.

## Episodios y señalización

Un episodio es una secuencia máxima de ticks contiguos clasificados stopped.
Gaps de frame lo separan. Censura izquierda/derecha explícita; las duraciones
comparadas excluyen episodios truncados, pero se conserva su conteo. No se impone
una duración mínima elegida por ajuste. Onset/release registran fase y distancia.

{table(episodes[['series','vehicles_stopped','episodes','complete_episodes','duration_mean_s','duration_median_s','duration_P25_s','duration_P75_s','duration_max_s']])}

{table(phase[['series','intersection','direction','phase','n','operational_stopped_fraction']])}

El modelo RESPETA rojo y forma colas. Por ejemplo I2 NB OLD tiene61,20% operational
stopping en RED frente41,49% REAL. No es ausencia de respuesta al rojo. En cambio
hay detenciones reales importantes en GREEN y después de la última señal que no
se reproducen. Falta una distribución espacial/temporal correcta de las colas.
Cuando no hay observaciones de una fase, el indicador es no estimable, no cero.
Bandas físicas congeladas0–50,50–100,100–200,200+ft se exportan por separado.

## Stop-lines y sincronización

{table(lines[lines.series.eq('REAL_B2_ALL_OBSERVED_ARTERIAL')][['intersection','direction','OLD_STOPLINE','NEW_STOPLINE','distance_median_ft','distance_P25_ft','distance_P75_ft','distance_P95_ft']])}

Las referencias permanecen632,5395/777,262ft en11th y1168,9155/1240,7775ft en12th.
Medianas de cabezas en rojo a6,69–11,64ft de los proxies, contra6,84–6,86ft OLD.
Estas cabezas no son un levantamiento de painted stop bars. Las colas muy alejadas
y los gaps no justifican mover la geometría por ajuste. OLD_STOPLINE=NEW_STOPLINE.

{table(alignment[['intersection','direction','GREEN_crossings','RED_crossings','YELLOW_crossings','UNKNOWN_crossings','unknown_clock_ticks','OLD_OFFSET_s','NEW_OFFSET_s']])}

No se identificó con documentación una inversión de dirección/fase, pérdida de
cobertura ni offset corregible. Se conservan clocks, dirección y schedules.
Los cruces reales en rojo respecto a mouths aproximados quedan registrados;
no prueban por sí mismos un offset ni que la referencia sea una painted bar.
Las cuatro figuras superponen fases, stopped count y crossings en el mismo reloj.
Correlación RED/count es descriptiva, no optimización de timing.

## Líderes e interacciones omitidas

Referencia usable requiere presencia same-frame, dirección/lane/section coherentes,
leader longitudinalmente delante y bumper gap positivo. Se distingue versión
geométrica y versión STRICT_ROAD conlane1/2,int_id0; no se confunde con el CF limpio
para calibración. El{omitted*100:.3f}% del seguimiento STRICT_ROAD tiene líder fuera
del target;8,8336% de los frames exact-zero válidos y8,8091% operational stopped.
Se exportan denominadores y categorías A/B/C/D, incluida referencia no utilizable.

{table(leaders[leaders.subset.isin(['STRICT_ROAD_VALID_FOLLOWING','STRICT_ROAD_EXACT_ZERO_FOLLOWING','STRICT_ROAD_OPERATIONAL_FOLLOWING'])])}

{table(pd.read_csv(OUT/'omitted_interaction_summary.csv'))}

La omisión existe; proximidad lateral/turning NO equivale a conflicto causal.
La confianza de su contribución contrafactual al fallo global es MEDIUM, no HIGH.
No se añadieron background agents: no se sustentó una red completa de movimientos,
permisos y receiving constraints para ellos. Añadir turning agents arbitrarios
para producir colas sería una corrección sin evidencia. El rol TARGET/BACKGROUND
está soportado y probado sintéticamente; en los experimentos hay274 TARGET y0 BG.
Los primeros vehículos reales para geometría/release incluyen todo el contexto
arterial observado, y las colas físicas se exportan además de las target-only.

## Frontera, inicialización y salida al verde

{table(delay)}

La frontera OLD permitía overtaking de arrivals dentro del mismo carril:24 pares
de scheduled order invertido. Es un error de implementación verificable. FIFO
por dirección/lane elimina esas inversiones sin alterar la condición de gap,
deceleración segura o crear solapamiento. No se fuerza entrada a su hora prevista.
Scheduled y actual time, phase change y cola pendiente siguen registrados.

El snapshot original conserva21 vehículos, velocidad media2,4543ft/s y12 ya
operationally stopped. No es artificialmente fluido en t0. La evolución posterior
sí pierde restricciones no representadas; eso no autoriza mover el snapshot.
Posiciones, leaders, phase, clearance y transient0–10/10–60s están exportados.

Se estimó SIGNAL_RELEASE_DELAY desde37 primeras cabezas Through reales, normales,
dentro100ft antes del verde, con contexto completo observado para identificar
quién era realmente primero. Mediana1,6s,IQR1,2–2,7s. La muestra es heterogénea
entre aproximaciones y no demuestra un parámetro cognitivo universal. Se usa
UNA mediana pooled, DATASET_DERIVED, congelada antes de revised rollouts. El pooling
constante es una simplificación explícita. Hold=mediana−dt para contar el tick
físico hasta cruzar el threshold de movimiento. Solo se retiene la primera cabeza;
los followers responden por IDM. No se añade delay individual a toda la cola.

{table(discharge.groupby('series').headway_s.agg(['count','mean','median']).reset_index())}

Estos discharge intervals usan TARGET ya queued antes de green dentro100ft.
Se exporta también todo green crossing headway. No son garantía de saturación:
hay demanda discontinua y background omitido. OLD median3,147s vs REAL2,826s no
sustenta una descarga excesivamente rápida entre vehículos. No se añadió otro
parámetro de saturation headway.

## Queue, temporalidad y headway

Queue: cadena de operationally stopped desde la cabeza más próxima al control,
misma lane, adyacencia limitada por B2 standstill-gap P90. Métrica target-only y
contexto arterial completo se etiquetan explícitamente; excluir una cabeza BG
puede romper una cadena target-only. No se interpreta su máximo como toda la cola.

{table(queue)}

Bins10/30/60s se alinean por tick0,1s. Occupancy sin vehículos es0; velocidad y
stopped fraction sin observaciones son indefinidas. No se rellenan como velocidad0.
Se reporta número de bins comparables para no esconder ventanas vacías.

{table(temporal)}

{table(flow)}

El máximo acumulado en event times es8 vehículos OLD y9 REVISED; evaluar solo
edges de10s daría8 y7 y ocultaría ese empeoramiento. MAE30s1,6875→2,25 veh/bin;
timing bias0,739→2,404s en referencias prefijadas. Total274=274 no prueba fidelity.
Condicionales de headway por estado/fase/distancia se exportan; headway sin líder
es indefinido, no0. Primary headway compara CF REAL limpio con leaders simulados
en la misma sección vial. No son muestras individualmente emparejadas y la selección
de calidad puede influir. KS es distancia descriptiva, no inferencia iid de frames.

## Orden de causas y decisión previa al cambio

{table(causes)}

Los5 IDM permanecen fijos. Internal section travel OLD37,741s vs REAL34,214s ya
difiere, aunque el total coincide; esto sugiere compensación entre componentes,
no identificación de un error de parámetro aislado. No se recalibró T ni se
alteraron pesos para forzar stopped_fraction. La estructura de receiving sigue
sin identificarse; optimizar ahora podría ocultarla.

Clasificación final: **{decision['classification']}**. B1 LOCKED. E1/E2/E3 DISABLED.
'''
    (docs/'peachtree3r_structural_diagnosis.md').write_text(tidy(diagnosis),encoding='utf-8')
    selected=summary[summary.metric.isin(['mean_speed_ft_s','mean_headway_ft','mean_travel_time_s','operational_stopped_fraction','exact_zero_fraction_literal','fraction_vehicles_stopped','duration_mean_s','duration_median_s','stop_duration_W1_s','throughput_temporal_normalized_error'])]
    revision=f'''# PEACHTREE-3R — informe de revisión

**{decision['classification']}**. Se corrigieron mecanismos concretos y medibles;
el fallo residual impide abrir B1. No se reemplazó AgentPy ni se rehizo la red.

## Cambios mínimos implementados

1. Operational stopped≤0,1m/s compartido REAL/OLD/REVISED; exact zero literal aparte.
2. Episodios con continuidad/censura y contexto de señales/distancias.
3. SIGNAL_RELEASE_DELAY pooled1,6s desde37 cabezas B2; hold solo al primer vehículo.
4. FIFO en safe insertion: no overtaking same-lane, sin eliminar seguridad.
5. Bins físicos y NaN de speed en ventanas sin vehículos; conservación de occupancy0.
6. Instrumentación de roles, inputs de revisión separados, guards B1, UI de revisión.

Geometría, offsets, arrivals programados, snapshot, clases, dt e IDM no cambiaron.
No se añadieron BG porque la evidencia causal para esa corrección es MEDIUM y
su movimiento/conflicto/receiving no estaba identificado. No hubo replay ni
animación falsa. No se ejecutó optimizer ni selección por seed: la estructura
recibió cambios directos fundamentados, y conservar IDM permite aislar el efecto.
Se difiere recalibración hasta resolver el contexto de recepción; no se presenta
esa recalibración como completada.

## OLD / REVISED / REAL

Referencias prefijadas OLDseed10 y REVISEDseed210, no escogidas por fit:

{table(comparison)}

Controles pareados OLD/REVISED conlas mismas30 seeds3000–3029:

{table(paired)}

Hay mejora de headway y stopped incidence, pero no readiness global. En30 réplicas
operational stopping18,7141% OLD→19,8358% revised frente27,4785% REAL. Literal
exact zero revised0,5661% frente9,9158% REAL. Medio travel60,848→62,812s;
source60,758s. Speed16,423→15,919ft/s, source16,487. El error temporal30s normalizado
sube20,12%→26,28%. Internal section travel empeora37,741→39,189s vs34,214s real.
Estos tradeoffs se reportan, no se esconden tras un score agregado.

## Réplicas, verificación y preservación

Development210/211/212; final3000–3029 congeladas antes de revised rollouts.
30 revised +30 paired OLD controls; archivo anterior1000–1029 intacto. Una versión
intermedia release-only se conserva enarchive_release_only; FIFO se decidió
por inversión física del orden, no porque mejorara un score. IC95 Student-t
de media cubre solo RNG de boundary speed, no discrepancy ni source uncertainty.

{table(selected[['metric','n','mean','SD','CI95_low','CI95_high']])}

Todos los30 revised conservan21 inicial+253 entered=274 exited, sin pendientes,
sin negative speeds ni invalid overlap. OLD mode también reproduce las magnitudes
físicas originales a10 decimales. Todos los hashes originales y el scope/data
freeze coinciden. El runner guarda su reporte actual enpeachtree3r y preserva
el reporte original PEACHTREE-3. El exportador legado de parámetros se bloquea
para impedir sobrescribir los resultados originales.

Tests: **{tests['tests_total']} total, {tests['passed']} passed, {tests['skipped']} skipped,
0 failures/errors**. Los26 skips siguen siendo20 fixtures reales/mixtas bloqueadas
por B1 y6 casos históricos I80 sin datos. Los métodos con registros sintéticos
sí se ejecutan. Las pruebas nuevas cubren classifier, episodes, conditioned metrics,
geometry, clock/crossing alignment, omitted leader categories, roles/interactions,
FIFO/safe insertion, release, discharge, queues, bins/empty occupancy, B1 guards,
no source replay y preservación/regresión del modo OLD.

## Streamlit y QA

OLD/REVISED seleccionables; params read only; revised engine recibe solo initial,
boundary arrivals y reglas congeladas. Canvas consume estados AgentPy, roles y
signal states; browser requestAnimationFrame interpola sin modificar dt. Plotly
muestra queue timelines, episodes, phase metrics y comparación pareada. No se
programó una cola artificial. Run/Pause/Reset, seed y speed visual pasan AppTest.
Canvas pasa un test JS conDOM/2D mocks. E1/E2/E3 siguen disabled y TEST LOCKED.

Estado obligatorio: **UI_IMPLEMENTED_NOT_BROWSER_VALIDATED**. Se verificaron
estructura/layout estático, tamaños de Canvas, IDs, JavaScript y controles.
No hubo navegador automatizado disponible; no se declara validación visual.
Las figuras científicas standalone permiten inspección sin afirmar browser QA.

## Respuestas finales

1. Stopped final:≤0,1m/s, external operational convention, frozen before B1.
2. Literal exact zero y numerical-rest legacy se distinguen, no se renombra el pasado.
   Redondeo diagnóstico a la precisión reportada da9,916/7,739/8,202% REAL/OLD/REV;
   no es el clasificador operacional ni una regla física.
3. Episodios:334 REAL,219 OLD,232 revised de referencia; medianas11,6/12,6/13,85s.
4. Stopping por fase y banda está exportado; el modelo respeta rojo, no reproduce
   suficiente detención GREEN/no-next-control.
5. Stop-lines auditadas y conservadas; no evidencia independiente de painted bars.
6. Schedules/offsets sin cambios; coverage UNKNOWN0 y cruces RED documentados.
7. Líderes omitidos:8,0147% seguimiento vial válido,8,8336% exact-zero following.
8. Background queue predecessors/proximidades se cuantificaron, sin llamar toda
   proximidad un conflicto ni inventar rutas de turning.
9. Safe insertion: FIFO elimina24 inversiones; referencia revisedmean0,835s,
   P956,470s,max13,722s,7/253 phase changes.
10. Release observed:37 primeras cabezas Through,median1,6s,IQR1,2–2,7s; no cognitivo.
11. Queued discharge median REAL2,826 vs OLD3,147 vs revised3,143s; no descarga
   demasiado rápida demostrada ni otro delay impuesto.
12. Queue por señal reporta mean/median/P90/max/duration, target y contexto completo.
13. Speed temporal10/30/60s no mejora uniformemente; RMSE30s2,657→2,976ft/s.
14. Throughput total274 todos, pero MAE30s1,6875→2,25 y event-time cumulative8→9.
15. Headway mejora de54,526→53,212ft enpaired means, real48,564ft; queda sesgo.
16. Causa G: medición + receiving context no representado + release + fronteraFIFO.
17. Correcciones mínimas descritas arriba, sin free params ajustados por una métrica.
18. Background agents añadidos:0; roles soportados, incorporación no sustentadaHIGH.
19.5 IDM conservados: v0=12,511825,T=2,356183,s0=2,086210,a=2,621727,b=2,625115;
   release1,6s dataset-derived, threshold0,1m/s measurement-only.
20. OLD/REVISED/REAL y controles pareados disponibles enold_vs_revised/paired CSVs.
21.30 revised finales y susmean/SD/IC95 exportados; no mejorseed.
22. Tests{tests['tests_total']}/{tests['passed']}/{tests['skipped']},0 errores.
23. B1 LOCKED en esta fase; no speed/position/headway/travel/stopping/throughput B1.
24. Clasificación **B. BASELINE_NEEDS_REVISION**.
25. Siguiente paso: identificar receiving constraints de los cortes conB2/documentación
   o delimitar observabilidad sin modificar silenciosamente scope. No B1 ni E1/E2/E3.

Futuro nombre de validación: TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR
FEASIBILITY SUMMARY EXPOSURE. No se declara validación plenamente ciega.

Comandos: `python -m calibration.run_revision`, `python -m scripts.finish_peachtree3r`,
`python -m scripts.plot_peachtree3r`, `python -m scripts.run_train_tests`,
`python -m streamlit run streamlit_app.py`.
'''
    (docs/'peachtree3r_revision_report.md').write_text(tidy(revision),encoding='utf-8')
    required=['stop_speed_semantics.csv','stop_episode_real_vs_sim.csv','signal_conditioned_stopping.csv','stopline_audit.csv','signal_alignment_audit.csv','omitted_leader_audit.csv','omitted_interaction_summary.csv','safe_insertion_delay.csv','green_release_delay.csv','discharge_headway.csv','queue_real_vs_sim.csv','temporal_speed_comparison.csv','temporal_throughput_comparison.csv','conditional_headway.csv','cause_ranking.csv','revised_parameters.csv','revised_30_replica_summary.csv','old_vs_revised.csv']
    if not all((OUT/x).is_file() for x in required):raise RuntimeError('Missing artifact')
    manifest={'phase':'PEACHTREE-3R','B1_LOCKED':True,'required_artifacts_present':len(required),'original_outputs_preserved':all(old_checks.values()),'original_data_freeze_preserved':all(source_checks.values()),
        'ui_status':decision['ui_status'],'code_sha256':{str(p.relative_to(ROOT)):digest(p) for folder in ['simulation','calibration','ui'] for p in sorted((ROOT/folder).glob('*.py'))},
        'artifact_sha256':{str(p.relative_to(ROOT)):digest(p) for p in OUT.glob('*') if p.is_file() and p.name!='revision_manifest.json'}}
    (OUT/'revision_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'classification':decision['classification'],'tests':tests['tests_total'],'passed':tests['passed'],'skipped':tests['skipped'],'artifacts':len(required),'original_preserved':True,'B1':'LOCKED'},indent=2))
if __name__=='__main__':main()
