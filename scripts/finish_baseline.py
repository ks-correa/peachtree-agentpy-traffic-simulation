"""Write a reviewable TRAIN-only decision, verification report and delivery."""
import json,hashlib
import pandas as pd
from simulation.training_data import ROOT
from scripts.evaluate_local import digest

def main():
    out=ROOT/'outputs';docs=ROOT/'docs'
    freeze=json.loads((out/'baseline_scope_freeze.json').read_text(encoding='utf-8'))
    checks={p:digest(ROOT/p)==sha for p,sha in freeze['hashes'].items()}
    if not all(checks.values()):raise RuntimeError('Frozen source/input/criteria integrity changed')
    tests=json.loads((out/'b2_test_report.json').read_text(encoding='utf-8'))
    if tests['failures'] or tests['errors']:raise RuntimeError('Verification has unresolved failures')
    params=json.loads((out/'b2_calibrated_parameters.json').read_text(encoding='utf-8'))
    summary=pd.read_csv(out/'b2_calibration_summary.csv').set_index('metric')
    compare=pd.read_csv(out/'b2_real_vs_simulated.csv').set_index('indicator')
    diagnostic=json.loads((out/'b2_emergent_diagnostics.json').read_text(encoding='utf-8'))
    runs=pd.read_csv(out/'b2_calibration_runs.csv')
    reason='Engine and conservation pass, but TRAIN stopping is strongly underestimated, mean headway is inflated and temporal throughput/section travel residuals remain. Continuous IDM rest vs source exact-zero measurement, omitted local interactions and simplified lane changes require TRAIN-only revision before B1.'
    decision={'classification':'B. BASELINE_NEEDS_REVISION','reason':reason,'training_acquisition':'B2','final_replicates':30,
        'B1_LOCKED':True,'next_phase':'Revise stopping/observation model and TRAIN residuals; retain B1 lock. Then reconsider readiness.','E1_E2_E3':'DISABLED',
        'ui_checks':'Streamlit AppTest controls/render/pass; Canvas JS mock test pass. Real browser screenshot/playback QA unavailable: browser inventory empty.',
        'methodological_incident':'One accidental shell header read of legacy mixed quality-filter CSV displayed B1 filter counts. No B1 performance comparison/parameter fitting/UI/optimization used. This means the phase cannot claim absolutely zero B1-derived content was displayed.',
        'yellow_chronology':'Conservative assumption fixed before search; detailed onset diagnostic completed after search. Not an empirically identified decision model, no subsequent rule fitting.',
        'validation_description':freeze['validation_description']}
    (out/'b2_baseline_decision.json').write_text(json.dumps(decision,indent=2),encoding='utf-8')
    current=hashlib.sha256(b''.join(p.read_bytes() for folder in ['simulation','calibration'] for p in sorted((ROOT/folder).glob('*.py')))).hexdigest()
    manifest={'freeze_integrity':checks,'B1_LOCKED':True,'calibration_code_sha256':params['code_sha256'],'current_code_sha256':current,
        'post_search_code_change':'Plot title encoding corrected and recorder instrumentation columns added: per-boundary exit counts, braking count, signal-stopped count. No physics/parameters changed; reference exporter rerun, final replicate summaries unchanged.',
        'physics_files_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'simulation'/name for name in ['agents.py','model.py','network.py','signals.py','demand.py','parameters.py']]},
        'outputs_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sorted(out.glob('b2_*')) if p.is_file() and p.name!='b2_runtime_manifest.json'}}
    (out/'b2_runtime_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    rows=[]
    for metric,indicator in [('mean_speed_ft_s','speed'),('mean_headway_ft','headway'),('mean_travel_time_s','route_travel_time'),('stopped_fraction','stopped_fraction'),('vehicles_exited','exit_throughput_total')]:
        s=summary.loc[metric];real=compare.loc[indicator,'real_mean']
        rows.append(f'| {metric} | {real:.6f} | {s["mean"]:.6f} | {s["SD"]:.6f} | [{s["CI95_low"]:.6f}, {s["CI95_high"]:.6f}] |')
    table='| Indicator | Real B2 | Simulated mean (30 seeds) | SD | IC95 mean |\n|---|---:|---:|---:|---|\n'+'\n'.join(rows)
    report=f'''# PEACHTREE-3 verification report

Decision: **{decision['classification']}**. {reason}

{table}

## Engine and statistical checks

Real AgentPy subclasses and lifecycle are exercised, not a custom loop pretending
to be AgentPy. Synthetic A–H checks cover free acceleration, slow leader response,
red stopping before the reference, green release, nonoverlap, EXITED, identical
seed results and SI/dt consistency. Additional tests reject invalid initial
overlap, wrong dt, nonfinite parameters and unsafe insertion. Permuting agent
creation order produces the same spatial result. All ticks check conservation;
all30 final runs have21 initial+253 entered=274 exited, zero remaining/pending and
zero acceleration safety interventions. No negative speed or overlap exceptions.

{runs.candidate.nunique()} evaluated candidates ×3 fixed development seeds =
{len(runs)} rollouts, then30 fixed final seeds. Powell reached the prespecified
finite budget; this is not a global convergence guarantee. Each normalized error
is exported separately. Throughput totals agree but temporal-bin discrepancies
remain; total agreement alone is not fidelity. KS distances are descriptive,
not significance claims on autocorrelated repeated frames.

Full-route travel excludes initial agents. Separate post-search section diagnostic
uses the same two reference cuts: observed {diagnostic['section_time_observed_mean_s']:.3f}s,
simulated {diagnostic['section_time_simulated_mean_s']:.3f}s,262 pairs each. This was
not an objective used to choose parameters. Section mismatch reinforces revision.

## Emergent numerical evidence

Maximum active population {diagnostic['max_active']}; maximum exactly-stopped
vehicles {diagnostic['max_stopped']}; maximum connected queue proxy
{diagnostic['max_queue_proxy']}; maximum negative-acceleration count
{diagnostic['max_braking_vehicles']}. Signal-stopped/following/free-flow exposures
and changing collective speed are exported. Formation and release are numeric
series, not just an animation. Backward braking-wave causality has not been
established; spatial states and braking counts provide instrumentation.

## Tests and interface

{tests['tests_total']} collected: **{tests['passed']} passed, {tests['skipped']} skipped,
0 failures/errors**. All56 historical cases are retained, including the50 that
passed in the earlier phase.20 historical actual-source/mixed-metric cases are
now skipped before setUpClass to respect B1 closure, alongside6 prior unavailable
I80 cases.30 safe historical cases and31 new cases ran. Use
`python -m scripts.run_train_tests`; do not run legacy source fixtures unfiltered.

Streamlit AppTest passed rendering, TRAIN-only CSV paths, Run/Pause/Reset,
seed-triggered AgentPy execution, disabled E1/E2/E3 and visual-speed independence
from engine summaries. Canvas JavaScript executes with a mocked DOM/2D context,
updates playback cards and persists time via requestAnimationFrame. This is not
visual browser QA. Real browser inventory was empty; no screenshot or actual
browser rendering check could be completed. UI server runs locally on port8501.
The interface is implemented and component tested; visual fidelity is unverified.

## Revisions and methodological incidents

The first attempt failed on real initial B2 overlap before a successful rollout;
original freeze retained, explicit start/desired-speed amendment applied before
search. Road-transition quality-filter implementation corrected and same search
repeated; previous TRAIN artifacts retained. Serialization export failed on NumPy
int64 once, then was corrected; completed optimization and replicas were preserved.
After the final search only recorder columns were added; reference export was
rerun without tuning. Calibration and current code hashes are both retained.

An accidental shell header read of `peachtree_quality_filters.csv` displayed
legacy B1 filter rows. No B1 speed/headway/travel/throughput performance was opened
for development, no B1 data entered estimation or optimizer, and no B1 metrics
were loaded by Streamlit. This incident is disclosed instead of claiming zero
B1-derived material was ever displayed. B1 remains locked for model use. Hashing
mixed immutable source bytes is an integrity check, not behavioral analysis.

Yellow's comfortable-distance assumption was frozen before search. Detailed
TRAIN onset diagnostics came afterward:63 onset observations,18 yellow crossings.
This chronology does not identify an observed behavioral decision boundary; keep
yellow classified ASSUMPTION and audit it in a TRAIN-only revision.

## Limits and next decision

Stopped fraction is strongly understated. Continuous IDM approaches rest and
raw NGSIM contains exact-zero plateaus; distinguish source measurement semantics
from physical dwell before revising. This is a hypothesis, not an established
cause. Omitting local/turning streams and discretionary changes can also inflate
headways and alter discharge. Do not fix fit visually or choose a better seed.
Final CI covers RNG variability only, not model discrepancy. No arbitrary WAPE
acceptance threshold. Frozen hashes verified; scope/classes/intersections unchanged.

Remain in TRAIN revision. **Do not open B1 or implement E1/E2/E3.** Future
validation label: {freeze['validation_description']}.
'''
    (docs/'verification_report.md').write_text(report,encoding='utf-8')
    p=params['parameters'];speed=compare.loc['speed'];head=compare.loc['headway'];tt=compare.loc['route_travel_time']
    delivery=f'''# PEACHTREE-3 — entrega en24 puntos

1. Arquitectura: simulation/, calibration/, ui/, tests/ separan datos, física,
   búsqueda, métricas e interfaz. AgentPy es el motor real.
2. VehicleAgent: ap.Agent conID sintético, clase, dimensiones, estado cinemático,
   ruta, líder/seguidor y tiempos de entrada/salida.
3. Estados: ENTERING, FREE_FLOW, FOLLOWING, STOPPED_SIGNAL, LANE_CHANGING, EXITED.
4. Entorno: Through clases2/3, Y400–1400ft, dos carriles por sentido,11th/12th;
   stop lines son proxies de mouths, lateral esquemático.
5. Señales: cuatro series B2 Through confirmadas I2/I3 NB/SB, sin modificar tiempos.
6. dt:0,1s por step AgentPy; reproducción visual independiente.
7. Arrivals:253 eventos exógenos B2; velocidades de frontera muestreadas por
   dirección con RNG semillado, inserción segura y retrasos registrados.
8. Inicialización:21 vehículos en frame936,93,4s. Primer snapshot sin overlap
   tras estar conocidas todas las señales; enmienda explícita, original conservado.
9. Car-following: IDM agrupado, integración balística y rojo como líder virtual;
   amarillo conservador ASSUMPTION; sin replay después de inicializar.
10. Parámetros CALIBRATED B2: v0={p['v0']:.6f}m/s; T={p['T']:.6f}s;
    s0={p['s0']:.6f}m; a={p['a']:.6f}m/s²; b={p['b']:.6f}m/s². δ=4 literatura.
11. Calibración: estimaciones empíricas,16 LHC, Powell40 evaluaciones;57 candidatos
    ×seeds10/11/12. Objetivo normalizado explícito, sin ajustar posiciones.
12. TRAIN final:30 réplicas1000–1029 conmean/SD/IC95. Desarrollo, no validación.

{table}

13. Speed: referencia seed10 real {speed.real_mean:.3f} vs sim {speed.simulated_mean:.3f}ft/s;
    KS={speed.ks:.4f}; W1={speed.wasserstein:.4f}ft/s.
14. Headway: real {head.real_mean:.3f} vs sim {head.simulated_mean:.3f}ft;
    KS={head.ks:.4f}; W1={head.wasserstein:.4f}ft. Muestra observada limpia, sin
    correspondencia individual ni garantía de idéntica selección.
15. Travel cut-to-cut: {tt.real_mean:.3f} vs {tt.simulated_mean:.3f}s;
    W1={tt.wasserstein:.3f}s. Sección interna:34,214 vs37,741s, diagnóstico aparte.
16. Throughput:274 salidas reales/simuladas; errores temporales persisten.
    Series acumuladas por frontera y bins30s disponibles.
17. Detenidos: real9,916% vs referencia1,317%; fallo principal de compatibilidad.
18. Verificación: nooverlap, nonegative speed, rojo/verde, salidas, conservación,
    reproducibilidad, orden de agentes, dt/unidades y barreras TRAIN comprobados.
19. Emergencia: máximos35 activos,8 detenidos, cola5; series de frenado/señal/velocidad
    colectiva. No atribuir causalidad de ondas por una animación.
20. UI: Streamlit oscuro, Canvas conrequestAnimationFrame, Plotly, tarjetas en
    reproducción, Run/Pause/Reset, seed y parámetros de sololectura; E1/E2/E3 disabled.
    AppTest/JS pasan; QA visual real pendiente por navegador no disponible.
21. Pruebas:87 totales;61 pasan;26 seomiten (20 lockB1+6 heredadas I80);0 errores.
    Se conservan las50 pruebas previamente aprobadas.
22. B1=LOCKED para calibración, selección y UI. Incidencia de lectura accidental
    de cabecera de filtros legados revelada enverification_report.md; no uso enfit.
23. Clasificación: **B. BASELINE_NEEDS_REVISION** por detención/headway/residuos.
24. Recomendación: corregir modelo de observación/dwell y auditar residuos soloB2;
    reevaluar readiness antes de la fase holdout. No B1 ni escenarios enesta fase.

Inicio: `python -m streamlit run streamlit_app.py`.
Tests: `python -m scripts.run_train_tests`.
'''
    (docs/'peachtree3_delivery.md').write_text(delivery,encoding='utf-8')
    print(json.dumps({'classification':decision['classification'],'freeze_integrity':all(checks.values()),'tests':tests['tests_total'],'passed':tests['passed'],'skipped':tests['skipped'],'B1':'LOCKED'},indent=2))

if __name__=='__main__':main()
