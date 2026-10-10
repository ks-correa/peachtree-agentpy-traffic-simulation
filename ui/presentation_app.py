"""Academic presentation dashboard; exclusively reads frozen artifacts/states."""
import io,json,uuid
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from ui.presentation_data import *
from ui.canvas_renderer import render_canvas

@st.cache_data
def manifest():return read_json('presentation_assets/presentation_manifest.json')

def provenance(source):
    with st.expander('Fuente y definición del dato'):
        st.caption('SOURCE ARTIFACT: '+source)

def chart(fig,asset=None):
    fig.update_layout(margin_b=210,height=max(fig.layout.height or 800,800))
    if fig.layout.showlegend is not False:fig.update_layout(legend=dict(y=1.06,yanchor='bottom',x=0))
    for annotation in fig.layout.annotations:
        if str(annotation.text).startswith('Fuente:'):annotation.y=-.28
    st.plotly_chart(fig,width='stretch',theme=None,config={'displayModeBar':False,'displaylogo':False,'toImageButtonOptions':{'format':'png','width':1920,'height':1080,'scale':1}})
    provenance(fig.layout.meta['source_artifact'])
    if asset:st.download_button('Download PNG ·16:9',(ASSETS/asset).read_bytes(),file_name=asset,mime='image/png',key='png_'+asset)

def asset(name):chart(assets_chart(Path(name).stem+'.json'),name)

def display_table(d,source,filename='datos.csv',key=None):
    shown=d.drop(columns=['source_artifact'],errors='ignore').copy()
    st.dataframe(shown.style.format(precision=2),hide_index=True,width='stretch')
    provenance(source)
    st.download_button('Download CSV',source_table(d,source).to_csv(index=False).encode('utf-8-sig'),file_name=filename,mime='text/csv',key=key or filename)

def info(title,text):st.markdown('#### '+title);st.write(text)

def project():
    st.markdown('### '+TITLE)
    st.write('Modelo AgentPy calibrado, validado y utilizado para evaluar estrategias de control semafórico')
    with st.expander('Configurar portada · datos de presentación'):
        for name in ['Integrantes','Docente','Asignatura','Fecha de presentación']:
            value=st.text_input(name,key='cover_'+name)
            if value:st.caption(name+': '+value)
        cfg={name:st.session_state.get('cover_'+name,'') for name in ['Integrantes','Docente','Asignatura','Fecha de presentación']}
        st.download_button('Download portada JSON',json.dumps(dict(title=TITLE,**cfg),ensure_ascii=False,indent=2),file_name='portada.json')
    info('Fenómeno real','Tráfico vehicular urbano Through entre11th y12th de Peachtree Street, Atlanta.')
    info('Problema','El desempeño depende de la interacción entre vehículos, colas y fases semafóricas. El green split y la coordinación pueden modificar recorridos, detenciones y colas.')
    asset('02_problem_scope.png')
    info('Pregunta de investigación',QUESTION);info('Objetivo general',OBJECTIVE)

def data():
    d=table('dataset_summary.csv');total=int(d.rows.sum());cols=st.columns(4)
    dt=freezes()['structure']['dt_s']
    for col,label,value in zip(cols,['Filas originales','Frecuencia','B2','B1'],[f'{total:,}',f'{1/dt:g} Hz','TRAIN','VALIDATION']):col.metric(label,value)
    st.write('Next Generation Simulation — NGSIM. Peachtree Street, Atlanta, Georgia. U.S. Department of Transportation / FHWA. Dataset8ect-6jqj.')
    st.link_button('Fuente oficial USDOT','https://data.transportation.gov/Automobiles/Next-Generation-Simulation-NGSIM-Vehicle-Trajectories/8ect-6jqj')
    st.caption('Condiciones de uso: consultar fuente USDOT. No se atribuye una licencia no documentada.')
    info('Evidencia de obtención','Datos externos documentados, no datos sintéticos. Descarga mediante scripts/download_peachtree.py y API Socrata; fuente local data/peachtree_full.csv. Señales TXT observadas y documentación oficial auxiliar.')
    with st.expander('API, filtros y períodos'):
        st.code('https://data.transportation.gov/resource/8ect-6jqj.json\n$where=location=\'peachtree\'\n$order=global_time, vehicle_id')
        st.write('Through TARGET, clases2/3. Scope NB400→1346.452ft; SB1400→597.878ft. Reloj relativo por Frame_ID, no por epoch inconsistente Global_Time.')
        display_table(d,'outputs/peachtree_acquisition_timing.csv','dataset_summary.csv')
    info('Variables del dataset','Atributos utilizados como entradas, reglas o mediciones; las trayectorias observadas no mueven agentes después de la inicialización.')
    display_table(table('dataset_variables.csv'),'data/reference/Peachtree_metadata_text.txt','dataset_variables.csv')
    st.markdown('### Análisis estadístico descriptivo')
    context=st.selectbox('Adquisición estadística',['B1+B2','B2','B1'])
    stats=table('descriptive_statistics.csv')
    if context!='B1+B2':stats=stats[stats.context.eq(context)]
    st.caption('N identifica observaciones de la población indicada; vehículo-tiempo no implica independencia. SD/varianza muestrales; valores indefinidos de Time_Headway excluidos.')
    display_table(stats,'presentation_assets/tables/descriptive_statistics.csv','descriptive_statistics.csv')
    for name in ['06_speed_distribution.png','06_speed_boxplot.png','06_headway_distribution.png','06_travel_boxplot.png','06_acceleration_distribution.png','06_direction_frequency.png','06_arrivals.png']:asset(name)

def model():
    asset('04_agents_environment.png');asset('07_conceptual_model.png');asset('08_agentpy_architecture.png')
    info('Reloj y geometría','1 tick=0,1s simulados. Local_Y es el centro del frente. Los controles efectivos son referencias empíricas de entrada, no stop bars pintadas.')
    info('Reglas individuales','IDM, líder simulado y líder virtual semafórico; integración balística; inserción segura FIFO; release pooled1,6s; followers manejados por IDM. No replay ni stop-zone que fuerce velocidades.')
    st.latex(r'a=a_{\max}\left[1-\left(\frac{v}{v_0}\right)^4-\left(\frac{s^*}{s}\right)^2\right],\quad s^*=s_0+\max\left(0,vT+\frac{v\Delta v}{2\sqrt{ab}}\right)')
    info('Datos → parámetros y reglas','Las referencias y las condiciones externas vienen de datos; los cinco IDM se calibraron con B2. Convenciones, simplificaciones y reglas experimentales se declaran por separado.')
    display_table(table('model_parameters.csv'),'outputs/peachtree4/calibration_freeze.json','model_parameters.csv')
    provenance_table=table('component_provenance.csv').copy()
    rules=provenance_table.set_index('component')['value/rule']
    readable={'IDM v0/T/s0/a/b':'Ver parámetros calibrados en SI','effective control references':'Referencias11th/12th (ft), ver esquema'}
    for component,unit in [('dt','s'),('stopped','m/s'),('standstill queue gap','m'),('head selection window','ft'),('green release delay','s'),('IDM delta','sin unidad')]:
        readable[component]=f'{float(rules[component]):.2f} {unit}'
    provenance_table['value/rule']=provenance_table.apply(lambda r:readable.get(r.component,r['value/rule']),axis=1)
    display_table(provenance_table,'outputs/peachtree3u/component_classification.csv','component_provenance.csv')
    verification()

def verification():
    qa=read_json('outputs/peachtree6/test_report.json');cols=st.columns(4)
    for col,k in zip(cols,['tests_total','passed','skipped','failures']):col.metric(k.replace('_',' ').title(),str(qa[k]))
    st.write('Conservación, no solapamientos, no velocidad negativa, señales/salidas válidas, determinismo y boundaries congelados. Tests verifican implementación; no equivalen a validar el fenómeno.')
    if (ASSETS/'test_report.json').exists():
        uiqa=json.loads((ASSETS/'test_report.json').read_text());st.caption(f'QA adicional de presentación: {uiqa["passed"]}/{uiqa["presentation_tests"]} · sin repetir tests científicos ni corridas')
    provenance('outputs/peachtree6/test_report.json;outputs/peachtree6/experiment_freeze.json')

def simulation():
    from ui.simulation_view import render_simulation
    render_simulation()

def calibration():
    f=freezes()['calibration'];candidates=read_csv('outputs/peachtree4/calibration_candidates.csv');initial=candidates[candidates.stage.eq('PRECALIBRATION')].iloc[0]
    cols=st.columns(4)
    for col,label,value in zip(cols[:3],['Sets evaluados','Candidatos LHS','Seeds de desarrollo'],[str(f['evaluated_parameter_sets']),str((candidates.stage=='LHS').sum()),str(len(f['development_seeds']))]):col.metric(label,value)
    cols[3].metric('Objective FINAL',f'{f["selection_objective"]:.6f}',f'PRE {initial.objective:.6f}',delta_color='off')
    st.caption('TRAIN=B2. Normalización y seis dominios iguales predeclarados. Objetivo sin unidad; no es validación. v0 tocó el upper bound y no se amplió.')
    display_table(table('model_parameters.csv'),'outputs/peachtree4/calibration_freeze.json','calibrated_parameters.csv')
    asset('09_calibration.png')
    display_table(table('calibration_pre_post.csv'),'outputs/peachtree4/pre_vs_post_calibration.csv','calibration_pre_post.csv')
    st.warning('Tradeoff conservado: la duración de detenciones empeoró, aunque mejoró el objective global.')
    verification()

def validation():
    f=freezes()['validation'];st.markdown('### VALIDACIÓN HOLDOUT B1');st.info(f['classification'])
    st.caption(f['validation_name']);st.write('TRAIN=B2 · VALIDATION=B1 ·30 réplicas · parámetros sin cambios')
    d=table('validation_real_sim.csv');keys=list(METRICS)
    view=d[d.metric.isin(keys)][['metric','VALIDATION_REAL_B1','VALIDATION_SIM_B1']].copy()
    for k in ['operational_stopped','vehicles_stopped_fraction']:view.loc[view.metric.eq(k),['VALIDATION_REAL_B1','VALIDATION_SIM_B1']]*=100
    view['Métrica']=view.metric.map(lambda k:METRICS[k][0]+' ('+METRICS[k][1]+')');view=view.drop(columns='metric')
    display_table(view,'outputs/peachtree5/train_vs_validation.csv','validation_real_sim.csv')
    asset('10_validation.png')
    for name in ['validation_speed.png','validation_headway.png','validation_travel.png','validation_stopping.png','validation_throughput.png']:
        asset('10_'+name)
    t=read_csv('outputs/peachtree5/b1_temporal_metrics.csv');t=t[t.bin_s.eq(30)].groupby('metric')[['RMSE','MAE','bias','correlation']].mean().reset_index()
    t.loc[t.metric.eq('stopped'),['RMSE','MAE','bias']]*=100
    t['Unidad de RMSE / MAE / bias']=t.metric.map({'active':'vehículos','speed':'ft/s','stopped':'pp','throughput':'vehículos/30s'})
    t=t.rename(columns={'correlation':'Correlación (sin unidad)'})
    display_table(t,'outputs/peachtree5/b1_temporal_metrics.csv','validation_temporal_30s.csv')
    st.caption('IC95 de la media: variabilidad de simulación, no incertidumbre de REAL. El sesgo de headway y de detenciones sigue siendo evidencia disponible.')

def scenarios():
    spec=read_json('outputs/peachtree6/scenario_design_freeze.json');asset('11_scenarios.png')
    e=spec['E2'];cols=st.columns(3)
    cols[0].metric('Dirección dominante',e['DOMINANT_PROGRESSION_DIRECTION']);cols[1].metric('Tiempo de progresión',f'{e["PROGRESSION_TRAVEL_TIME"]:.2f} s');cols[2].metric('Desplazamiento',f'{e["OFFSET_SHIFT_SECONDS"]:.2f} s')
    st.write('Exactly3 alternativas. E1: +10% nominal, descontado del RED y limitado a malla0,1s. E2: mismo shift en ambos contextos y ambos sentidos del control downstream. E3: combinación sin recalcular. Diseño previo a resultados, no búsqueda de horarios.')
    context=st.selectbox('Contexto del timeline',['B2','B1']);chart(timeline(context),'11_signal_timeline.png' if context=='B2' else None)
    st.warning('EXPERIMENTAL_RULE: ciclo y amarillo conservados. All-red no está separado en las series observadas. No es una recomendación operativa para campo.')

def results():
    context=st.selectbox('Contexto de resultados',['B2','B1','B1+B2'])
    for c in (['B1','B2'] if context=='B1+B2' else [context]):
        st.markdown('### '+c+' SCENARIO RESULTS');display_table(scenario_table(c),f'outputs/peachtree6/{c.lower()}_scenario_summary.csv','scenario_results_'+c+'.csv')
    for metric in ['travel_mean_s','operational_stopped','mean_stopped_time_per_vehicle_s','speed_mean_ft_s','queue_mean']:chart(scenario_chart(context,metric))
    chart(directional_chart(context))
    for c in (['B1','B2'] if context=='B1+B2' else [context]):chart(departures(c),'12_departures_'+c+'.png')
    st.caption('Comparación SIM E1/E2/E3 frente a SIM BASE. No existen datos REAL contrafactuales. Total throughput cierra demanda; no mide capacidad absoluta.')

def emergent():
    asset('13_emergent_behavior.png')
    d=read_csv('outputs/peachtree6/emergent_behavior.csv');view=d.groupby(['context','scenario']).mean(numeric_only=True).reset_index().drop(columns='seed',errors='ignore')
    display_table(view,'outputs/peachtree6/emergent_behavior.csv','emergent_behavior.csv')
    st.write('IDM y señales producen acumulación bajo RED; los releases GREEN generan descarga y agrupación de vehículos. Las reglas locales modifican velocidades colectivas, colas y stop-and-go. El número de vehículos con varias detenciones cuantifica repetición; las curvas agrupadas permiten observar platoons.')
    context=st.selectbox('Contexto espacio-tiempo',['B2','B1']);mode=st.selectbox('Configuración espacio-tiempo',['BASE','E1','E2','E3'])
    chart(space_time(context,mode),'13_space_time_base.png' if context=='B2' and mode=='BASE' else '13_space_time_e1.png' if context=='B2' and mode=='E1' else None)
    st.caption('Seed7000 ilustrativa predeclarada. Para SB la progresión es12th→11th; para NB11th→12th. Las conclusiones usan las30 réplicas, no una animación seleccionada.')

def decision():
    f=freezes()['experiment'];st.success('RECOMMENDED WITHIN SCOPE · '+f['recommended_alternative']);asset('14_final_decision.png')
    st.caption('IC95 = intervalo de confianza del 95% de la media del efecto pareado.')
    chart(paired_chart(),'14_paired_effects.png');chart(paired_chart('operational_stopped'),'14_paired_stopping.png')
    effects=read_csv('outputs/peachtree6/paired_differences.csv');display_table(effects[effects.scenario.eq('E1')&effects.metric.isin(['travel_mean_s','operational_stopped','NB_travel_mean_s','SB_travel_mean_s'])], 'outputs/peachtree6/paired_differences.csv','paired_effects.csv')
    asset('14_robustness.png')
    pareto=read_csv('outputs/peachtree6/pareto_analysis.csv');display_table(pareto[pareto.dominates],'outputs/peachtree6/pareto_analysis.csv','pareto.csv')
    scores=read_csv('outputs/peachtree6/decision_score.csv').groupby(['context','scenario'])[['TRAVEL','STOPPING','TEMPORAL_FLOW','DIRECTIONAL_BALANCE','DECISION_SCORE']].mean().reset_index()
    display_table(scores,'outputs/peachtree6/decision_score.csv','decision_scores.csv')
    st.write('Menor score es mejor. E1 domina BASE en ambos contextos y beneficia NB/SB. E2/E3 mejoran B2, pero empeoran B1: CONTEXT_DEPENDENT. La robustez favorece E1 dentro de las alternativas evaluadas, no un óptimo universal.')
    asset('16_conclusions.png')

def limitations():
    asset('15_limitations.png')
    for text in freezes()['validation']['limitations']:st.write('• '+text)
    d=table('component_provenance.csv');display_table(d[d.classification.isin(['ASSUMPTION','LITERATURE_DERIVED'])],'outputs/peachtree3u/component_classification.csv','assumptions.csv')

def references():
    from importlib.metadata import metadata
    st.markdown('### Referencias y evidencias')
    refs=[('USDOT NGSIM Vehicle Trajectories and Supporting Data','https://data.transportation.gov/Automobiles/Next-Generation-Simulation-NGSIM-Vehicle-Trajectories/8ect-6jqj'),
        ('API Socrata utilizada','https://data.transportation.gov/resource/8ect-6jqj.json'),('AgentPy · documentación del paquete instalado',metadata('agentpy').get('Home-page')),
        ('IDM · referencia utilizada',read_json('docs/b2_estimation_criteria.json')['delta']['source'])]
    for title,url in refs:st.link_button(title,url)
    st.write('FHWA: fuente institucional NGSIM documentada en el dataset y la metadata Peachtree. Metadata local: Peachtree_Street_Metadata_Documentation.pdf. Señales originales y documentos auxiliares: data/reference/.')
    for title,path in [('Metadata Peachtree','data/reference/Peachtree_Street_Metadata_Documentation.pdf'),('Structural freeze','outputs/peachtree3u/structural_model_freeze.json'),('Calibration freeze','outputs/peachtree4/calibration_freeze.json'),('Validation freeze','outputs/peachtree5/validation_freeze.json'),('Experiment freeze','outputs/peachtree6/experiment_freeze.json'),('Tests científicos','outputs/peachtree6/test_report.json')]:
        st.download_button(title,(ROOT/path).read_bytes(),file_name=Path(path).name,key='ref_'+title)
    st.caption('Fuentes existentes del proyecto; sin nueva investigación ni licencia inventada.')

def export_center():
    st.markdown('### MATERIAL PARA PRESENTACIÓN ·17 puntos de la guía')
    st.download_button('Download todo el material ·ZIP',(ASSETS/'presentation_material.zip').read_bytes(),file_name='presentation_material.zip',mime='application/zip')
    st.download_button('Download presentation_manifest.json',(ASSETS/'presentation_manifest.json').read_bytes(),file_name='presentation_manifest.json')
    for slide in manifest()['slides']:
        with st.expander(f'Slide {slide["slide_number"]} — {slide["recommended_title"]}'):
            st.write(slide['main_message']);st.image(str(ASSETS/slide['figure_file']),width='stretch')
            st.caption('Nota sugerida: '+slide['speaker_note_summary']);provenance(slide['data_source'])
            st.download_button('Download PNG',(ASSETS/slide['figure_file']).read_bytes(),file_name=slide['figure_file'],mime='image/png',key='slide_png_'+str(slide['slide_number']))
            st.download_button('Download CSV',(ASSETS/slide['table_file']).read_bytes(),file_name=Path(slide['table_file']).name,mime='text/csv',key='slide_csv_'+str(slide['slide_number']))
    references()

def main():
    st.html('''<style>.stApp{background:#f6f8fc;color:#102a43}.block-container{max-width:1500px;padding-top:4.5rem}h1,h2,h3{color:#102a43} [data-testid="stMetric"]{background:white;border:1px solid #d9e2ef;border-radius:12px;padding:16px} [data-testid="stMetricValue"]{font-size:1.5rem!important} [data-testid="stSidebar"]{background:#eaf0f7}button{border-radius:8px!important}</style>''')
    st.title('NGSIM Peachtree · AgentPy')
    st.caption('REALIDAD → DATOS → AGENTES Y REGLAS → MODELO → CALIBRACIÓN → VALIDACIÓN →3 ESCENARIOS → EXPERIMENTACIÓN → DECISIÓN')
    st.caption('BASELINE VALIDATED WITH LIMITATIONS · Resultados científicos congelados · Material académico exportable')
    if not (ASSETS/'presentation_manifest.json').exists():st.error('Faltan assets. Ejecutar python -m scripts.build_presentation_assets.');return
    tabs=st.tabs(SECTIONS,key='presentation_section',on_change='rerun')
    functions=[project,data,model,simulation,calibration,validation,scenarios,results,emergent,decision,limitations,export_center]
    for tab,render in zip(tabs,functions):
        if tab.open:
            with tab:render()
