"""Read-only presentation views of official results. No model/optimizer imports."""
import json
import textwrap
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'presentation_assets'
SECTIONS=['Proyecto','Datos','Modelo','Simulación','Calibración','Validación','Escenarios','Resultados','Comportamiento emergente','Decisión','Limitaciones','Material para presentación']
TITLE='Simulación basada en agentes del tráfico en un corredor urbano semaforizado mediante datos reales NGSIM Peachtree Street'
QUESTION='¿Cómo afectan cambios en el green split y en la coordinación semafórica entre 11th y 12th al tiempo de recorrido, las detenciones y la dinámica del tráfico Through, bajo diferentes condiciones observadas de demanda?'
OBJECTIVE='Evaluar mediante simulación basada en agentes el efecto de tres estrategias de control semafórico sobre el desempeño del tráfico Through entre 11th y 12th de Peachtree Street, utilizando datos reales para calibración y validación y apoyando la selección de la alternativa con mejor desempeño.'
COLORS={'BASE':'#486A95','E1':'#008E84','E2':'#D99A32','E3':'#875F9A','B2':'#237C8A','B1':'#C5762D'}
METRICS={'travel_mean_s':('Tiempo de recorrido','s'),'section_travel_mean_s':('Recorrido entre controles','s'),
    'operational_stopped':('Fracción detenida operacional','%'),'vehicles_stopped_fraction':('Vehículos que se detienen','%'),
    'mean_stopped_time_per_vehicle_s':('Tiempo detenido por vehículo','s/vehículo'),'stop_episodes_per_vehicle':('Episodios por vehículo','episodios/vehículo'),
    'speed_mean_ft_s':('Velocidad media','ft/s'),'headway_mean_ft':('Headway medio','ft'),'queue_mean':('Cola media','vehículos'),
    'stop_episodes':('Episodios de detención','episodios'),'complete_stop_duration_mean_s':('Duración de detención completa','s'),
    'throughput_total':('Salidas totales','vehículos'),'departure_t90_s':('Tiempo al 90% de salidas','s')}

def read_json(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def read_csv(path):return pd.read_csv(ROOT/path)
def table(name):return pd.read_csv(ASSETS/'tables'/name)
def freezes():return {name:read_json(path) for name,path in {'structure':'outputs/peachtree3u/structural_model_freeze.json','calibration':'outputs/peachtree4/calibration_freeze.json','validation':'outputs/peachtree5/validation_freeze.json','experiment':'outputs/peachtree6/experiment_freeze.json'}.items()}
def source_table(d,source):
    d=d.copy();d['source_artifact']=source;return d

def style(fig,title,source,ytitle=None,subtitle=None):
    subtitle=subtitle or 'Evidencia del proyecto · datos y supuestos congelados'
    source_label='resultados del modelo AgentPy — PEACHTREE-6' if 'peachtree6/' in source else 'datos y artefactos oficiales del proyecto NGSIM Peachtree'
    fig.update_layout(template='plotly_white',title={'text':title+'<br><sup>'+subtitle+'</sup>','x':.035,'y':.95,'yanchor':'top','font':{'size':28}},font={'family':'Arial','size':18,'color':'#102A43'},
        paper_bgcolor='#F6F8FC',plot_bgcolor='#FFFFFF',margin=dict(l=100,r=65,t=165,b=105),height=700,
        legend=dict(orientation='h',y=1.08,x=0,title_text=''),meta={'source_artifact':source},
        annotations=[a for a in fig.layout.annotations if not str(a.text).startswith(('SOURCE ARTIFACT:','Fuente:'))]+[dict(text='Fuente: '+source_label,xref='paper',yref='paper',x=0,y=-.14,showarrow=False,font=dict(size=12,color='#64748B'),align='left',xanchor='left')])
    if ytitle:fig.update_yaxes(title_text=ytitle)
    return fig


def scenario_table(context):
    d=read_csv(f'outputs/peachtree6/{context.lower()}_scenario_summary.csv');keys=['travel_mean_s','section_travel_mean_s','operational_stopped','vehicles_stopped_fraction','mean_stopped_time_per_vehicle_s','stop_episodes_per_vehicle','speed_mean_ft_s','queue_mean']
    p=d[d.metric.isin(keys)].pivot(index='scenario',columns='metric',values='mean').reindex(['BASE','E1','E2','E3'])
    for key in ['operational_stopped','vehicles_stopped_fraction']:p[key]*=100
    return p.rename(columns={k:METRICS[k][0]+' ('+METRICS[k][1]+')' for k in keys}).reset_index()






def card_figure(title,blocks,source):
    fig=go.Figure()
    n=len(blocks);columns=2 if n>3 else 1;rows=int(np.ceil(n/columns))
    for j,(heading,body) in enumerate(blocks):
        body='<br>'.join('<br>'.join(textwrap.wrap(part,width=49 if columns==2 else 99)) for part in body.split('<br>'))
        col=j%columns;row=j//columns;x=col/columns+.035;y=1-(row+.5)/rows
        fig.add_shape(type='rect',x0=x,y0=y-.39/rows,x1=(col+1)/columns-.035,y1=y+.39/rows,fillcolor='#FFFFFF',line=dict(color='#D9E2EF',width=1))
        fig.add_annotation(x=x+.018,y=y+.24/rows,text='<b>'+heading+'</b>',showarrow=False,xanchor='left',font=dict(size=22,color='#008E84'))
        fig.add_annotation(x=x+.018,y=y-.05/rows,text=body,showarrow=False,xanchor='left',font=dict(size=19),align='left')
    fig.update_xaxes(visible=False,range=[0,1]);fig.update_yaxes(visible=False,range=[0,1]);return style(fig,title,source)

def assets_chart(name):
    path=ASSETS/'charts'/name
    import base64
    def decode(value):
        if isinstance(value,dict):
            if 'bdata' in value and 'dtype' in value:
                a=np.frombuffer(base64.b64decode(value['bdata']),dtype=value['dtype'])
                if value.get('shape'):a=a.reshape(tuple(int(x) for x in value['shape'].split(',')))
                return a.tolist()
            return {k:decode(v) for k,v in value.items()}
        if isinstance(value,list):return [decode(v) for v in value]
        return value
    return go.Figure(decode(json.loads(path.read_text(encoding='utf-8'))))

# Shared figure factories used by both Streamlit and clean Kaleido exports.
from ui.static_charts import (scenario_chart, directional_chart, paired_chart,
    timeline, departures, space_time, emergent_chart, robustness_chart,
    validation_distribution, validation_departures)
