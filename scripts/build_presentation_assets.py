"""Derive presentation statistics/exports only; never runs AgentPy experiments."""
import json,hashlib,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from importlib.metadata import metadata
from plotly.subplots import make_subplots
from PIL import Image,PngImagePlugin
from ui.presentation_data import *

def write_table(name,d,source):
    d=source_table(d,source);d.to_csv(ASSETS/'tables'/name,index=False);return d

def observations(context):
    if context=='B2':
        core=pd.read_parquet(ROOT/'data/b2_baseline_source.parquet');full=pd.read_parquet(ROOT/'data/b2_all_observed.parquet');source='data/b2_baseline_source.parquet'
        origin=read_json('outputs/peachtree3u/final_inputs.json')['source_window_start_relative_s']
    else:
        core=pd.read_parquet(ROOT/'outputs/peachtree5/b1_target_core.parquet');full=pd.read_parquet(ROOT/'outputs/peachtree5/b1_source.parquet');source='outputs/peachtree5/b1_target_core.parquet'
        origin=read_json('outputs/peachtree5/b1_exogenous_inputs.json')['source_window_start_relative_s']
    assert core.acquisition_id.eq(context).all() and full.acquisition_id.eq(context).all()
    core=core[core.t_relative.ge(origin)&((core.direction.eq(2)&core.local_y.between(400,1346.452))|(core.direction.eq(4)&core.local_y.between(597.878,1400)))].copy()
    cf=pd.read_parquet(ROOT/f'outputs/working/peachtree_cf_preparation_{context}.parquet');keys=set(zip(cf.vehicle_id,cf.frame_id))
    leader=full.set_index(['frame_id','vehicle_id']).reindex(pd.MultiIndex.from_arrays([core.frame_id,core.preceding]));y=leader.local_y.to_numpy()
    mask=np.array([(v,f) in keys for v,f in zip(core.vehicle_id,core.frame_id)])&np.where(core.direction.eq(2),(y>=400)&(y<=1346.452),(y>=597.878)&(y<=1400))
    cfcore=core[mask&core.space_headway.gt(0)]
    # Existing final metric distributions, B2 cut-to-cut travel reconstructed
    # descriptively from the isolated source, without any model execution.
    if context=='B1':travel=np.load(ROOT/'outputs/peachtree5/REAL_B1_travel.npy');duration=np.load(ROOT/'outputs/peachtree5/REAL_B1_duration.npy')
    else:
        d=pd.read_parquet(ROOT/'outputs/peachtree3s/target_full_downstream_observations.parquet');events=[]
        for id,g in d.sort_values(['id','frame']).groupby('id'):
            di=int(g.cohort_direction.iloc[0]);g=g[g.direction.eq(di)];sgn=1 if di==2 else -1;yy=g.y.to_numpy()*sgn;tt=g.time.to_numpy();ff=g.frame.to_numpy();times=[]
            for cut in ([400,1346.452] if di==2 else [1400,597.878]):
                hit=np.flatnonzero((yy[:-1]<cut*sgn)&(yy[1:]>=cut*sgn)&(np.diff(ff)==1))
                if len(hit):j=hit[0];times.append(tt[j]+.1*(cut*sgn-yy[j])/(yy[j+1]-yy[j]))
            if len(times)==2:events.append(times[1]-times[0])
        travel=np.array(events)
        d=pd.read_parquet(ROOT/'outputs/peachtree3s/real_same_scope_observations.parquet');durations=[]
        for id,g in d.sort_values(['id','frame']).groupby('id'):
            mask=g.speed.to_numpy()<=.1/(1200/3937);fr=g.frame.to_numpy();j=0
            while j<len(g):
                if not mask[j]:j+=1;continue
                k=j
                while k+1<len(g) and mask[k+1] and fr[k+1]==fr[k]+1:k+=1
                if j>0 and k+1<len(g) and fr[k+1]==fr[k]+1:durations.append((k-j+1)*.1)
                j=k+1
        duration=np.array(durations)
    path='outputs/peachtree3u/final_inputs.json' if context=='B2' else 'outputs/peachtree5/b1_exogenous_inputs.json';inp=read_json(path)
    arrivals=np.sort([r['requested_time_s'] for r in inp['entries']]);interarrival=[]
    for di in [2,4]:interarrival.extend(np.diff(sorted(r['requested_time_s'] for r in inp['entries'] if r['direction']==di)))
    values={'speed':(core.v_vel.to_numpy(),'ft/s','vehicle-time'), 'acceleration':(core.v_acc.to_numpy(),'ft/s²','vehicle-time, observed saturation retained'),
        'Space_Headway':(cfcore.space_headway.to_numpy(),'ft','cleaned road CF; in-scope leader'),
        'Time_Headway':(cfcore[cfcore.time_headway.gt(0)&cfcore.time_headway.lt(9999.99)].time_headway.to_numpy(),'s','cleaned CF; undefined sentinel excluded'),
        'travel_time':(travel,'s','complete entry-to-exit journeys'), 'vehicle_length':(core.groupby('vehicle_id').v_length.first().to_numpy(),'ft','one value per vehicle'),
        'arrival_time':(arrivals,'s','requested boundary events, relative to start'), 'interarrival':(np.array(interarrival),'s','successive arrivals within direction'),
        'stopped_episode_duration':(duration,'s','complete operational-stopped episodes; censoring excluded')}
    return core,values,source,inp

def hist(values,title,source,unit):
    fig=go.Figure();allx=np.concatenate([v for v in values.values()]);edges=np.linspace(np.min(allx),np.max(allx),41)
    for context,x in values.items():
        count,_=np.histogram(x,edges);fig.add_trace(go.Bar(x=(edges[1:]+edges[:-1])/2,y=count/count.sum(),width=np.diff(edges),name=context,opacity=.7,marker_color=COLORS[context]))
    fig.update_layout(barmode='overlay');fig.update_xaxes(title=unit)
    return style(fig,title,source,'Proporción de observaciones')

def export(filename,fig):
    source=fig.layout.meta['source_artifact'];fig.write_json(ASSETS/'charts'/(Path(filename).stem+'.json'))
    fig.write_image(ASSETS/filename,width=1920,height=1080,scale=1)
    with Image.open(ASSETS/filename) as im:
        info=PngImagePlugin.PngInfo();info.add_text('source_artifact',source);im.save(ASSETS/filename,pnginfo=info)
    print(filename,flush=True)

def build():
    (ASSETS/'tables').mkdir(exist_ok=True);(ASSETS/'charts').mkdir(exist_ok=True)
    f=freezes();core={};values={};inputs={};stats=[];sources=[]
    for context in ['B2','B1']:
        core[context],values[context],source,inputs[context]=observations(context);sources.append(source)
        for variable,(x,unit,population) in values[context].items():
            x=np.asarray(x);x=x[np.isfinite(x)]
            stats.append(dict(context=context,Variable=variable,unit=unit,population=population,N=len(x),Mean=x.mean(),Median=np.median(x),SD=x.std(ddof=1),Variance=x.var(ddof=1),Min=x.min(),Max=x.max(),P25=np.quantile(x,.25),P75=np.quantile(x,.75),source_artifact=source+';'+('outputs/peachtree5/REAL_B1_{travel,duration}.npy' if context=='B1' else 'outputs/peachtree3s/{target_full_downstream,real_same_scope}_observations.parquet')))
    pd.DataFrame(stats).to_csv(ASSETS/'tables/descriptive_statistics.csv',index=False)
    dataset=read_csv('outputs/peachtree_acquisition_timing.csv')
    write_table('dataset_summary.csv',dataset,'outputs/peachtree_acquisition_timing.csv')
    params=f['calibration']['final_parameter_values'];pre=f['structure']['pre_calibration_IDM']
    write_table('model_parameters.csv',pd.DataFrame([dict(parameter=k,PRE=pre[k],FINAL=v,unit={'v0':'m/s','T':'s','s0':'m','a':'m/s²','b':'m/s²'}[k]) for k,v in params.items()]),'outputs/peachtree4/calibration_freeze.json;outputs/peachtree3u/structural_model_freeze.json')
    for name,source in {'calibration_pre_post.csv':'outputs/peachtree4/pre_vs_post_calibration.csv','validation_real_sim.csv':'outputs/peachtree5/train_vs_validation.csv',
        'scenario_results_B2.csv':'outputs/peachtree6/b2_scenario_summary.csv','scenario_results_B1.csv':'outputs/peachtree6/b1_scenario_summary.csv',
        'directional_results.csv':'outputs/peachtree6/directional_results.csv','paired_effects.csv':'outputs/peachtree6/paired_differences.csv','robustness.csv':'outputs/peachtree6/robustness_summary.csv'}.items():write_table(name,read_csv(source),source)
    write_table('decision_summary.csv',pd.DataFrame([dict(recommendation=f['experiment']['recommended_alternative'],classification=f['experiment']['classification'],validation=f['validation']['classification'])]),'outputs/peachtree6/experiment_freeze.json;outputs/peachtree5/validation_freeze.json')
    write_table('component_provenance.csv',read_csv('outputs/peachtree3u/component_classification.csv'),'outputs/peachtree3u/component_classification.csv')
    references=pd.DataFrame([
        dict(reference='USDOT / FHWA · NGSIM dataset8ect-6jqj',url='https://data.transportation.gov/Automobiles/Next-Generation-Simulation-NGSIM-Vehicle-Trajectories/8ect-6jqj',evidence='scripts/download_peachtree.py'),
        dict(reference='API de descarga',url='https://data.transportation.gov/resource/8ect-6jqj.json',evidence='scripts/download_peachtree.py'),
        dict(reference='Peachtree metadata',url='',evidence='data/reference/Peachtree_Street_Metadata_Documentation.pdf'),
        dict(reference='AgentPy documentación',url=metadata('agentpy').get('Home-page'),evidence='Installed AgentPy0.1.5 package metadata'),
        dict(reference='IDM utilizado',url=read_json('docs/b2_estimation_criteria.json')['delta']['source'],evidence='docs/b2_estimation_criteria.json')])
    write_table('references.csv',references,'scripts/download_peachtree.py;docs/b2_estimation_criteria.json;AgentPy package metadata')
    vars=[('Vehicle_ID','Identidad de trayectoria, con adquisición'),('Frame_ID','Reloj relativo a10Hz'),('Global_Time','Separar adquisiciones; epoch inconsistente, no fecha civil corregida'),('Local_X','Posición lateral del frente; contexto de carril'),('Local_Y','Frente longitudinal, alcance y crossings'),('v_Vel','Velocidad inicial/medición; no replay'),('v_Acc','Diagnóstico estadístico y estimación B2'),('Lane_ID','Carril inicial/entrada y seguimiento'),('Vehicle_Class','TARGET clases2/3'),('v_Length','Geometría del vehículo'),('v_Width','Ancho y render'),('Preceding','CF observado para métricas'),('Following','Reconstrucción de colas observadas'),('Space_Headway','Headway frente a frente'),('Time_Headway','Estimación empírica; sentinel excluido'),('Section_ID','Contexto vial'),('Int_ID','Transiciones de intersección'),('Direction','NB/SB'),('Movement','Through'),('Origin (o_zone)','Contexto de ruta'),('Destination (d_zone)','Contexto de ruta')]
    write_table('dataset_variables.csv',pd.DataFrame(vars,columns=['Variable','Uso en el modelo']),'data/reference/Peachtree_metadata_text.txt;data/peachtree_full.csv schema')
    source=';'.join(sources)
    for key,name in [('speed','06_speed_distribution.png'),('Space_Headway','06_headway_distribution.png'),('travel_time','06_travel_distribution.png')]:
        export(name,hist({c:values[c][key][0] for c in values},key+' · observaciones reales B1/B2',source,values['B2'][key][1]))
    export('06_acceleration_distribution.png',hist({c:values[c]['acceleration'][0] for c in values},'Aceleración observada B1/B2',source,'ft/s²'))
    for key,name in [('speed','06_speed_boxplot.png'),('travel_time','06_travel_boxplot.png')]:
        fig=go.Figure()
        for c in ['B1','B2']:
            x=values[c][key][0];q1,med,q3=np.quantile(x,[.25,.5,.75]);iqr=q3-q1
            fig.add_trace(go.Box(name=c,q1=[q1],median=[med],q3=[q3],lowerfence=[x[x>=q1-1.5*iqr].min()],upperfence=[x[x<=q3+1.5*iqr].max()],marker_color=COLORS[c]))
        export(name,style(fig,'Distribución real · '+key,source,values['B2'][key][1]))
    dirs=[];arrivalbins=[]
    for c,inp in inputs.items():
        for di,label in [(2,'NB'),(4,'SB')]:
            population=[r for r in inp['initial']+inp['entries'] if r['direction']==di];dirs.append(dict(Contexto=c,Dirección=label,Vehículos=len(population)))
            ts=[r['requested_time_s'] for r in inp['entries'] if r['direction']==di];edges=np.arange(0,inp['horizon_s']+30,30);count=np.histogram(ts,edges)[0]
            arrivalbins.extend(dict(Contexto=c,Dirección=label,Tiempo=float(a),Llegadas=int(n)) for a,n in zip(edges[:-1],count))
    write_table('direction_frequency.csv',pd.DataFrame(dirs),'outputs/peachtree3u/final_inputs.json;outputs/peachtree5/b1_exogenous_inputs.json')
    write_table('arrival_bins.csv',pd.DataFrame(arrivalbins),'outputs/peachtree3u/final_inputs.json;outputs/peachtree5/b1_exogenous_inputs.json')
    export('06_direction_frequency.png',style(px.bar(pd.DataFrame(dirs),x='Dirección',y='Vehículos',color='Contexto',barmode='group',color_discrete_map=COLORS),'Demanda Through modelada por dirección','outputs/peachtree3u/final_inputs.json;outputs/peachtree5/b1_exogenous_inputs.json','vehículos'))
    export('06_arrivals.png',style(px.line(pd.DataFrame(arrivalbins),x='Tiempo',y='Llegadas',color='Contexto',line_dash='Dirección',color_discrete_map=COLORS),'Llegadas solicitadas en intervalos30s','outputs/peachtree3u/final_inputs.json;outputs/peachtree5/b1_exogenous_inputs.json','vehículos /30s'))
    refs=f['structure']['signal_control_references'];bounds=f['structure']['boundaries']
    fig=go.Figure()
    fig.add_shape(type='rect',x0=400,x1=1400,y0=.5,y1=4.5,fillcolor='#E4EAF3',line_width=0)
    for y in [1.5,3.5]:fig.add_shape(type='line',x0=400,x1=1400,y0=y,y1=y,line=dict(color='white',dash='dash',width=3))
    fig.add_shape(type='line',x0=400,x1=1400,y0=2.5,y1=2.5,line=dict(color='#C9A457',width=4))
    for i,street in [(2,'11th'),(3,'12th')]:
        center=(refs[f'{i}/2']+refs[f'{i}/4'])/2
        fig.add_annotation(x=center,y=5.15,text='<b>'+street+' Street</b>',showarrow=False,font=dict(size=25))
        for di,low,high in [(2,.5,2.5),(4,2.5,4.5)]:
            x=refs[f'{i}/{di}'];fig.add_shape(type='line',x0=x,x1=x,y0=low,y1=high,line=dict(color='#008E84',width=4))
            fig.add_annotation(x=x,y=.15 if di==2 else 4.7,text=f'{x:.3f} ft',showarrow=False,font=dict(size=18,color='#008E84'))
    for di,y,label in [(2,1,'NB'),(4,4,'SB')]:
        a=bounds['entry_ft'][str(di)];b=bounds['exit_ft'][str(di)]
        fig.add_annotation(x=b,y=y,ax=a,ay=y,axref='x',ayref='y',text=label,showarrow=True,arrowhead=3,arrowsize=1.2,arrowwidth=3,arrowcolor='#486A95',font=dict(size=22))
        fig.add_shape(type='line',x0=b,x1=b,y0=.5 if di==2 else 2.5,y1=2.5 if di==2 else 4.5,line=dict(color='#875F9A',dash='dot',width=3))
    fig.update_xaxes(title='Local_Y del frente (ft)',range=[350,1450]);fig.update_yaxes(visible=False,range=[-.5,5.7])
    export('02_problem_scope.png',style(fig,'Peachtree Street ·11th–12th · alcance congelado','outputs/peachtree3u/structural_model_freeze.json'))
    e2=read_json('outputs/peachtree6/scenario_design_freeze.json')['E2'];original_rows=int(dataset['rows'].sum())
    cards={
        '01_project_cover.png':('NGSIM Peachtree · simulación basada en agentes',[('Proyecto',TITLE),('Método','Modelo AgentPy calibrado, validado y utilizado<br>para evaluar estrategias de control semafórico'),('Presentación','Integrantes, docente y fecha configurables<br>No se atribuyen datos personales no almacenados')],'outputs/peachtree6/experiment_freeze.json;guía de presentación proporcionada'),
        '03_question_objective.png':('Pregunta de investigación y objetivo',[('Pregunta',QUESTION),('Objetivo general',OBJECTIVE)],'guía de presentación proporcionada;outputs/peachtree3u/structural_model_freeze.json'),
        '17_references.png':('Referencias y evidencias',[('Datos externos','USDOT / FHWA · NGSIM8ect-6jqj<br>Metadata Peachtree · signal TXT'),('Implementación','AgentPy · documentación del paquete<br>IDM · referencia utilizada en criterios'),('Evidencias del proyecto','Datos · código · tests<br>Calibration / validation / experiment freezes<br>Streamlit y figuras exportables')],'presentation_assets/tables/references.csv'),
        '04_agents_environment.png':('VehicleAgent · atributos, estados e interacciones',[('Atributos','id · clase · longitud · ancho<br>dirección · carril · posición<br>velocidad · aceleración · líder<br>entrada · salida'),('Estados','ENTERING · FREE_FLOW · FOLLOWING<br>STOPPED_SIGNAL · LANE_CHANGING · EXITED'),('Interacciones','vehículo ↔ vehículo<br>vehículo ↔ señal<br>vehículo ↔ carril / entorno'),('Entorno','11th / 12th · carriles<br>controles efectivos · boundaries<br>horarios de señal')],'simulation/agents.py;outputs/peachtree3u/structural_model_freeze.json'),
        '05_dataset_evidence.png':('NGSIM · evidencia de datos externos',[('Fuente','USDOT / FHWA<br>Peachtree Street, Atlanta<br>Dataset8ect-6jqj'),('Adquisición',f'{original_rows:,} filas originales<br>10Hz · dt0,1s<br>B2 TRAIN · B1 VALIDATION'),('Evidencia local','peachtree_full.csv · API Socrata<br>Metadata oficial y signal TXT<br>Condiciones: consultar fuente USDOT')],'scripts/download_peachtree.py;outputs/peachtree_acquisition_timing.csv'),
        '07_conceptual_model.png':('Modelo conceptual · evolución individual',[('Entrada','Arrival → ENTERING<br>FIFO e inserción segura'),('Movimiento','FREE_FLOW / FOLLOWING<br>IDM + líder simulado / virtual'),('Control y cola','Señal → detención → cola<br>GREEN → release → continuar'),('Salida y medición','EXITED · conservación<br>Metrics Collector · resultados')],'simulation/model.py;simulation/agents.py;outputs/peachtree3u/structural_model_freeze.json'),
        '08_agentpy_architecture.png':('Python y AgentPy · arquitectura',[('Datos y preparación','data/ + scripts de preparación<br>entradas exógenas y snapshot'),('AgentPy model','VehicleAgent · SignalController<br>DemandStream · Environment · Metrics'),('Reloj físico','1 tick =0,1s simulados<br>IDM congelado · sin replay'),('Resultados y Streamlit','Artefactos oficiales → dashboard<br>La UI consume estados AgentPy')],'simulation/model.py;simulation/metrics.py;ui/canvas_renderer.py'),
        '11_scenarios.png':('BASE y exactamente tres alternativas',[('BASE','Horario observado propio de B1/B2'),('E1 · Green Split','+10% nominal GREEN Through<br>Menos RED · mismo ciclo / amarillo'),('E2 · Coordinación',f'{e2["DOMINANT_PROGRESSION_DIRECTION"]} dominante ·12th →11th<br>Tiempo{e2["PROGRESSION_TRAVEL_TIME"]:.2f}s<br>Desplazamiento{e2["OFFSET_SHIFT_SECONDS"]:.2f}s'),('E3 · Combinación','E1 + exactamente el mismo E2<br>Sin rediseñar el offset')],'outputs/peachtree6/scenario_design_freeze.json'),
        '14_final_decision.png':('RECOMMENDED WITHIN SCOPE · '+f['experiment']['recommended_alternative'],[('Robustez','Mejora travel y stopping en B1/B2<br>Beneficia NB y SB'),('Pareto y evidencia','E1 domina BASE en ambos contextos<br>Efectos pareados y score congelado'),('Por qué no E2/E3','Mejoran B2, empeoran B1<br>La coordinación depende del contexto')],'outputs/peachtree6/experiment_freeze.json;outputs/peachtree6/pareto_analysis.csv'),
        '15_limitations.png':('Limitaciones visibles',[('Sesgos del modelo','Headway alto · pocos stop episodes<br>Detenciones completas largas<br>Discrepancia de distribución B1'),('Alcance','Through clases2/3 · target-only<br>Giros / flujos locales omitidos<br>Receiving libre'),('Interpretación','Demanda cerrada ≠ capacidad<br>Queues con contexto diferente<br>No es un plan listo para campo')],'outputs/peachtree5/validation_freeze.json'),
        '16_conclusions.png':('Conclusiones',[('1 · Modelo útil con límites','AgentPy reproduce patrones generales<br>de otra adquisición real, con sesgos'),('2 · E1 consistente','El green split reduce travel y stopping<br>en B1 y B2'),('3 · Coordinación sensible','E2/E3 no generalizan igual en B1<br>E1 es la más robusta de las evaluadas')],'outputs/peachtree5/validation_freeze.json;outputs/peachtree6/experiment_freeze.json')}
    for name,(title,blocks,source) in cards.items():export(name,card_figure(title,blocks,source))
    cal=read_csv('outputs/peachtree4/pre_vs_post_calibration.csv');sel=['speed_mean_ft_s','headway_mean_ft','travel_mean_s','operational_stopped','throughput_temporal_L1_normalized','section_travel_mean_s'];cal=cal[cal.metric.isin(sel)]
    long=cal.melt(id_vars='metric',value_vars=['REAL_B2','PRECALIBRATION','FINAL_CALIBRATED'],var_name='Serie',value_name='Valor')
    export('09_calibration.png',compare_plot(cal,sel,['REAL_B2','PRECALIBRATION','FINAL_CALIBRATED'],'Calibración B2 · magnitud y tradeoffs','outputs/peachtree4/pre_vs_post_calibration.csv'))
    val=read_csv('outputs/peachtree5/train_vs_validation.csv');val=val[val.metric.isin(sel[:4])];long=val.melt(id_vars='metric',value_vars=['VALIDATION_REAL_B1','VALIDATION_SIM_B1'],var_name='Serie',value_name='Valor')
    export('10_validation.png',compare_plot(val,sel[:4],['VALIDATION_REAL_B1','VALIDATION_SIM_B1'],'Validación B1 · compatibilidad y limitaciones','outputs/peachtree5/train_vs_validation.csv'))
    export('11_signal_timeline.png',timeline())
    for file,key in [('12_travel_comparison.png','travel_mean_s'),('12_stopping_comparison.png','operational_stopped')]:export(file,scenario_chart('B1+B2',key))
    data=scenario_table('B2');data=data.drop(columns=['Cola media (vehículos)']);headers=[c.replace(' (','<br>(').replace(' por vehículo','<br>por vehículo') for c in data.columns]
    fig=go.Figure(go.Table(columnwidth=[100]+[235]*(len(data.columns)-1),header=dict(values=headers,fill_color='#D9E2EF',height=90),cells=dict(values=[data[c].round(2) if pd.api.types.is_numeric_dtype(data[c]) else data[c] for c in data],height=65)))
    export('12_scenario_table.png',style(fig,'Resultados B2 · medias30 réplicas','outputs/peachtree6/b2_scenario_summary.csv'))
    export('12_directional_results.png',directional_chart('B1+B2'))
    export('13_space_time_base.png',space_time(mode='BASE'));export('13_space_time_e1.png',space_time(mode='E1'))
    emergence=read_csv('outputs/peachtree6/emergent_behavior.csv').groupby(['context','scenario'])[['RED_queue_mean','GREEN_queue_mean','peak_active','vehicles_multiple_stops']].mean().reset_index()
    export('13_emergent_behavior.png',style(px.bar(emergence.melt(id_vars=['context','scenario'],var_name='Indicador',value_name='Valor'),x='scenario',y='Valor',color='context',facet_col='Indicador',facet_col_wrap=2,barmode='group',color_discrete_map=COLORS),'Comportamiento colectivo · evidencia cuantitativa','outputs/peachtree6/emergent_behavior.csv','Unidades según indicador'))
    export('14_paired_effects.png',paired_chart())
    robust=read_csv('outputs/peachtree6/robustness_summary.csv');rb=robust[robust.metric.eq('travel_mean_s')].melt(id_vars='scenario',value_vars=['B2_effect','B1_effect'],var_name='Contexto',value_name='Efecto')
    export('14_robustness.png',style(px.bar(rb,x='scenario',y='Efecto',color='Contexto',barmode='group'),'Robustez de travel · negativo=mejora','outputs/peachtree6/robustness_summary.csv','s (E−BASE)'))
    manifest()
    # Keep future full asset builds consistent with the shared static-reading UI.
    from scripts.refresh_presentation_charts import main as refresh_charts
    refresh_charts()

def compare_plot(data,keys,series,title,source):
    names=[METRICS.get(k,(k,'índice normalizado')) for k in keys]
    fig=make_subplots(rows=2,cols=3 if len(keys)>4 else 2,subplot_titles=[n+' ('+u+')' for n,u in names])
    cols=3 if len(keys)>4 else 2
    for j,key in enumerate(keys):
        row=data[data.metric.eq(key)].iloc[0];factor=100 if names[j][1]=='%' else 1
        for k,serie in enumerate(series):
            label=serie.replace('VALIDATION_','').replace('PRECALIBRATION','PRE').replace('FINAL_CALIBRATED','FINAL').replace('_',' ')
            fig.add_trace(go.Bar(x=[label],y=[row[serie]*factor],name=label,showlegend=j==0,marker_color=['#9AAABE','#875F9A','#008E84'][k]),row=j//cols+1,col=j%cols+1)
    result=style(fig,title,source);result.update_layout(legend=dict(y=1.15),margin=dict(t=150));return result

def manifest():
    names=['Portada','Fenómeno real y problema','Pregunta y objetivo','Agentes y entorno','Obtención de datos','Datos y estadística','Modelo conceptual','Implementación AgentPy','Calibración y verificación','Validación','Tres escenarios','Resultados','Comportamiento emergente','Decisión','Limitaciones y supuestos','Conclusiones','Referencias y evidencias']
    mapping={1:('Proyecto','01_project_cover.png','dataset_summary.csv'),2:('Proyecto','02_problem_scope.png','dataset_summary.csv'),3:('Proyecto','03_question_objective.png','decision_summary.csv'),4:('Modelo','04_agents_environment.png','component_provenance.csv'),5:('Datos','05_dataset_evidence.png','dataset_summary.csv'),6:('Datos','06_speed_distribution.png','descriptive_statistics.csv'),7:('Modelo','07_conceptual_model.png','component_provenance.csv'),8:('Modelo','08_agentpy_architecture.png','model_parameters.csv'),9:('Calibración','09_calibration.png','calibration_pre_post.csv'),10:('Validación','10_validation.png','validation_real_sim.csv'),11:('Escenarios','11_scenarios.png','decision_summary.csv'),12:('Resultados','12_travel_comparison.png','scenario_results_B2.csv'),13:('Comportamiento emergente','13_emergent_behavior.png','directional_results.csv'),14:('Decisión','14_final_decision.png','paired_effects.csv'),15:('Limitaciones','15_limitations.png','component_provenance.csv'),16:('Decisión','16_conclusions.png','decision_summary.csv'),17:('Material para presentación','17_references.png','references.csv')}
    messages={1:TITLE,2:'Vehículos y señales generan colas y variaciones de desempeño.',3:QUESTION,4:'El comportamiento colectivo surge de interacciones locales.',5:'Datos externos USDOT documentados, no datos sintéticos.',6:'Describir observaciones separadas por adquisición, con unidades y población.',7:'IDM, señales y FIFO producen movimiento, detención y descarga.',8:'AgentPy integra a0,1s; Streamlit visualiza sus estados.',9:'B2 es TRAIN: parámetros calibrados y luego congelados.',10:'B1 generaliza con limitaciones, no es fully unseen validation.',11:'Exactamente tres alternativas predeclaradas, sin optimización.',12:'Comparar SIM alternativas frente a SIM BASE en ambos contextos.',13:'Colas, acumulación y descarga son patrones emergentes cuantificables.',14:'E1 es la alternativa robusta dentro del alcance evaluado.',15:'Sesgos y omisiones limitan la interpretación absoluta y de campo.',16:'Modelo útil con límites; E1 consistente; coordinación sensible al contexto.',17:'Referencias y freezes permiten rastrear cada evidencia.'}
    rows=[]
    for n,title in enumerate(names,1):
        section,fig,tab=mapping[n];source=read_json('presentation_assets/charts/'+Path(fig).stem+'.json')['layout']['meta']['source_artifact']
        rows.append(dict(slide_number=n,section=section,recommended_title=title,main_message=messages[n],data_source=source,metrics=list(table(tab).columns),
            figure_file=fig,table_file='tables/'+tab,limitations=freezes()['validation']['limitations'],speaker_note_summary=messages[n]))
    (ASSETS/'presentation_manifest.json').write_text(json.dumps({'coverage':'ALL 17 PRESENTATION REQUIREMENTS COVERED','slides':rows,'scientific_results_unchanged':True},indent=2),encoding='utf-8')
    with zipfile.ZipFile(ASSETS/'presentation_material.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in ASSETS.rglob('*'):
            if path.is_file() and path.suffix!='.zip' and path.name!='pre_presentation_integrity.json':archive.write(path,path.relative_to(ASSETS))

if __name__=='__main__':build()
