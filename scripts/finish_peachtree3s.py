"""Publish receiving evidence, frozen directional scope and pre-fit comparison."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from calibration.receiving import OUT,LAST,EXIT
from simulation.training_data import ROOT,require_train
from scripts.evaluate_local import digest

def table(df):
    def cell(v):return f'{v:.5f}' if isinstance(v,(float,np.floating)) and np.isfinite(v) else ('NA' if pd.isna(v) else str(v).replace('|','/'))
    return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(cell(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))

def main(acquisition='B2'):
    require_train(acquisition);figures=OUT/'figures';figures.mkdir(exist_ok=True)
    decision=json.loads((OUT/'decision.json').read_text());data=pd.read_parquet(OUT/'target_full_downstream_observations.parquet')
    episodes=pd.read_csv(OUT/'post_control_stops.csv');geometry=pd.read_csv(OUT/'downstream_geometry.csv');clusters=pd.read_csv(OUT/'post_control_stop_clusters.csv')
    for idx,row in episodes[episodes.right_censored].iterrows():
        future=data[data.id.eq(row.id)&data.time.ge(row.end_time-1e-7)]
        if len(future) and (~future.longitudinal_observation).any():episodes.loc[idx,'observation_class']='OBSERVED_PATH_TURN_CENSORS_LONGITUDINAL_EPISODE'
        elif abs(row.track_termination_time_s-939.3)<.2:episodes.loc[idx,'observation_class']='WINDOW_END_RIGHT_CENSOR_NOT_PROVEN_ARTIFACT'
        else:episodes.loc[idx,'observation_class']='TRACK_TERMINATION_RIGHT_CENSOR_POSSIBLE_ARTIFACT_NOT_PROVEN'
    episodes.to_csv(OUT/'post_control_stops.csv',index=False)
    lead=pd.read_csv(OUT/'post_control_leaders.csv');capacity=pd.read_csv(OUT/'receiving_capacity.csv');block=pd.read_csv(OUT/'receiving_block_episodes.csv')
    summary=pd.read_csv(OUT/'pre_recalibration_metrics.csv');real=pd.read_csv(OUT/'real_same_scope_metrics.csv').iloc[0]
    real['section_travel_mean_s']=pd.read_csv(ROOT/'outputs/b2_observed_section_times.csv').travel_time_s.mean()
    scopes=pd.read_csv(OUT/'scope_comparison.csv')
    scopes['signal_coverage']='Four confirmed B2 I2/I3 Through series, complete selected window; extra controls incomplete ifextended'
    scopes['vehicle_count']=scopes.vehicles_observed
    scopes['travel_time_available']=scopes.complete_route_vehicles.gt(0)
    scopes['throughput_boundary']=scopes.get('throughput_observed',pd.Series(index=scopes.index,dtype=float)).fillna(274.)
    scopes['headway_available']=True;scopes['stopping_measurable']=True
    scopes.to_csv(OUT/'scope_comparison.csv',index=False)
    comparison=[]
    for metric in ['speed_mean_ft_s','speed_KS','speed_W1_ft_s','headway_mean_ft','headway_KS','headway_W1_ft','travel_mean_s','travel_W1_s','operational_stopped','stop_episodes','complete_stop_duration_mean_s','stop_duration_W1_s','queue_proxy_mean','queue_proxy_max','throughput_total','throughput_temporal_L1_normalized','section_travel_mean_s']:
        row={'metric':metric,'REAL_B2_same_boundaries':real.get(metric,np.nan)}
        for mode in ['OLD','REVISED','NEW_REDUCED_SCOPE']:
            q=summary[(summary['mode']==mode)&(summary.metric==metric)];row[mode]=q['mean'].iloc[0] if len(q) else np.nan
        comparison.append(row)
    comparison=pd.DataFrame(comparison);comparison.to_csv(OUT/'real_sim_same_boundary_comparison.csv',index=False)
    # Spatial/temporal figures show observed phenomenon, never animated fake queues.
    fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    for ax,di in zip(axes,[2,4]):
        d=data[data.cohort_direction.eq(di)&data.longitudinal_observation&data.downstream_ft.gt(0)];ax.scatter(d.downstream_ft.iloc[::12],d.speed.iloc[::12],s=2,alpha=.2)
        ax.axvspan(0,1246.452-LAST[2] if di==2 else LAST[4]-647.878,color='#dcebef',alpha=.65,label='Own junction after nominal proxy')
        ax.axvline(abs(EXIT[di]-LAST[di]),color='black',linestyle='--',label='Current exit');ax.set(title=f'B2 direction{di}',xlabel='Distance after nominal last control(ft)',ylabel='Observed speed(ft/s)');ax.legend()
    fig.savefig(figures/'post_control_speed_position.png',dpi=140);plt.close(fig)
    hist=pd.read_csv(OUT/'post_control_spatial_bins.csv');fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    for ax,di in zip(axes,[2,4]):
        for width in [10,25,50]:
            d=hist[(hist.direction==di)&(hist.bin_width_ft==width)];ax.step(d.bin_start_ft,d.density_vehicle_seconds_per_ft,where='post',label=f'{width}ft bins')
        ax.axvline(abs(EXIT[di]-LAST[di]),color='black',linestyle='--');ax.set(title=f'Direction{di}: operational stopping',xlabel='Distance after nominal last control(ft)',ylabel='Vehicle-seconds /ft');ax.legend()
        ax.axvspan(0,1246.452-LAST[2] if di==2 else LAST[4]-647.878,color='#dcebef',alpha=.65)
    fig.savefig(figures/'post_control_stopping_density.png',dpi=140);plt.close(fig)
    frame=pd.read_csv(OUT/'receiving_frame_audit.csv');fig,axes=plt.subplots(2,1,figsize=(12,6),layout='constrained')
    for ax,di in zip(axes,[2,4]):
        z=frame[frame.direction==di];ax.plot(z.time,z.upstream_stopped,label='Stopped target within100ft upstream');ax.plot(z.time,z.downstream_stopped,label='Stopped observed arterial within200ft downstream');ax.set(title=f'Direction{di}',xlabel='Time(s)',ylabel='Observed stopped count (not inferred queue capacity)');ax.legend()
    fig.savefig(figures/'post_control_queue_timeline.png',dpi=140);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4),layout='constrained');z=lead[(lead.region=='POST_CONTROL_REGION')&(lead.subset=='ALL_STOPPED_INCLUDING_UNUSABLE')]
    for di,offset in [(2,-.2),(4,.2)]:
        q=z[z.direction==di];ax.bar(np.arange(len(q))+offset,q.fraction,width=.4,label=f'Direction{di}')
    ax.set_xticks(np.arange(5),['TARGET','NON_TARGET23','TURNING','CROSS/LOCAL','UNUSABLE']);ax.set(ylabel='Fraction of post-proxy stopped frames',title='Physical leader category; unusable is not absence of control');ax.legend();fig.savefig(figures/'downstream_leader_categories.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(12,6),layout='constrained')
    for ax,di in zip(axes,[2,4]):
        for width in [5,10,30,60]:
            q=capacity[(capacity.direction==di)&(capacity.bin_s==width)];ax.step(q.start_s,q.observed_flow_veh_h,where='post',label=f'{width}s bins',alpha=.75)
        ax.set(title=f'Direction{di}: observed TARGET crossings',xlabel='Time(s)',ylabel='Demand-conditioned flow(veh/h), not capacity');ax.legend()
    fig.savefig(figures/'receiving_flow_over_time.png',dpi=140);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4),layout='constrained');g=geometry.set_index('direction')
    for y,di in [(1,2),(0,4)]:
        start=400 if di==2 else 1400;old=EXIT[di];new=decision['exit_ft']['NB' if di==2 else 'SB'];ax.plot([start,old],[y,y],lw=12,color='#c4cbd2',label='Current' if di==2 else None);ax.plot([start,new],[y,y],lw=5,color='#197e83',label='Reduced directional route' if di==2 else None);ax.scatter([LAST[di],new],[y,y],c=['#cc7a21','#197e83'],s=70)
    ax.axvspan(647.878,777.753,color='#dcebef',alpha=.6);ax.axvspan(1172.939,1246.452,color='#dcebef',alpha=.6);ax.set(yticks=[0,1],yticklabels=['SB','NB'],xlabel='Local_Y(ft)',title='Physical scope decision before simulated fit');ax.legend();fig.savefig(figures/'scope_comparison.png',dpi=140);plt.close(fig)
    frozen=json.loads((OUT/'pre_revision_hashes.json').read_text());checks={p:digest(ROOT/p)==sha for p,sha in frozen['hashes'].items()}
    if not all(checks.values()):raise RuntimeError('Earlier phase file changed: '+str([p for p,v in checks.items() if not v]))
    (OUT/'preservation_check.json').write_text(json.dumps({'all145_original_hashes_match':True,'checks':checks},indent=2),encoding='utf-8')
    decision['previous_stages_preserved']=True;decision['IDM_recalibrated']=False;decision['ui_boundary_activation']='Not activated: original OLD/REVISED displays preserved; reduced technical trace prepared for boundary approval.'
    decision['methodological_incident']='Initial read of mixed legacy reconstruction markdown displayed previously exposed B1 feasibility summaries. No B1 trajectory/signal dataset was accessed or used for geometry, boundary choice, mechanism ranking or evaluation. No fully-unseen claim.'
    (OUT/'decision.json').write_text(json.dumps(decision,indent=2),encoding='utf-8')
    physical=f'''# PEACHTREE-3S — contexto de recepción

El rótulo antiguo “post-control” confundía pasar un proxy con haber salido de una
intersección. B2 completo cambia la interpretación: **NB no tiene detenciones
TARGET después de la salida completa de12th y antes deY1400**. Los4304 frames
stopped NB del bucket viejo están entreY1174–1192, enla aproximación/interior de
12th;4064 ocurren enRED deesa misma señal. No prueban una receiving queue externa.
La cifra anterior73,65% no debe interpretarse ahora como atribución causal de
receiving desconocido: incluía esta clasificación espacial incorrecta.

EnSB sí hay4948 stopped frames TARGET enla carretera después de salir de11th,
con onset hastaY514,535 y posiciones hasta514,676. El siguiente control es10th,
aprox166,46ft después delexit actualY400. Líderes detenidos sustentan seguimiento
enesa región. Más allá de1400NB, losonsets se concentran cerca de14th, no13th.

## Física observada por dirección

{table(geometry)}

NB: última señal12th, proxy1168,9155, exit1400;231,0845ft después delproxy.
SigueS4, luego13th/I4 conSTOP documentado aaprox1589,104 yS5 hasta14th/I5.
SB: última señal11th, proxy777,262, exit400;377,262ft después delproxy.
SigueS2, luego10th/I1 semaforizada aaprox233,5375 yS1. Dos carriles normales
observados antes/después; lane11 esbahía, no tercer carril de capacidad probado.
No seidentificó lane drop. Local_Y esproyección longitudinal, no arclength exacta.

Fuentes: metadata oficial Peachtree; informe oficial **0400pm–0415pm**, Fig4 p11
(página impresa6), descripción decontroles p10; B2 section/int/O-D/direction/movement,
posiciones globales ylocales; TXT **0400-0415** de10thSB y14thNB. La figura oficial
serenderizó comoofficial_schematic.png. GIS existente tiene8 polígonos decámaras,
no topología de carriles. DWG disponible pero no decodificado: no seinventó una
lectura deentidades. Tube detectors sonagregados15min, no arrivals ni gap events.

## Stops, clusters y líderes

{table(episodes.groupby(['direction','onset_region']).agg(episodes=('id','size'),vehicles=('id','nunique'),median_onset_y=('onset_y_ft','median'),median_duration_s=('duration_s','median')).reset_index())}

{table(clusters[['direction','center_ft','vehicles','episodes','associated_section','associated_intersection','known_control_nearby','classification']])}

Bins10/25/50ft verifican sensibilidad; losgrupos25ft sondescriptivos yno descubren
intersecciones automáticamente. Hayposición deonset/release, censura, track end,
O-D, movimiento ytime since lastcontrol. Censura no equivale aobservation artifact;
un stop conrelease observado es distinto deuna terminación de seguimiento. No se
asume que todos losstops seancongestión. Loscambios depath después delscope original
limitan observabilidad longitudinal yse retienen como advertencia.

{table(pd.read_csv(OUT/'background_share_by_region.csv'))}

Enelbucket POST nominal, omitted leader share válidoNB1,32%,SB5,16%; dentro del
CONTROLLED actualNB11,02%,SB7,64%. No aumenta claramente downstream dentro del
scope actual. Más allá deexits:NB11,03%,SB5,78%. Enstopped POST nominal, NB0% tiene
leader válido detenido ySB76,45% sí. LoNB escompatible concontrol directo propio
yreferencias ambiguas enint/lane0, no prueba de ausencia deun líder físico.
Las categorías A/B/C/D/E sonexclusivas; referencias cross/local incoherentes para
CF seconsideran inutilizables, no un conflicto longitudinal inventado.
A significa pertenencia a la cohorte Through de11th/12th; fuera deese alcance
el mismo target puede girar. No seinterpreta esa pertenencia como Through en10th/14th.

## Receiving ycontroles posteriores

{table(pd.read_csv(OUT/'next_control_audit.csv'))}

13th sí estágeométricamente aguas abajo delexitNB. **No escausa sustentada del
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
Esto es asociación condicionada, no prueba deuna supply law ni replay. Detalles
en next_signal_conditioned_stops.csv. Thru schedules completos no significan que
todas laspermisiones/conflictos de turning estén completamente observados.

{table(block)}

Los6 candidatosSB deblocking suman9,1s;mediana0,9s,máximo5s. Exigen simultáneamente
targets stopped100ft upstream, class23 stopped200ft downstream, último control
GREEN yningún crossing en tickscontiguos0,1s. Soncondiciones observadas necesarias,
no identificación deuna supply law ni prueba de backward shockwave. Se exportan
occupancy, stopped counts, crossings5/10/30/60s yflujo observado demand-conditioned.
No seintrodujo capacity fija niservice slots copiados deexits reales.

{table(pd.read_csv(OUT/'mechanism_candidates.csv'))}

HIGH: reclasificación de stops ligadosal propio12th, ubicación física documentada
de controles. MEDIUM: siguiente signal como sistema receptor completo, spillback,
finite capacity, turning/background, artifact deobservación. LOW: STOP13th como
causa delresidual ylane drop. Existencia HIGH deuna señal no convierte sus
interacciones incompletas enun mecanismoHIGH implementable.
'''
    (ROOT/'docs/peachtree3s_receiving_context.md').write_text(physical,encoding='utf-8')
    tests_path=OUT/'test_report.json';tests=json.loads(tests_path.read_text()) if tests_path.exists() else {'tests_total':'pending','passed':'pending','skipped':'pending'}
    report=f'''# PEACHTREE-3S — decisión descope

Decisión exacta: **B. FREEZE_REDUCED_SCOPE**.
Readiness: **B. NEEDS_ONE_MORE_STRUCTURAL_REVISION**.

No seextendió Peachtree ni seañadió física receiving especulativa. No hay un mecanismo
externo conconfianzaHIGH ytodos susparámetros/interacciones esenciales identificados.
Sí existen cortes físicos defendibles anteriores aese contexto. La reducción es
direccional yconserva los ingress observados: no elimina lasaproximaciones necesarias.

| Sentido | Entrada conservada(ft) | Salida anterior(ft) | Salida congelada(ft) | Longitud ruta(ft) |
|---|---:|---:|---:|---:|
| NB |400|1400|1346.452|946.452|
| SB |1400|400|597.878|802.122|

No seexpresa como un único intervalo común: NB400→1346,452 ySB1400→597,878.
Ambas rutas conservan11th/12th ysu link. Se mantiene espacio después dela
intersección completa:100ft NB,50ft SB. NB no tiene stopped TARGET enese buffer;
SB tampoco. Se contrastaron candidatos comunes25/50/100ft yse conservaron entradas
originales para no truncar anticipación/frenado ni alterar arrivals porun cut nuevo.

Selección **ANTES deSIM fit**: mayor buffer predeclarado con separación física.
EnSB el receiving stopped vehicle BODY observado llega aY558,089. El candidato
100ft dejaría exit547,878 e invadiría esa carrocería; se rechaza. Exit597,878 deja
39,789ft frente astandstill-gapB2 P90+nominal4ft deallowance. Este último no es
garantía universal deseguridad ni deindependencia contrafactual. Fuente: B2 y
geometría, no elmenor error. Scenario relevance es11th/12th dentro deestas fronteras
condicionales; no beneficios full-network ni predicciones de10th/14th. Future queues
fuera delrégimen observado puedeninvalidar receiving libre ydeben declararse.

No se presenta el corte como libre deanticipación de otros vehículos en todo futuro. El chequeo adicional
de retained_buffer_external_leader_audit.csv encuentra16 frames deun targetSB
(1,6s;0,664% delbuffer) siguiendo a un líder externo detenido, y0 enNB. Esa pequeña
exposición de borde estádocumentada; no seafirma independencia absoluta delreceiving.

{table(pd.read_csv(OUT/'scope_comparison.csv')[['candidate','north_entry_ft','north_exit_ft','south_entry_ft','south_exit_ft','vehicles_observed','complete_route_vehicles','selected','physical_interpretability']])}

## Implementación ysameness de métricas

Modo separadoNEW_REDUCED_SCOPE, subclass deDiagnosticModel/ap.Model. Seheredan
VehicleAgent, IDM, signals, FIFO, release ydt. Solo sealtera salida: natural
crossing detectado delpaso balístico, timestamp interpolado yEXITED. No posición
histórica, cambio develocidad ni teleport. Cinco IDM, threshold0,1m/s, stop-lines
yoffsets permanecencongelados. Ningún agente adicional; TARGET sigueigual.

Source ySIM usan losmismos cortes por dirección ylas mismas métricasoperacionales.
274 targets enventana;253 viajes completos medidos desde entradas originales;
21 iniciales excluidos deTT completo. OLD/REVISED se evalúan enlos mismos cortes,
aunque susagentes continúan fuera; NEW losretira físicamente allí. No se comparan
viajes de longitudes diferentes como si fueran iguales. Eventos EXITED tienen
ledger explícito: la últimamuestra deun agente antes delcut no basta para inferir
su salida. Una primera evaluación falló por usar crossing desde snapshots truncados;
se corrigió aledger deeventos yse repitió la evaluación, sin tuning.

90 corridas: OLD/REVISED/NEW conlas mismas30 seeds3000–3029. No optimization,
no recalibration. Mean/SD/IC95 de media enpre_recalibration_metrics.csv cubren RNG,
no discrepancy ni source uncertainty. Reference210 prefijado, no best seed.

{table(comparison)}

Enesas fronteras REALspeed15,9189ft/s,TT54,1619s,operational stop27,3543%.
NEWmean speed14,7588,TT58,3927,stop21,3595%; error/residuo persiste yse reporta.
Todos losmodos conservan274 exits,remaining0,pending0. Elgran receiving SB observado
seexcluye físicamente, pero eldiagnósticoNB muestra una representación pendiente
del propio control: fuente B2 se detiene después delproxy dentro de12th.
La asociación decontrolled envelope/first queue head/stop reference debe auditarse
antes deajustar IDM. No se deduce una painted bar desde elmejor fit ni semueve aquí.
Ésa es lacorrección concreta adicional deconfianza fuerte, no receiving aleatorio.

## Preservación, tests yUI

145 hashes pre-revisión coinciden; no sobrescritura dePEACHTREE-3/3R. Nueva fuente
yartefactos solo enpeachtree3s; mapas/metadata oficiales B2 separados. B1 permanece
inaccesible alectores ymodel selection. Incidencia: lectura inicial demarkdown legado
mixto mostró resúmenesB1 previamenteexpuestos; no seaccedió datasets/schedules B1 ni
seusó eso para decisiones. Se declara en vez deafirmar exposición absolutamente cero.

Tests: {tests['tests_total']} total,{tests['passed']} passed,{tests['skipped']} skipped.
Las fixtures anteriores de fuentes mixtas/B1 siguenomitidas antes de setUpClass;
los métodos sintéticos sí se ejecutan. Nuevos tests validan direcciones, clasificación,
bins, episodes, leaders,block detection,next control,B1 guard,scope一致,
conservación/exit ledger,no replay,scenario relevance ypreservación/preprocessing.

UI originalOLD/REVISED conservada; no rediseño ni activación silenciosa delnuevo
scope. Trace técnico preparado; límites seactivarán trasaprobar lafrontera y
resolver larepresentación delcontrol. E1/E2/E3 disabled,TESTLOCKED.
UI_IMPLEMENTED_NOT_BROWSER_VALIDATED. No seafirma QA visual deunbrowser.

Siguiente paso: revisiónB2 del controlled envelope/lane-specific front reference
ycondicionamiento dela primera cabeza decola. Mantener boundaries seleccionados
congelados; no recalibrar todavía ni abrir B1. Nombre futuro devalidación:
TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.
'''
    # Readable scientific prose without altering filenames/code identifiers.
    import re
    for name,text in [('peachtree3s_receiving_context.md',physical),('peachtree3s_scope_decision.md',report)]:
        text=text.replace('scope一致','scope consistency')
        joins={'delexit':'del exit','delproxy':'del proxy','delbucket':'del bucket','delpropio':'del propio','delcontrol':'del control','delcut':'del cut','enla':'en la','enel':'en el','ese contexto':'ese contexto',
            'deuna':'de una','deque':'de que','deseñal':'de señal','sepuede':'se puede','seobserv':'se observ','seclasific':'se clasific','semueve':'se mueve','secomparan':'se comparan','seextendió':'se extendió','seañadió':'se añadió','seintrodujo':'se introdujo','setrata':'se trata','seconserv':'se conserv','seutiliz':'se utiliz',
            'conlas':'con las','susparámetros':'sus parámetros','dela':'de la','delas':'de las','delos':'de los','enlos':'en los','enese':'en ese','enesa':'en esa','enesas':'en esas','deese':'de ese',
            'aprox166':'aprox 166','aaprox':'a aprox','seidentificó':'se identificó','escompatible':'es compatible','serenderizó':'se renderizó','seinventó':'se inventó','parainferir':'para inferir','No seafirma':'No se afirma','No seextendió':'No se extendió',
            'B2 section':'B2 section','sondescriptivos':'son descriptivos','soncondiciones':'son condiciones','corrección concreta':'corrección concreta','seactivarán':'se activarán','seactiv':'se activ','seheredan':'se heredan','sealtera':'se altera','seexpresa':'se expresa','seexcluye':'se excluye','seretienen':'se retienen','selocaliz':'se localiz',
            'lider físico':'líder físico','yse':'y se','yoffsets':'y offsets','ydt':'y dt','ylocales':'y locales','ytime':'y time','yflujo':'y flujo','yventana':'y ventana','ysu':'y su','yfirst':'y first','ysameness':'y sameness','yartefactos':'y artefactos','yrepresentación':'y representación','yposiciones':'y posiciones',
            'los4304':'los 4304','Los4304':'Los 4304','los6':'los 6','Los6':'Los 6','NI':'NI','scope original':'scope original','lastcontrol':'last control','oprior':'o prior','deque':'de que'}
        for old,new in joins.items():text=text.replace(old,new)
        text=re.sub(r'\b(\d+(?:[.,]\d+)?)(ft|s|min)\b',r'\1 \2',text)
        text=re.sub(r'\b(enla|enel|dela|delproxy|deseñal|deese|deque|descope|setiene|seextendió|seañadió|seidentificó|serenderizó|seinventó|seintrodujo|seexpresa|sealtera|seheredan|serechaza|conlas|susparámetros)',lambda m:{'enla':'en la','enel':'en el','dela':'de la','delproxy':'del proxy','descope':'de scope','seextendió':'se extendió','seañadió':'se añadió','seidentificó':'se identificó','serenderizó':'se renderizó','seinventó':'se inventó','seintrodujo':'se introdujo','seexpresa':'se expresa','sealtera':'se altera','seheredan':'se heredan','serechaza':'se rechaza','conlas':'con las','susparámetros':'sus parámetros'}.get(m.group(),m.group()),text)
        (ROOT/'docs'/name).write_text(text,encoding='utf-8')
    required=['pre_revision_hashes.json','downstream_geometry.csv','post_control_stops.csv','post_control_stop_clusters.csv','post_control_leaders.csv','receiving_capacity.csv','receiving_block_episodes.csv','next_control_audit.csv','background_share_by_region.csv','mechanism_candidates.csv','scope_candidates.csv','scope_comparison.csv','pre_recalibration_metrics.csv','decision.json']
    if not all((OUT/name).exists() for name in required):raise RuntimeError('Missing artifact')
    manifest={'B1_LOCKED':True,'prior_hashes_match':True,'required_artifacts':len(required),'physics_changed':False,'bounds_changed_in_separate_mode':True,
        'hashes':{str(p.relative_to(ROOT)):digest(p) for p in OUT.glob('*') if p.is_file() and p.name!='artifact_manifest.json'}}
    (OUT/'artifact_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'decision':decision['decision'],'readiness':decision['readiness'],'prior_hashes_preserved':True,'required_artifacts':len(required),'B1':'LOCKED'},indent=2))

if __name__=='__main__':main()
