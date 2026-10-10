"""Read-only TRAIN dashboard. No dynamics, calibration, or TEST loading here."""
import json,uuid
import pandas as pd
import plotly.express as px
import streamlit as st
from simulation.training_data import ROOT,load_inputs,require_train
from simulation.parameters import IDMParameters
from simulation.model import run_baseline
from .canvas_renderer import render_canvas

def chart(fig,context='B2',source=None):
    fig.update_layout(template='plotly_white',paper_bgcolor='#ffffff',plot_bgcolor='#ffffff',font_color='#102a43',margin=dict(l=10,r=10,t=42,b=10),legend_title_text='',height=290)
    from ui.technical_chart_labels import annotate_technical
    if source is None:
        title=fig.layout.title.text or ''
        source=('outputs/peachtree3r/stop_episodes_detail.csv' if 'episodios completos' in title else
            'outputs/peachtree3r/queue_timeseries.csv' if 'Queue operacional' in title else
            'outputs/b2_observed_timeseries.csv; outputs/b2_baseline_timeseries.csv' if 'temporal' in title and 'Throughput' not in title else
            'outputs/b2_throughput_bins.csv' if 'Throughput temporal' in title else 'outputs/b2_distributions.csv')
    fig=annotate_technical(fig,context,source)
    st.plotly_chart(fig,width='stretch',theme=None,config={'displayModeBar':False})

def read_csv(name):
    if not name.startswith('b2_'):raise PermissionError('TEST LOCKED')
    return pd.read_csv(ROOT/'outputs'/name)

def read_revision_csv(name):
    allowed={'old_vs_revised.csv','queue_real_vs_sim.csv','queue_timeseries.csv','stop_episode_real_vs_sim.csv','stop_episodes_detail.csv',
        'cause_ranking.csv','signal_conditioned_stopping.csv','revised_30_replica_summary.csv','temporal_speed_comparison.csv','temporal_throughput_comparison.csv','paired_old_vs_revised.csv'}
    if name not in allowed:raise PermissionError('TEST LOCKED: only predefined B2 revision exports')
    return pd.read_csv(ROOT/'outputs/peachtree3r'/name)

def main():
    require_train('B2')
    st.set_page_config(page_title='NGSIM Peachtree · AgentPy',page_icon='◈',layout='wide')
    st.html('''<style>
    .stApp{background:#ffffff;color:#102a43} [data-testid="stSidebar"]{background:#f4f7fb;border-right:1px solid #d9e2ef}
    .block-container{padding-top:4.5rem;max-width:1450px} h1{font-size:2rem!important;letter-spacing:-.8px} h3{font-size:1.1rem!important}
    .eyebrow{font-size:11px;letter-spacing:2px;color:#52667a;margin-bottom:8px}.subtitle{color:#52667a;font-size:14px;line-height:1.8}
    .badge{display:inline-block;background:#e2f3ef;color:#007f73;border:1px solid #9fcfc4;padding:5px 12px;border-radius:6px;font-size:11px;letter-spacing:.6px;margin-right:8px}.locked{background:#eef2f7;color:#40566e;border-color:#cbd5e1}
    [data-testid="stMetric"]{background:#ffffff;border:1px solid #d9e2ef;border-radius:10px;padding:15px}
    </style>''')
    st.html('<div class="eyebrow">LABORATORIO DE MOVILIDAD URBANA / PEACHTREE-3</div><h1>NGSIM PEACHTREE</h1><div class="subtitle">Simulación basada en agentes de tráfico urbano<br>Subcorredor 11th–12th Street · AgentPy · Datos reales NGSIM</div><p><span class="badge">BASELINE — TRAIN B2</span><span class="badge locked">TEST LOCKED</span></p>')
    if (ROOT/'outputs/peachtree3s/decision.json').exists():
        st.html('<span class="badge">STRUCTURAL REVISION — TRAIN B2</span>')
    path=ROOT/'outputs/b2_calibrated_parameters.json'
    if not path.exists():st.info('Calibración B2 en ejecución. Los resultados aparecerán al finalizar.');return
    revision_folder=ROOT/'outputs/peachtree3r'
    available=(revision_folder/'revised_trace.json').exists() and (revision_folder/'old_vs_revised.csv').exists()
    choices=['REVISED_BASELINE','OLD_BASELINE'] if available else ['OLD_BASELINE']
    if (ROOT/'outputs/peachtree3t/control_envelope_trace.json').exists():choices+=['NEW_REDUCED_SCOPE','CONTROL_ENVELOPE_REVISION']
    if (ROOT/'outputs/peachtree3u/final_structure_trace.json').exists():choices+=['FINAL_STRUCTURE']
    if (ROOT/'outputs/peachtree4/final_calibrated_trace.json').exists():choices+=['FINAL_CALIBRATED_B2']
    if (ROOT/'outputs/peachtree6/experiment_freeze.json').exists():choices+=['SCENARIO_EXPERIMENTATION']
    default_version=choices.index('FINAL_CALIBRATED_B2') if 'FINAL_CALIBRATED_B2' in choices else 0
    if 'technical_version' not in st.session_state:st.session_state['technical_version']=choices[default_version]
    version=st.sidebar.selectbox('Versión del baseline',choices,key='technical_version')
    if version=='REVISED_BASELINE':path=revision_folder/'revised_parameters.json'
    params=json.loads(path.read_text());require_train(params['training_acquisition'])
    scenario_mode=version=='SCENARIO_EXPERIMENTATION'
    scenario_labels={'Baseline actual':'BASE','E1 — Green Split':'E1','E2 — Coordinación semafórica':'E2','E3 — Combinación':'E3'}
    selected_scenario='BASE';selected_context='B2'
    if scenario_mode:
        selected_context=st.sidebar.selectbox('Contexto',['B2','B1'])
        selected_scenario=scenario_labels[st.sidebar.selectbox('Escenario',list(scenario_labels),key='scenario_selector')]
        st.html('<span class="badge">BASELINE VALIDATED WITH LIMITATIONS</span><span class="badge">SCENARIO EXPERIMENTATION</span>')
    if version in ['FINAL_CALIBRATED_B2','SCENARIO_EXPERIMENTATION']:
        from calibration.final_calibration import final_parameters
        frozen_structure=json.loads((ROOT/'outputs/peachtree3u/structural_model_freeze.json').read_text())
        params={'training_acquisition':'B2','parameters':dict(final_parameters(),delta=4.),'queue_gap_m':frozen_structure['queue_gap_m']}
        st.html('<span class="badge">BASELINE CALIBRATED — TRAIN B2</span>')
    state=st.session_state
    trace_path=revision_folder/'revised_trace.json' if version=='REVISED_BASELINE' else ROOT/'outputs/b2_reference_trace.json'
    if version in ['NEW_REDUCED_SCOPE','CONTROL_ENVELOPE_REVISION']:
        trace_path=ROOT/'outputs/peachtree3t/control_envelope_trace.json'
    if version=='FINAL_STRUCTURE':trace_path=ROOT/'outputs/peachtree3u/final_structure_trace.json'
    if version=='FINAL_CALIBRATED_B2':trace_path=ROOT/'outputs/peachtree4/final_calibrated_trace.json'
    if scenario_mode:trace_path=ROOT/'outputs/peachtree6/traces'/f'{selected_context}_{selected_scenario}_7000.json'
    view_identity=version+(':'+selected_context+':'+selected_scenario if scenario_mode else '')
    artifact_stamp=trace_path.stat().st_mtime_ns
    if 'trace' not in state or state.get('version')!=view_identity or state.get('artifact_stamp')!=artifact_stamp:
        state.trace=json.loads(trace_path.read_text());state.run_id=str(uuid.uuid4());state.playing=False;state.reset=False;state.version=view_identity
        state.artifact_stamp=artifact_stamp
    st.caption('UI_IMPLEMENTED_NOT_BROWSER_VALIDATED · PEACHTREE-4 TRAIN ONLY' if version=='FINAL_CALIBRATED_B2' else 'UI_IMPLEMENTED_NOT_BROWSER_VALIDATED · PEACHTREE-3U TRAIN ONLY' if version=='FINAL_STRUCTURE' else 'UI_IMPLEMENTED_NOT_BROWSER_VALIDATED · PEACHTREE-3R TRAIN ONLY' if available else 'UI_IMPLEMENTED_NOT_BROWSER_VALIDATED')
    with st.sidebar:
        st.markdown('### Control de ejecución')
        seed=st.number_input('Seed',min_value=0,max_value=2147483647,value=7000 if scenario_mode else 4000 if version=='FINAL_CALIBRATED_B2' else 210 if version=='REVISED_BASELINE' else 10,step=1,key='seed_'+version)
        speed=st.slider('Velocidad de reproducción visual',1.,32.,8.,1.,format='%gx')
        st.caption('Reproducción visual. Física fija: Δt = 0,1 s.')
        show_envelopes=st.checkbox('Show control envelopes',value=False)
        show_heads=st.checkbox('Show queue heads',value=False)
        show_effective=st.checkbox('Show effective control references',value=False)
        show_progression=st.checkbox('Show progression',value=False,disabled=not(scenario_mode and selected_scenario in ['E2','E3']))
        if version=='FINAL_STRUCTURE':st.caption('FINAL_STRUCTURE · EFFECTIVE_SIGNAL_CONTROL_REFERENCE · TRAIN B2 · FROZEN')
        if version=='FINAL_CALIBRATED_B2':st.caption('Structure FROZEN · Parameters FROZEN · TRAIN B2 only')
        if version=='CONTROL_ENVELOPE_REVISION':st.caption('Measurement/association revision only. Physical references unresolved; NOT FROZEN.')
        st.selectbox('Modelo',['BASELINE'])
        if st.button('Run',type='primary',width='stretch'):
            if state.trace['seed']!=seed or scenario_mode:
                with st.spinner('Ejecutando AgentPy con parámetros calibrados…'):
                    run_inputs=json.loads((revision_folder/'revised_inputs.json').read_text()) if version=='REVISED_BASELINE' else load_inputs()
                    require_train(run_inputs['acquisition_id'])
                    if scenario_mode:
                        from scripts.finish_peachtree6 import trace_for
                        state.trace=trace_for(selected_context,selected_scenario,int(seed));model=None
                    elif version in ['NEW_REDUCED_SCOPE','CONTROL_ENVELOPE_REVISION']:
                        from scripts.finish_peachtree3t import trace_for
                        state.trace=trace_for(int(seed));model=None
                    elif version=='FINAL_STRUCTURE':
                        from scripts.finish_peachtree3u import trace_for
                        state.trace=trace_for(int(seed));model=None
                    elif version=='FINAL_CALIBRATED_B2':
                        from scripts.finish_peachtree4 import trace_for
                        state.trace=trace_for(int(seed));model=None
                    else:model=run_baseline(run_inputs,IDMParameters(**params['parameters']),seed=int(seed),trace=True,queue_gap=params['queue_gap_m'])
                if model is not None:state.trace={'training_acquisition':'B2','seed':int(seed),'frames':model.recorder.traces,'network':load_inputs()['network'],'summary':model.summary}
                state.run_id=str(uuid.uuid4());state.reset=True
            state.playing=True
        col1,col2=st.columns(2)
        if col1.button('Pause',width='stretch'):state.playing=False
        if col2.button('Reset',width='stretch'):state.playing=False;state.reset=True;state.run_id=str(uuid.uuid4())
        st.markdown('### Parámetros calibrados')
        st.caption('READ ONLY · TRAIN B2 · autos y pesados')
        units={'v0':'m/s','T':'s','s0':'m','a':'m/s²','b':'m/s²'}
        st.table(pd.DataFrame([{'Parámetro':n,'Valor':f'{params["parameters"][n]:.3f} {u}'} for n,u in units.items()]))
        if version=='REVISED_BASELINE':st.caption('SIGNAL_RELEASE_DELAY = 1,6 s · B2\n\nStopped operacional ≤ 0,1 m/s · Exact zero por separado')
        st.markdown('### Escenarios')
        experiment_path=ROOT/'outputs/peachtree6/experiment_freeze.json'
        experiment_complete=experiment_path.exists() and json.loads(experiment_path.read_text())['status']=='COMPLETED'
        def pick_scenario(label):
            st.session_state['technical_version']='SCENARIO_EXPERIMENTATION'
            st.session_state['scenario_selector']=label
        for label,name in list(scenario_labels.items())[1:]:
            if experiment_complete:st.button(name,disabled=False,width='stretch',on_click=pick_scenario,args=(label,))
            else:st.button(name,disabled=True,width='stretch')
        validation_path=ROOT/'outputs/peachtree5/validation_freeze.json'
        if experiment_complete:
            st.caption('E1/E2/E3 implementados y evaluados · resultados congelados. Selecciona un botón para visualizar el escenario.')
            st.caption('B2: TRAIN · B1: validación y evaluación autorizadas; excluido de calibración.')
        elif validation_path.exists() and json.loads(validation_path.read_text())['classification'].startswith(('A.','B.')):
            st.caption('E1/E2/E3 · READY FOR NEXT PHASE · No implementados ni ejecutados')
        else:st.caption('Disponibles después de validación del modelo base')
        st.divider();st.caption('B2 — CALIBRACIÓN / TRAIN\n\nB1 — VALIDACIÓN · PARÁMETROS CONGELADOS' if experiment_complete else 'TRAIN — CALIBRATION/DEVELOPMENT\n\nTEST = B1 · LOCKED')
    labels=['Corredor y dinámica','Datos reales vs simulación — TRAIN','Diagnóstico estructural','Diseño y verificación']
    if (ROOT/'outputs/peachtree5/validation_freeze.json').exists():labels+=['VALIDACIÓN']
    containers=st.tabs(labels,key='phase_tabs',on_change='rerun')
    overview,data_tab,diagnosis,method=containers[:4]
    if len(containers)>4:
        validation=containers[4]
        with validation:
            st.caption('TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE')
            if validation.open:
                result=json.loads((ROOT/'outputs/peachtree5/validation_freeze.json').read_text())
                st.info(result['classification']);st.caption('Parámetros READ ONLY · B1 solo VALIDATION · Sin recalibración')
                comparison=pd.read_csv(ROOT/'outputs/peachtree5/train_vs_validation.csv')
                selected=['speed_mean_ft_s','speed_KS','speed_W1_ft_s','headway_mean_ft','headway_KS','headway_W1_ft','travel_mean_s','travel_W1_s','operational_stopped','vehicles_stopped_fraction','stop_episodes','complete_stop_duration_mean_s','throughput_total','throughput_temporal_L1_normalized','section_travel_mean_s']
                st.dataframe(comparison[comparison.metric.isin(selected)],hide_index=True,width='stretch')
                for figure in ['validation_speed.png','validation_headway.png','validation_travel.png','validation_stopping.png','validation_throughput.png']:
                    from ui.presentation_data import ASSETS
                    st.image(str(ASSETS/('10_'+figure)))
                for limitation in result['limitations']:st.write('• '+limitation)
            else:st.caption('Selecciona esta pestaña para cargar los resultados autorizados B1.')
    with overview:
        st.iframe(render_canvas(state.trace,state.run_id,state.playing,speed,state.reset,show_envelopes,show_heads,show_effective,show_progression,light=True),height=660,alt='Simulación AgentPy del corredor Peachtree');state.reset=False
        if scenario_mode:
            spec=json.loads((ROOT/'outputs/peachtree6/scenario_design_freeze.json').read_text())
            st.caption(f'{selected_scenario}: Green +10% limitado a malla0.1s' if selected_scenario in ['E1','E3'] else f'{selected_scenario}: Green durations BASE')
            st.caption(f'Offset shift={spec["E2"]["OFFSET_SHIFT_SECONDS"]:.3f}s' if selected_scenario in ['E2','E3'] else 'Offset BASE')
            st.caption(f'Progression {spec["E2"]["DOMINANT_PROGRESSION_DIRECTION"]} · Cycle preserved Sí · Yellow preserved Sí · INTERVENTIONS EXPERIMENTAL')
            results=pd.read_csv(ROOT/f'outputs/peachtree6/{selected_context.lower()}_scenario_summary.csv')
            pivot=results.pivot(index='metric',columns='scenario',values='mean')
            st.markdown('### BASE vs escenario seleccionado · medias30 réplicas')
            cols=st.columns(3)
            for j,(key,label) in enumerate([('travel_mean_s','Travel(s)'),('operational_stopped','Stopped fraction'),('mean_stopped_time_per_vehicle_s','Stopped time/vehicle(s)'),('speed_mean_ft_s','Speed(ft/s)'),('queue_mean','Queue'),('departure_t90_s','Time90% departures(s)')]):
                base=float(pivot.loc[key,'BASE']);value=float(pivot.loc[key,selected_scenario]);delta=value-base
                cols[j%3].metric(label,f'{value:.3f}',f'{delta:+.3f} ({delta/base*100:+.2f}%)',delta_color='off')
            st.markdown('### COMPARACIÓN DE ESCENARIOS')
            st.dataframe(pivot.loc[['travel_mean_s','section_travel_mean_s','operational_stopped','vehicles_stopped_fraction','mean_stopped_time_per_vehicle_s','stop_episodes_per_vehicle','NB_travel_mean_s','SB_travel_mean_s']].reset_index(),hide_index=True,width='stretch')
        st.caption(f'Seed {state.trace["seed"]} · {len(state.trace["frames"]):,} snapshots simulados · Interpolación de Canvas entre snapshots · Δt físico 0,1 s')
        times=pd.DataFrame([f['metrics'] for f in state.trace['frames']])
        left,right=st.columns(2)
        with left:chart(px.line(times,x='simulation_time',y='mean_speed_ft_s',title='Velocidad colectiva · ft/s',color_discrete_sequence=['#007f73']),context=selected_context,source=str(trace_path.relative_to(ROOT)))
        with right:chart(px.line(times,x='simulation_time',y='vehicles_active',title='Acumulación de vehículos',color_discrete_sequence=['#7352a3']),context=selected_context,source=str(trace_path.relative_to(ROOT)))
        left,right=st.columns(2)
        with left:chart(px.line(times,x='simulation_time',y=['stopped_vehicles','queue_proxy_vehicles'],title='Formación y disolución de colas',color_discrete_sequence=['#b67a12','#c64764']),context=selected_context,source=str(trace_path.relative_to(ROOT)))
        with right:chart(px.line(times,x='simulation_time',y='throughput_cumulative',title='Throughput acumulado · cruces de salida',color_discrete_sequence=['#007f73']),context=selected_context,source=str(trace_path.relative_to(ROOT)))
        left,right=st.columns(2)
        with left:chart(px.line(times,x='simulation_time',y='stopped_fraction',title='Fracción detenida',color_discrete_sequence=['#b67a12']),context=selected_context,source=str(trace_path.relative_to(ROOT)))
        with right:chart(px.line(times,x='simulation_time',y='travel_time_mean_s',title='Travel time medio acumulado · s',color_discrete_sequence=['#7352a3']),context=selected_context,source=str(trace_path.relative_to(ROOT)))
    with data_tab:
        st.markdown('### TRAIN — CALIBRATION/DEVELOPMENT')
        st.markdown('#### OLD_BASELINE · Resultados originales conservados')
        st.caption('Comparación de referencia con seed 10 fijada antes de calibrar. Las 30 réplicas están resumidas por separado. Estos gráficos no validan el modelo.')
        compare=read_csv('b2_real_vs_simulated.csv');st.dataframe(compare[['indicator','unit','real_mean','simulated_mean','ks','wasserstein']],hide_index=True,width='stretch')
        dist=read_csv('b2_distributions.csv');left,right=st.columns(2)
        with left:chart(px.line(dist[dist.indicator=='speed'],x='value',y='probability',color='series',title='Distribución de velocidad · ft/s',color_discrete_sequence=['#007f73','#7352a3']))
        with right:chart(px.line(dist[dist.indicator=='headway'],x='value',y='probability',color='series',title='Headway front-to-front · ft',color_discrete_sequence=['#007f73','#7352a3']))
        left,right=st.columns(2)
        with left:chart(px.line(dist[dist.indicator=='travel_time'],x='value',y='probability',color='series',title='Travel time cut-to-cut · s',color_discrete_sequence=['#007f73','#7352a3']))
        with right:chart(px.line(read_csv('b2_throughput_bins.csv'),x='time',y=['real_exits','simulated_exits'],title='Throughput temporal · salidas / 30 s',color_discrete_sequence=['#007f73','#7352a3']))
        observed=read_csv('b2_observed_timeseries.csv');sim=read_csv('b2_baseline_timeseries.csv')
        def grouped(d,label):
            d=d.copy();d['time']=(d.simulation_time//30)*30
            q=d.groupby('time')[['mean_speed_ft_s','stopped_fraction']].mean().reset_index();q['series']=label;return q
        joined=pd.concat([grouped(observed,'B2 real'),grouped(sim,'AgentPy')])
        left,right=st.columns(2)
        with left:chart(px.line(joined,x='time',y='mean_speed_ft_s',color='series',title='Velocidad temporal · promedios 30 s',color_discrete_sequence=['#007f73','#7352a3']))
        with right:chart(px.line(joined,x='time',y='stopped_fraction',color='series',title='Fracción detenida temporal',color_discrete_sequence=['#007f73','#7352a3']))
        st.markdown('### 30 réplicas TRAIN · mean / SD / IC95 de media')
        st.dataframe(read_csv('b2_calibration_summary.csv')[['metric','n','mean','SD','CI95_low','CI95_high']],hide_index=True,width='stretch')
        if available:
            st.markdown('### REAL B2 / OLD / REVISED · Experimento estructural')
            st.caption('Comparación congelada de referencias OLD seed10 y REVISED seed210. No seleccionadas por aspecto o ajuste. Réplicas finales pareadas por seed3000–3029. El modelo sigue en revisión.')
            st.dataframe(read_revision_csv('old_vs_revised.csv'),hide_index=True,width='stretch')
            st.dataframe(read_revision_csv('paired_old_vs_revised.csv'),hide_index=True,width='stretch')
            st.dataframe(read_revision_csv('revised_30_replica_summary.csv'),hide_index=True,width='stretch')
    with diagnosis:
        st.markdown('### PEACHTREE-3R · TRAIN ONLY')
        st.info('UI_IMPLEMENTED_NOT_BROWSER_VALIDATED · Layout y JavaScript comprobados estáticamente; revisión visual manual pendiente.')
        if available:
            st.markdown('### Colas por intersección y dirección')
            q=read_revision_csv('queue_timeseries.csv');q['signal']=q.intersection.astype(str)+' / '+q.direction.astype(str)
            selected=st.selectbox('Señal para comparar cola',sorted(q.signal.unique()))
            chart(px.line(q[q.signal==selected],x='time',y='queue',color='series',title='Queue operacional · TARGET y contexto arterial observado',color_discrete_map={'REAL_B2':'#007f73','OLD_BASELINE':'#7352a3','REVISED_BASELINE':'#b67a12','REAL_B2_ALL_OBSERVED_ARTERIAL':'#c64764'}))
            st.dataframe(read_revision_csv('queue_real_vs_sim.csv'),hide_index=True,width='stretch')
            st.markdown('### Episodios de detención')
            st.dataframe(read_revision_csv('stop_episode_real_vs_sim.csv'),hide_index=True,width='stretch')
            episodes=read_revision_csv('stop_episodes_detail.csv')
            chart(px.ecdf(episodes[~episodes.left_censored&~episodes.right_censored],x='duration_s',color='series',title='Duración de episodios completos · s',color_discrete_sequence=['#007f73','#7352a3','#b67a12']))
            st.markdown('### Estado semafórico y detención condicionada')
            st.dataframe(read_revision_csv('signal_conditioned_stopping.csv'),hide_index=True,width='stretch')
            st.markdown('### Evidencia y causas')
            st.dataframe(read_revision_csv('cause_ranking.csv'),hide_index=True,width='stretch')
        else:st.caption('Diagnóstico estructural pendiente de exportación.')
    with method:
        st.markdown('### Alcance y reglas')
        if version in ['FINAL_STRUCTURE','FINAL_CALIBRATED_B2']:
            st.write('FINAL_STRUCTURE · TARGET Through clases2/3 · NB400→1346.452 ft; SB1400→597.878 ft · AgentPy dt0.1s · FIFO y release1.6s sin cambios.')
            st.info('EFFECTIVE_SIGNAL_CONTROL_REFERENCE = INTERSECTION_ENTRY_REFERENCE. Frontera empírica de anotación NGSIM; no representa una painted stop bar. STOP_ZONE observacional sin física.')
        else:
            st.write('Arterial Through, clases 2/3, Local_Y 400–1400 ft. Señales NB/SB observadas de 11th y 12th. IDM agrupado; demanda B2 exógena; una sola condición inicial; evolución posterior simulada por AgentPy.')
            st.warning('Geometría esquemática, stop bars aproximadas por mouths observados. Flujos locales/giros omitidos. Cambios discrecionales simplificados por muestra escasa. La animación no sustituye evidencia numérica.')
        decision=revision_folder/'decision.json' if available else ROOT/'outputs/b2_baseline_decision.json'
        if version=='FINAL_STRUCTURE':decision=ROOT/'outputs/peachtree3u/structural_model_freeze.json'
        if version=='FINAL_CALIBRATED_B2':decision=ROOT/'outputs/peachtree4/calibration_freeze.json'
        if decision.exists():
            report=json.loads(decision.read_text());st.write(report['classification']);st.write(report['reason'])
        st.info('TEST = B1 · LOCKED. La futura fase debe denominarse TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.')
        st.code('python -m scripts.run_train_tests\npython -m streamlit run streamlit_app.py',language='bash')

if __name__=='__main__':main()
