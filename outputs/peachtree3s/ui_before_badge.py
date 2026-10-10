"""Read-only TRAIN dashboard. No dynamics, calibration, or TEST loading here."""
import json,uuid
import pandas as pd
import plotly.express as px
import streamlit as st
from simulation.training_data import ROOT,load_inputs,require_train
from simulation.parameters import IDMParameters
from simulation.model import run_baseline
from .canvas_renderer import render_canvas

def chart(fig):
    fig.update_layout(template='plotly_dark',paper_bgcolor='#0c1422',plot_bgcolor='#0c1422',font_color='#b9c8db',margin=dict(l=10,r=10,t=42,b=10),legend_title_text='',height=290)
    st.plotly_chart(fig,width='stretch',config={'displayModeBar':False})

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
    .stApp{background:#0c1422;color:#dbe4f0} [data-testid="stSidebar"]{background:#101b2b;border-right:1px solid #23334b}
    .block-container{padding-top:2rem;max-width:1450px} h1{font-size:2rem!important;letter-spacing:-.8px} h3{font-size:1.1rem!important}
    .eyebrow{font-size:11px;letter-spacing:2px;color:#6b859f;margin-bottom:8px}.subtitle{color:#91a4bb;font-size:14px;line-height:1.8}
    .badge{display:inline-block;background:#113c3b;color:#5eead4;border:1px solid #236461;padding:5px 12px;border-radius:6px;font-size:11px;letter-spacing:.6px;margin-right:8px}.locked{background:#253044;color:#b7c5d8;border-color:#394a62}
    [data-testid="stMetric"]{background:#142237;border:1px solid #25364e;border-radius:10px;padding:15px}
    </style>''')
    st.html('<div class="eyebrow">LABORATORIO DE MOVILIDAD URBANA / PEACHTREE-3</div><h1>NGSIM PEACHTREE</h1><div class="subtitle">Simulación basada en agentes de tráfico urbano<br>Subcorredor 11th–12th Street · AgentPy · Datos reales NGSIM</div><p><span class="badge">BASELINE — TRAIN B2</span><span class="badge locked">TEST LOCKED</span></p>')
    path=ROOT/'outputs/b2_calibrated_parameters.json'
    if not path.exists():st.info('Calibración B2 en ejecución. Los resultados aparecerán al finalizar.');return
    revision_folder=ROOT/'outputs/peachtree3r'
    available=(revision_folder/'revised_trace.json').exists() and (revision_folder/'old_vs_revised.csv').exists()
    version=st.sidebar.selectbox('Versión del baseline',['REVISED_BASELINE','OLD_BASELINE'] if available else ['OLD_BASELINE'])
    if version=='REVISED_BASELINE':path=revision_folder/'revised_parameters.json'
    params=json.loads(path.read_text());require_train(params['training_acquisition'])
    state=st.session_state
    trace_path=revision_folder/'revised_trace.json' if version=='REVISED_BASELINE' else ROOT/'outputs/b2_reference_trace.json'
    artifact_stamp=trace_path.stat().st_mtime_ns
    if 'trace' not in state or state.get('version')!=version or state.get('artifact_stamp')!=artifact_stamp:
        state.trace=json.loads(trace_path.read_text());state.run_id=str(uuid.uuid4());state.playing=False;state.reset=False;state.version=version
        state.artifact_stamp=artifact_stamp
    st.caption('UI_IMPLEMENTED_NOT_BROWSER_VALIDATED · PEACHTREE-3R TRAIN ONLY' if available else 'UI_IMPLEMENTED_NOT_BROWSER_VALIDATED')
    with st.sidebar:
        st.markdown('### Control de ejecución')
        seed=st.number_input('Seed',min_value=0,max_value=2147483647,value=210 if version=='REVISED_BASELINE' else 10,step=1,key='seed_'+version)
        speed=st.slider('Velocidad de reproducción visual',1.,32.,8.,1.,format='%gx')
        st.caption('Reproducción visual. Física fija: Δt = 0,1 s.')
        st.selectbox('Modelo',['BASELINE'])
        if st.button('Run',type='primary',width='stretch'):
            if state.trace['seed']!=seed:
                with st.spinner('Ejecutando AgentPy con parámetros calibrados…'):
                    run_inputs=json.loads((revision_folder/'revised_inputs.json').read_text()) if version=='REVISED_BASELINE' else load_inputs()
                    require_train(run_inputs['acquisition_id'])
                    model=run_baseline(run_inputs,IDMParameters(**params['parameters']),seed=int(seed),trace=True,queue_gap=params['queue_gap_m'])
                state.trace={'training_acquisition':'B2','seed':int(seed),'frames':model.recorder.traces,'network':load_inputs()['network'],'summary':model.summary}
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
        for name in ['E1','E2','E3']:st.button(name,disabled=True,width='stretch')
        st.caption('Disponibles después de validación del modelo base')
        st.divider();st.caption('TRAIN — CALIBRATION/DEVELOPMENT\n\nTEST = B1 · LOCKED')
    overview,data_tab,diagnosis,method=st.tabs(['Corredor y dinámica','Datos reales vs simulación — TRAIN','Diagnóstico estructural','Diseño y verificación'])
    with overview:
        st.html(render_canvas(state.trace,state.run_id,state.playing,speed,state.reset),unsafe_allow_javascript=True);state.reset=False
        st.caption(f'Seed {state.trace["seed"]} · {len(state.trace["frames"]):,} snapshots simulados · Interpolación de Canvas entre snapshots · Δt físico 0,1 s')
        times=pd.DataFrame([f['metrics'] for f in state.trace['frames']])
        left,right=st.columns(2)
        with left:chart(px.line(times,x='simulation_time',y='mean_speed_ft_s',title='Velocidad colectiva · ft/s',color_discrete_sequence=['#5eead4']))
        with right:chart(px.line(times,x='simulation_time',y='vehicles_active',title='Acumulación de vehículos',color_discrete_sequence=['#a5b4fc']))
        left,right=st.columns(2)
        with left:chart(px.line(times,x='simulation_time',y=['stopped_vehicles','queue_proxy_vehicles'],title='Formación y disolución de colas',color_discrete_sequence=['#fbbf24','#fb7185']))
        with right:chart(px.line(times,x='simulation_time',y='throughput_cumulative',title='Throughput acumulado · cruces de salida',color_discrete_sequence=['#5eead4']))
        left,right=st.columns(2)
        with left:chart(px.line(times,x='simulation_time',y='stopped_fraction',title='Fracción detenida',color_discrete_sequence=['#fbbf24']))
        with right:chart(px.line(times,x='simulation_time',y='travel_time_mean_s',title='Travel time medio acumulado · s',color_discrete_sequence=['#a5b4fc']))
    with data_tab:
        st.markdown('### TRAIN — CALIBRATION/DEVELOPMENT')
        st.markdown('#### OLD_BASELINE · Resultados originales conservados')
        st.caption('Comparación de referencia con seed 10 fijada antes de calibrar. Las 30 réplicas están resumidas por separado. Estos gráficos no validan el modelo.')
        compare=read_csv('b2_real_vs_simulated.csv');st.dataframe(compare[['indicator','unit','real_mean','simulated_mean','ks','wasserstein']],hide_index=True,width='stretch')
        dist=read_csv('b2_distributions.csv');left,right=st.columns(2)
        with left:chart(px.line(dist[dist.indicator=='speed'],x='value',y='probability',color='series',title='Distribución de velocidad · ft/s',color_discrete_sequence=['#5eead4','#a5b4fc']))
        with right:chart(px.line(dist[dist.indicator=='headway'],x='value',y='probability',color='series',title='Headway front-to-front · ft',color_discrete_sequence=['#5eead4','#a5b4fc']))
        left,right=st.columns(2)
        with left:chart(px.line(dist[dist.indicator=='travel_time'],x='value',y='probability',color='series',title='Travel time cut-to-cut · s',color_discrete_sequence=['#5eead4','#a5b4fc']))
        with right:chart(px.line(read_csv('b2_throughput_bins.csv'),x='time',y=['real_exits','simulated_exits'],title='Throughput temporal · salidas / 30 s',color_discrete_sequence=['#5eead4','#a5b4fc']))
        observed=read_csv('b2_observed_timeseries.csv');sim=read_csv('b2_baseline_timeseries.csv')
        def grouped(d,label):
            d=d.copy();d['time']=(d.simulation_time//30)*30
            q=d.groupby('time')[['mean_speed_ft_s','stopped_fraction']].mean().reset_index();q['series']=label;return q
        joined=pd.concat([grouped(observed,'B2 real'),grouped(sim,'AgentPy')])
        left,right=st.columns(2)
        with left:chart(px.line(joined,x='time',y='mean_speed_ft_s',color='series',title='Velocidad temporal · promedios 30 s',color_discrete_sequence=['#5eead4','#a5b4fc']))
        with right:chart(px.line(joined,x='time',y='stopped_fraction',color='series',title='Fracción detenida temporal',color_discrete_sequence=['#5eead4','#a5b4fc']))
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
            chart(px.line(q[q.signal==selected],x='time',y='queue',color='series',title='Queue operacional · TARGET y contexto arterial observado',color_discrete_map={'REAL_B2':'#5eead4','OLD_BASELINE':'#a5b4fc','REVISED_BASELINE':'#fbbf24','REAL_B2_ALL_OBSERVED_ARTERIAL':'#fb7185'}))
            st.dataframe(read_revision_csv('queue_real_vs_sim.csv'),hide_index=True,width='stretch')
            st.markdown('### Episodios de detención')
            st.dataframe(read_revision_csv('stop_episode_real_vs_sim.csv'),hide_index=True,width='stretch')
            episodes=read_revision_csv('stop_episodes_detail.csv')
            chart(px.ecdf(episodes[~episodes.left_censored&~episodes.right_censored],x='duration_s',color='series',title='Duración de episodios completos · s',color_discrete_sequence=['#5eead4','#a5b4fc','#fbbf24']))
            st.markdown('### Estado semafórico y detención condicionada')
            st.dataframe(read_revision_csv('signal_conditioned_stopping.csv'),hide_index=True,width='stretch')
            st.markdown('### Evidencia y causas')
            st.dataframe(read_revision_csv('cause_ranking.csv'),hide_index=True,width='stretch')
        else:st.caption('Diagnóstico estructural pendiente de exportación.')
    with method:
        st.markdown('### Alcance y reglas')
        st.write('Arterial Through, clases 2/3, Local_Y 400–1400 ft. Señales NB/SB observadas de 11th y 12th. IDM agrupado; demanda B2 exógena; una sola condición inicial; evolución posterior simulada por AgentPy.')
        st.warning('Geometría esquemática, stop bars aproximadas por mouths observados. Flujos locales/giros omitidos. Cambios discrecionales simplificados por muestra escasa. La animación no sustituye evidencia numérica.')
        decision=revision_folder/'decision.json' if available else ROOT/'outputs/b2_baseline_decision.json'
        if decision.exists():
            report=json.loads(decision.read_text());st.write(report['classification']);st.write(report['reason'])
        st.info('TEST = B1 · LOCKED. La futura fase debe denominarse TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.')
        st.code('python -m scripts.run_train_tests\npython -m streamlit run streamlit_app.py',language='bash')

if __name__=='__main__':main()
