"""Complete simulation presentation, using saved AgentPy states and frozen results."""
import io,json,uuid
from functools import partial
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from PIL import Image,PngImagePlugin
from ui.presentation_data import ROOT,ASSETS,read_json,read_csv,style,COLORS,METRICS,scenario_chart,directional_chart,departures,space_time
from ui.canvas_renderer import render_canvas

SCENARIOS={'BASE':'Operación observada','E1':'Green Split','E2':'Coordinación semafórica','E3':'Green Split + Coordinación'}
WINDOWS={'60 s':60.,'120 s':120.,'180 s':180.,'Completa':None}
HORIZON_HELP='El horizonte corresponde al periodo temporal real reproducido por el modelo. La simulación no termina por alcanzar una cantidad fija de vehículos.'

def clock_label(seconds):
    tenths=round(seconds*10);minutes,remainder=divmod(tenths,600)
    return f'{minutes:02d}:{remainder/10:04.1f}'

@st.cache_data
def saved_run(context,scenario):
    path=f'outputs/peachtree6/traces/{context}_{scenario}_7000.json'
    trace=read_json(path)
    source='outputs/peachtree5/b1_exogenous_inputs.json' if context=='B1' else 'outputs/peachtree3u/final_inputs.json'
    inputs=read_json(source)
    assert trace['context']==context and trace['scenario']==scenario and trace['seed']==7000
    return trace,inputs,path,source

def run_series(trace,end):
    return pd.DataFrame([f['metrics'] for f in trace['frames'] if f['time']<=end])

def temporal_figure(trace,end,kind,source):
    d=run_series(trace,end);context=trace['context'];scenario=trace['scenario'];t=d.simulation_time
    if kind=='speed_stopped':
        fig=make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=.24,subplot_titles=['Velocidad media (ft/s)','Fracción detenida (%)'])
        specs=[('mean_speed_ft_s','Velocidad media','ft/s',1),('stopped_fraction','Fracción detenida','%',100)]
        for row,(key,label,unit,factor) in enumerate(specs,1):
            values=d[key].where(d.vehicles_active.gt(0))*factor
            fig.add_trace(go.Scatter(x=t.tolist(),y=values.tolist(),mode='lines',name=label,line=dict(color='#007f73' if row==1 else '#b67a12',width=2)),row=row,col=1)
            fig.update_yaxes(title=label+' ('+unit+')',row=row,col=1)
            finite=values.dropna()
            if len(finite):fig.add_annotation(text=f'Máximo {finite.max():.2f} {unit} · último estado con activos {finite.iloc[-1]:.2f} {unit}',x=1,y=1 if row==1 else .38,xref='paper',yref='paper',showarrow=False,xanchor='right',yanchor='bottom',font_size=15)
        title='Velocidad y detenciones durante la corrida';fig.update_xaxes(title='Tiempo simulado (s)',row=2,col=1)
    else:
        key,title,ytitle=('queue_proxy_vehicles','Formación y disipación de la cola','Vehículos en cola (proxy operacional)') if kind=='queue' else ('throughput_cumulative','Progresión de salidas de la corrida','Salidas acumuladas (vehículos)')
        values=d[key];fig=go.Figure(go.Scatter(x=t.tolist(),y=values.tolist(),mode='lines',line=dict(color=COLORS[scenario],width=3),name='Corrida ilustrativa'))
        peak=values.idxmax();text=f'Máximo: {values.max():.0f} vehículos en {t.loc[peak]:.1f} s · último snapshot: {values.iloc[-1]:.0f} vehículos'
        if kind=='departures' and values.iloc[-1]>0:
            quantiles=[float(t[values.ge(values.iloc[-1]*q)].iloc[0]) for q in [.5,.9]]
            text+=f'<br>t50 ≈ {quantiles[0]:.1f} s · t90 ≈ {quantiles[1]:.1f} s del total mostrado (snapshots; no son hitos oficiales)'
        fig.add_annotation(text=text,x=.01,y=.97,xref='paper',yref='paper',showarrow=False,xanchor='left',align='left',bgcolor='#F6F8FC',borderpad=8,font_size=16)
        fig.update_yaxes(title=ytitle);fig.update_xaxes(title='Tiempo simulado (s)')
    style(fig,title+' — '+context+' · '+scenario,source,subtitle=f'Corrida ilustrativa guardada · seed 7000 · ventana 0–{end:.1f} s · no es la media de 30 réplicas<br>B1: validación · B2: calibración TRAIN · snapshots cada 0,5 s · física dt = 0,1 s')
    fig.update_layout(showlegend=False,height=850 if kind=='speed_stopped' else 750,margin=dict(t=180,b=190))
    return fig,d

def png_bytes(figure_json):
    fig=go.Figure(json.loads(figure_json));blob=fig.to_image(format='png',width=1920,height=1080,scale=1)
    with Image.open(io.BytesIO(blob)) as im:
        metadata=PngImagePlugin.PngInfo();metadata.add_text('source_artifact',fig.layout.meta['source_artifact'])
        out=io.BytesIO();im.save(out,format='PNG',pnginfo=metadata);return out.getvalue()

def show_figure(fig,name,data):
    fig.update_layout(margin_b=210,height=max(fig.layout.height or 800,800))
    if fig.layout.showlegend is not False:fig.update_layout(legend=dict(y=1.06,yanchor='bottom',x=0))
    for a in fig.layout.annotations:
        if str(a.text).startswith('Fuente:'):a.y=-.28
    st.plotly_chart(fig,width='stretch',theme=None,config={'displayModeBar':False,'displaylogo':False},key='simulation_chart_'+name)
    source=fig.layout.meta['source_artifact']
    left,right=st.columns([1,1])
    left.download_button('Descargar PNG',data=partial(png_bytes,fig.to_json()),file_name=name+'.png',mime='image/png',key='simulation_png_'+name,on_click='ignore')
    csv=data.copy();csv['source_artifact']=source
    right.download_button('Descargar CSV',csv.to_csv(index=False).encode('utf-8-sig'),file_name=name+'.csv',mime='text/csv',key='simulation_csv_'+name,on_click='ignore')
    with st.expander('Fuente de la figura'):st.caption(source)

def render_simulation(technical=False):
    st.markdown('### Configuración')
    cols=st.columns([1.2,1.7,1,1,1])
    context=cols[0].selectbox('Contexto de simulación',['B2','B1'],format_func=lambda c:c+' — '+('Validación' if c=='B1' else 'Calibración'),key='simulation_context')
    scenario=cols[1].selectbox('Escenario de simulación',list(SCENARIOS),format_func=lambda s:s+' — '+SCENARIOS[s],key='simulation_scenario')
    cols[2].selectbox('Seed ilustrativa',[7000],key='simulation_seed',help='Seed ilustrativa predeclarada: se reproducen sus estados AgentPy guardados.')
    window=cols[3].selectbox('Ventana visual',list(WINDOWS),index=2,key='simulation_window')
    speed=cols[4].selectbox('Playback',[.5,1.,2.,5.,10.],index=1,format_func=lambda x:f'x{x:g}',key='simulation_playback')
    trace,inputs,path,input_source=saved_run(context,scenario);horizon=float(inputs['horizon_s']);end=min(WINDOWS[window] or horizon,horizon)
    state=st.session_state;identity=f'{context}:{scenario}:7000:{window}'
    if state.get('presentation_trace_id')!=identity:
        state.presentation_trace_id=identity;state.presentation_run_id=str(uuid.uuid4());state.presentation_playing=False;state.presentation_reset=True
    controls=st.columns(4)
    if controls[0].button('Iniciar',type='primary',key='simulation_start'):state.presentation_playing=True
    if controls[1].button('Pausar',key='simulation_pause'):state.presentation_playing=False
    if controls[2].button('Continuar',key='simulation_continue'):state.presentation_playing=True
    if controls[3].button('Reiniciar',key='simulation_reset'):state.presentation_playing=False;state.presentation_run_id=str(uuid.uuid4());state.presentation_reset=True
    st.caption('Reproducción de estados AgentPy oficiales guardados. Playback controla la animación; la física permanece en dt = 0,1 s.')
    st.markdown('### Contexto y escenario')
    left,right=st.columns(2)
    with left:
        st.markdown('**'+('B1 · VALIDACIÓN' if context=='B1' else 'B2 · CALIBRACIÓN')+'**')
        st.write('Periodo real independiente utilizado para evaluar qué tan bien generaliza el baseline calibrado.' if context=='B1' else 'Periodo real utilizado para estimar y calibrar los parámetros finales del baseline.')
        st.caption(f'{len(inputs["initial"])+len(inputs["entries"])} vehículos TARGET · {len(inputs["initial"])} iniciales · {len(inputs["entries"])} llegadas programadas')
        if context=='B1':st.caption('Validación temporal/de adquisición con exposición previa a resúmenes de factibilidad.')
    design=read_json('outputs/peachtree6/scenario_design_freeze.json')['E2']
    descriptions={'BASE':'Condiciones semafóricas observadas.',
        'E1':'Green Split: aumenta nominalmente 10% el verde Through, reduciendo rojo y conservando ciclo y amarillo.',
        'E2':'Coordinación semafórica: modifica el offset para favorecer progresión SB desde 12th hacia 11th.',
        'E3':'Combinación de Green Split + Coordinación.'}
    with right:
        st.markdown('**'+scenario+' · '+SCENARIOS[scenario]+'**');st.write(descriptions[scenario])
        if scenario in ['E2','E3']:st.caption(f'Tiempo de progresión: {design["PROGRESSION_TRAVEL_TIME"]:.2f} s · desplazamiento del offset: {design["OFFSET_SHIFT_SECONDS"]:.2f} s')
    cols=st.columns(2)
    cols[0].metric('Horizonte oficial',f'{horizon:.1f} s · {clock_label(horizon)}',help=HORIZON_HELP)
    cols[1].metric('Ventana de demostración',clock_label(end),help='La ventana limita la reproducción visual; no modifica la corrida oficial ni sus resultados.')
    st.caption(f'Reloj relativo de la adquisición: inicio {inputs["source_window_start_relative_s"]:.1f} s · fin {inputs["source_window_start_relative_s"]+horizon:.1f} s.')
    st.caption('La corrida completa cubre el horizonte temporal de la adquisición y procesa las llegadas programadas. Las salidas son un resultado del modelo, no el criterio único de finalización.')
    refs=st.toggle('Mostrar referencias técnicas',value=technical,key='simulation_references')
    st.markdown('### Progreso temporal, Canvas y métricas en vivo')
    view=dict(context=context,scenario=scenario,scenario_label=SCENARIOS[scenario],horizon_s=horizon,end_s=end,
        scheduled_target=len(inputs['initial'])+len(inputs['entries']),technical=technical,partial=end<horizon,
        stopped_threshold_ft_s=.1*(3937/1200))
    st.iframe(render_canvas(trace,state.presentation_run_id,state.presentation_playing,speed,state.presentation_reset,
        show_heads=False,show_effective=refs,presentation=True,light=True,view=view),height=1050,alt='Progreso, demanda, Canvas claro y ocho métricas de la corrida ilustrativa')
    state.presentation_reset=False
    st.caption(f'Último snapshot guardado: {trace["frames"][-1]["time"]:.1f} s. Entre snapshots se interpola solo la posición visual; en la fracción final sin snapshot se conserva el último estado guardado.')
    if technical:
        with st.expander('Detalles técnicos de la corrida'):
            st.write('Tick físico = tiempo / 0,1 s. El reloj visual y los snapshots no ejecutan nuevos pasos de AgentPy.')
            st.json(dict(context=context,scenario=scenario,seed=trace['seed'],dt_s=inputs['dt'],start_s=inputs['source_window_start_relative_s'],end_s=inputs['source_window_start_relative_s']+horizon,horizon_s=horizon,
                cuts=trace['receiving_scope'],references=trace['network']['stop_lines']))
            st.json(read_json('outputs/peachtree4/calibration_freeze.json')['final_parameter_values'])
            st.caption('IDs visibles al activar referencias técnicas; dimensiones físicas y estados guardados intactos.')
    st.divider();st.markdown('## Dinámica de la corrida actual')
    st.write('¿Qué está ocurriendo durante la simulación? Estas series pertenecen exclusivamente a la seed ilustrativa seleccionada y muestran toda la ventana visual, sin depender del avance de la reproducción.')
    for kind in ['speed_stopped','queue','departures']:
        fig,data=temporal_figure(trace,end,kind,path);show_figure(fig,f'run_{context}_{scenario}_{window.replace(" ","")}_{kind}',data)
    st.divider();st.markdown('## Resultados oficiales — 30 réplicas')
    st.info('Las siguientes métricas corresponden a las 30 réplicas oficiales y no a la corrida visual actual.')
    summary=read_csv(f'outputs/peachtree6/{context.lower()}_scenario_summary.csv');pivot=summary.pivot(index='metric',columns='scenario',values='mean')
    cols=st.columns(3)
    for col,key in zip(cols,['travel_mean_s','operational_stopped','mean_stopped_time_per_vehicle_s']):
        label,unit=METRICS[key];factor=100 if unit=='%' else 1;v=pivot.loc[key,scenario]*factor;b=pivot.loc[key,'BASE']*factor
        col.metric(label,f'{v:.2f} {unit}',f'{v-b:+.2f} '+('p.p.' if unit=='%' else unit)+' frente a BASE',delta_color='off')
    st.markdown('### Comparación BASE frente a escenarios')
    for key in ['travel_mean_s','operational_stopped']:
        show_figure(scenario_chart(context,key),f'official_{context}_{key}',summary[summary.metric.eq(key)])
    show_figure(directional_chart(context),f'official_{context}_directional',summary[summary.metric.isin(['NB_travel_mean_s','SB_travel_mean_s'])])
    temporal=read_csv('outputs/peachtree6/temporal_departures.csv')
    show_figure(departures(context),f'official_{context}_departures',temporal[temporal.context.eq(context)&temporal.direction.eq('ALL')])
    st.divider();st.markdown('## Comportamiento emergente')
    st.write('El comportamiento colectivo surge de la interacción entre VehicleAgents, seguimiento vehicular y señales; no se programa directamente una cola o un pelotón.')
    trajectories=pd.read_parquet(ROOT/f'outputs/peachtree6/illustrative_{context}_{scenario}.parquet')
    show_figure(space_time(context,scenario,end_time=end),f'run_{context}_{scenario}_space_time',trajectories[trajectories.time.le(end)&trajectories.frame.mod(5).eq(0)])
    queues=read_csv('outputs/peachtree6/queue_results.csv');emergent=read_csv('outputs/peachtree6/emergent_behavior.csv')
    grouped=emergent[emergent.context.eq(context)].groupby('scenario')[['vehicles_multiple_stops','peak_active']].mean()
    cols=st.columns(4)
    for j,(key,label) in enumerate([('queue_mean','Cola media'),('queue_max','Cola máxima'),('vehicles_multiple_stops','Vehículos con múltiples detenciones'),('peak_active','Máximo de vehículos activos')]):
        if key.startswith('queue_'):
            q=queues[queues.context.eq(context)&queues.metric.eq(key)].set_index('scenario')['mean'];v=q.loc[scenario];b=q.loc['BASE']
        else:v=grouped.loc[scenario,key];b=grouped.loc['BASE',key]
        cols[j].metric(label,f'{v:.2f} vehículos',f'{v-b:+.2f} frente a BASE',delta_color='off')
    st.caption('Resumen oficial de 30 réplicas: la cola máxima y el máximo de activos son máximos por réplica promediados.')
    messages={'BASE':'BASE representa la operación observada utilizada como referencia para comparar intervenciones.',
        'E1':'E1 reduce de forma consistente el tiempo de recorrido y las detenciones en B1 y B2; es la alternativa recomendada.',
        'E2':'E2 mejora B2, pero deteriora resultados en B1; su efecto depende del contexto.',
        'E3':'E3 obtiene fuertes mejoras en B2 pero no mantiene la ventaja en B1; se clasifica como dependiente del contexto.'}
    st.markdown('### Interpretación del escenario');st.info(messages[scenario])
    st.caption('Resultados dentro del alcance congelado; sesgos de headway y detenciones, diferencias de distribución B1 y demanda cerrada limitan la interpretación de campo.')

