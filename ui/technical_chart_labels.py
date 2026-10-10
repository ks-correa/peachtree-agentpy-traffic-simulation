"""Static reading aids for the preserved TRAIN technical charts."""
import numpy as np
import plotly.graph_objects as go

LABELS={'simulation_time':'Tiempo simulado (s)','time':'Tiempo simulado (s)','duration_s':'Duración (s)',
    'mean_speed_ft_s':'Velocidad media (ft/s)','vehicles_active':'Vehículos activos','stopped_vehicles':'Vehículos detenidos',
    'queue_proxy_vehicles':'Vehículos en cola','throughput_cumulative':'Salidas acumuladas (vehículos)',
    'stopped_fraction':'Fracción detenida','travel_time_mean_s':'Tiempo medio de recorrido (s)',
    'probability':'Proporción de observaciones','real_exits':'Salidas observadas','simulated_exits':'Salidas simuladas',
    'queue':'Vehículos en cola','REAL_B2':'Observado B2','SIM_B2':'Simulado B2',
    'OLD_BASELINE':'Baseline anterior','REVISED_BASELINE':'Baseline revisado','REAL_B2_ALL_OBSERVED_ARTERIAL':'Contexto arterial observado B2',
    'series':'Serie','variable':'Serie'}

def annotate_technical(fig,context='B2',source=None):
    # SVG keeps dense saved series visible in browsers without a WebGL context.
    traces=[]
    for trace in fig.data:
        payload=trace.to_plotly_json()
        if payload.get('type')=='scattergl':payload['type']='scatter'
        for axis in ['x','y']:
            if axis in payload and isinstance(payload[axis],np.ndarray):payload[axis]=payload[axis].tolist()
        traces.append(payload)
    fig=go.Figure(data=traces,layout=fig.layout)
    title=fig.layout.title.text or 'Evidencia TRAIN'
    title=title.replace('Travel time','Tiempo de recorrido').replace('Throughput','Salidas').replace('Queue operacional','Cola operacional').replace('Headway front-to-front','Distancia entre frentes')
    role='B1 — VALIDATION' if context=='B1' else 'B2 — TRAIN'
    fig.update_layout(title=dict(text=title+'<br><sup>'+role+' · series existentes</sup>',font_size=17,y=.97,yanchor='top'),height=610,
        margin=dict(l=65,r=30,t=210,b=115),legend=dict(orientation='h',y=-.22),font_size=13)
    xkey=fig.layout.xaxis.title.text;ykey=fig.layout.yaxis.title.text
    xunit='ft/s' if 'velocidad' in title.lower() else 'ft' if 'frentes' in title else 's'
    fig.update_xaxes(title=LABELS.get(xkey,'Valor ('+xunit+')' if xkey=='value' else xkey))
    fig.update_yaxes(title=LABELS.get(ykey,'Vehículos' if ykey=='value' else 'Proporción acumulada' if ykey=='probability' else ykey))
    if xkey=='duration_s':fig.update_yaxes(title='Proporción acumulada',tickformat='.0%')
    summaries=[]
    for t in fig.data:
        original=t.name or '';t.name=LABELS.get(original,original.replace('_',' '))
        if t.y is None or t.x is None:continue
        x=np.asarray(t.x,dtype=float);y=np.asarray(t.y,dtype=float);valid=np.isfinite(x)&np.isfinite(y);x=x[valid];y=y[valid]
        if not len(y):continue
        name=t.name or LABELS.get(ykey,title.split(' · ')[0])
        if ykey=='probability' and xkey=='value' and y.sum()>0:
            w=y/y.sum();mean=float((x*w).sum());sd=float(np.sqrt(((x-mean)**2*w).sum()));med=float(x[np.searchsorted(np.cumsum(w),.5)])
            summaries.append(f'{name}: media ≈{mean:.2f}, mediana ≈{med:.2f}, SD ≈{sd:.2f} {xunit} (bins)')
        elif ykey=='probability' and xkey=='duration_s':
            med=float(x[np.argmin(abs(y-.5))]);summaries.append(f'{name}: mediana ≈{med:.2f} s · N {len(y)}')
        else:
            fraction=ykey=='stopped_fraction';factor=100 if fraction else 1;unit='%' if fraction else 'ft/s' if ykey=='mean_speed_ft_s' else 's' if ykey=='travel_time_mean_s' else 'veh'
            j=int(np.argmax(y));summaries.append(f'{name}: final {y[-1]*factor:.2f} {unit} · máximo {y[j]*factor:.2f} en {x[j]:.1f} s')
            if ykey=='throughput_cumulative' and y[-1]>0:
                t50=x[np.flatnonzero(y>=y[-1]*.5)[0]];t90=x[np.flatnonzero(y>=y[-1]*.9)[0]]
                summaries[-1]+=f'<br>t50 ≈{t50:.1f} s · t90 ≈{t90:.1f} s (resolución de la serie)'
    if ykey=='stopped_fraction':fig.update_yaxes(title='Fracción detenida (%)',tickformat='.0%')
    fig.add_annotation(text='<br>'.join(summaries),xref='paper',yref='paper',x=0,y=1.04,xanchor='left',yanchor='bottom',showarrow=False,align='left',font=dict(size=11))
    if source:
        fig.update_layout(meta={'source_artifact':source})
        fig.add_annotation(text='Fuente: '+source,xref='paper',yref='paper',x=0,y=-.36,xanchor='left',showarrow=False,font=dict(size=9,color='#64748B'))
    return fig
