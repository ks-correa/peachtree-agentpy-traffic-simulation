"""Self-contained static/interactive views. Reads frozen results only."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from ui.presentation_data import ROOT, COLORS, METRICS, read_csv, read_json, style

ORDER=['BASE','E1','E2','E3']
CONTEXT='B1 = validación · B2 = calibración/experimentación TRAIN'
SCENARIOS='BASE: referencia · E1: más verde · E2: coordinación · E3: E1 + E2'

def note(fig,text,x=1,y=1,**kwargs):
    fig.add_annotation(name='static_reading',text=text,x=x,y=y,xref='paper',yref='paper',showarrow=False,
        xanchor='right',yanchor='top',align='left',font=dict(size=16,color='#102A43'),
        bgcolor='rgba(246,248,252,0.94)',bordercolor='#D9E2EF',borderpad=10,**kwargs)

def scenario_chart(context,metric):
    contexts=['B1','B2'] if context=='B1+B2' else [context]
    name,unit=METRICS[metric];rows=[]
    for c in contexts:
        d=read_csv(f'outputs/peachtree6/{c.lower()}_scenario_summary.csv')
        d=d[d.metric.eq(metric)].copy();d['context']=c
        if unit=='%':d[['mean','CI95_low','CI95_high']]*=100
        base=d.loc[d.scenario.eq('BASE'),'mean'].iloc[0]
        d['label']=[f'{r.mean:.2f} {unit}<br>'+('Referencia' if r.scenario=='BASE' else f'{(r.mean/base-1)*100:+.2f}% vs BASE') for r in d.itertuples()]
        rows.append(d)
    data=pd.concat(rows)
    fig=px.bar(data,x='scenario',y='mean',color='scenario',text='label',facet_col='context' if len(contexts)>1 else None,
        category_orders={'scenario':ORDER,'context':['B1','B2']},color_discrete_map=COLORS,
        error_y=data.CI95_high-data['mean'],error_y_minus=data['mean']-data.CI95_low)
    fig.update_traces(textposition='outside',textfont_size=16,cliponaxis=False,error_y=dict(thickness=2,width=7))
    for a in fig.layout.annotations:a.text=a.text.replace('context=','')
    title='Tiempo promedio de recorrido' if metric=='travel_mean_s' else name
    source=';'.join(f'outputs/peachtree6/{c.lower()}_scenario_summary.csv' for c in contexts)
    better='mayor velocidad no implica por sí sola mejor desempeño' if metric=='speed_mean_ft_s' else 'menor es mejor'
    style(fig,title+' — '+context,source,name+' ('+unit+')',f'Media de 30 réplicas · {better} · barras de error: IC95 de la media<br>{CONTEXT}<br>{SCENARIOS}')
    fig.update_layout(margin=dict(t=220,b=135),showlegend=False)
    fig.update_xaxes(title='Escenario');fig.update_yaxes(range=[0,float(data.CI95_high.max())*1.30])
    if metric=='travel_mean_s':
        effects=[]
        for c,d in zip(contexts,rows):
            b=d.loc[d.scenario.eq('BASE'),'mean'].iloc[0];e=d.loc[d.scenario.eq('E1'),'mean'].iloc[0]
            effects.append(f'{c}: {(1-e/b)*100:.2f}%')
        note(fig,'E1 reduce el tiempo frente a BASE · '+' · '.join(effects),y=-.09)
    return fig

def directional_chart(context):
    contexts=['B1','B2'] if context=='B1+B2' else [context];rows=[]
    for c in contexts:
        d=read_csv(f'outputs/peachtree6/{c.lower()}_scenario_summary.csv')
        d=d[d.metric.isin(['NB_travel_mean_s','SB_travel_mean_s'])].copy()
        d['Dirección']=d.metric.str[:2];d['Contexto']=c;d['label']=d['mean'].map(lambda v:f'{v:.2f} s');rows.append(d)
    d=pd.concat(rows)
    fig=px.bar(d,x='scenario',y='mean',color='Dirección',text='label',barmode='group',facet_col='Contexto',
        category_orders={'scenario':ORDER,'Dirección':['NB','SB'],'Contexto':['B1','B2']},color_discrete_map={'NB':'#008E84','SB':'#875F9A'})
    for a in fig.layout.annotations:a.text=a.text.replace('Contexto=','')
    style(fig,'Tiempo de recorrido por dirección','outputs/peachtree6/directional_results.csv','Tiempo de recorrido (s)',
        f'Media de 30 réplicas · NB: norte · SB: sur · menor es mejor<br>{CONTEXT}<br>{SCENARIOS}')
    fig.update_layout(margin=dict(t=225),legend=dict(y=1.10))
    fig.update_traces(textposition='outside',textfont_size=15,cliponaxis=False)
    fig.update_xaxes(title='Escenario');fig.update_yaxes(range=[0,d['mean'].max()*1.25]);return fig

def paired_chart(metric='travel_mean_s'):
    d=read_csv('outputs/peachtree6/paired_differences.csv');d=d[d.scenario.eq('E1')&d.metric.eq(metric)].copy()
    stopped=metric=='operational_stopped';unit='p.p.' if stopped else 's'
    if stopped:d[['mean','CI95_low','CI95_high']]*=100
    fig=go.Figure()
    for j,c in enumerate(['B1','B2']):
        r=d[d.context.eq(c)].iloc[0]
        fig.add_trace(go.Scatter(x=[r['mean']],y=[j],mode='markers',name=c,
            marker=dict(size=17,color=COLORS[c]),error_x=dict(type='data',array=[r.CI95_high-r['mean']],arrayminus=[r['mean']-r.CI95_low],thickness=3,width=12)))
        label=f'<b>{r["mean"]:+.2f} {unit}</b> · IC95 [{r.CI95_low:.2f}, {r.CI95_high:.2f}] {unit}'
        if not stopped:label+=f'<br>{r.mean_percentage_change:+.2f}% frente a BASE'
        fig.add_annotation(x=r['mean'],y=j,text=label,showarrow=False,yshift=55,font=dict(size=20),xanchor='left',align='left')
    title='Reducción de la fracción de tiempo detenido con E1' if stopped else 'Reducción del tiempo de recorrido con E1'
    style(fig,title,'outputs/peachtree6/paired_differences.csv',subtitle=f'Efecto pareado E1 − BASE · 30 réplicas · valores negativos = mejora<br>{CONTEXT}<br>IC95 = intervalo de confianza del 95% de la media del efecto pareado')
    low=float(d.CI95_low.min());fig.update_xaxes(title='Cambio en fracción detenida (p.p.)' if stopped else 'Cambio en tiempo de recorrido (s)',range=[low-abs(low)*.17,abs(low)*.05])
    fig.update_yaxes(tickvals=[0,1],ticktext=['B1 — VALIDATION','B2 — TRAIN'],range=[-.5,1.6],title=None)
    fig.add_vline(x=0,line_dash='dash',line_color='#64748B');note(fig,'← Mejora · 0 = sin cambio',x=1,y=.99)
    fig.update_layout(showlegend=False,margin=dict(l=200,t=200));return fig

def timeline(context='B2'):
    design=read_json('outputs/peachtree6/scenario_design_freeze.json')['E2']
    origin=read_json('outputs/peachtree3u/final_inputs.json' if context=='B2' else 'outputs/peachtree5/b1_exogenous_inputs.json')['source_window_start_relative_s']
    changes=read_csv('outputs/peachtree6/signal_changes_by_cycle.csv');changes=changes[changes.context.eq(context)&changes.direction.eq(design['direction'])]
    fig=go.Figure();colors={'GREEN':'#008E84','YELLOW':'#E5B445','RED':'#D66B6B'};labels={'GREEN':'Verde','YELLOW':'Amarillo','RED':'Rojo'}
    for k,mode in enumerate(ORDER):
        for r in read_json(f'outputs/peachtree6/signals_{context}_{mode}.json'):
            if r['direction']!=design['direction']:continue
            a=r['t_start_s']-origin;b=r['t_end_s']-origin
            if b<=0 or a>=400:continue
            y=7-k*2-(r['intersection_id']-2);label=labels[r['state']]
            fig.add_trace(go.Bar(x=[min(400,b)-max(0,a)],y=[y],base=[max(0,a)],orientation='h',marker_color=colors[r['state']],width=.65,
                name=label,showlegend=not any(t.name==label for t in fig.data),hovertemplate=mode+' · '+r['state']+'<extra></extra>'))
        for intersection in [2,3]:
            c=changes[changes.intersection.eq(intersection)]
            def span(key):return f'{c[key].min():.1f}–{c[key].max():.1f}'
            g='E1_green_s' if mode in ['E1','E3'] else 'BASE_green_s'
            text=f'V {span(g)} s · A {span("yellow_s")} s · C {span("cycle_s")} s'
            fig.add_annotation(x=410,y=7-k*2-(intersection-2),text=text,showarrow=False,xanchor='left',font=dict(size=14))
    style(fig,'Programación semafórica por escenario — '+context,
        f'outputs/peachtree6/signals_{context}_{{BASE,E1,E2,E3}}.json;outputs/peachtree6/signal_changes_by_cycle.csv;outputs/peachtree6/scenario_design_freeze.json',
        subtitle=f'Comparación de fases en 11th y 12th · progresión diseñada para SB · {CONTEXT}<br>V: verde nominal aplicado · A: amarillo · C: ciclo · rangos de ciclos completos')
    fig.update_layout(barmode='overlay',margin=dict(t=240,b=180),legend=dict(y=1.12))
    fig.update_yaxes(tickvals=list(range(8)),ticktext=[f'{mode} · {street}' for mode in reversed(ORDER) for street in ['12th','11th']],range=[-.7,7.7],title=None)
    fig.update_xaxes(title='Tiempo simulado (s)',range=[0,625],tickvals=[0,100,200,300,400],showgrid=False)
    note(fig,f'SB · 12th → 11th · progresión {design["PROGRESSION_TRAVEL_TIME"]:.2f} s · offset BASE {design["BASE_OFFSET"]:.2f} s → E2 {design["E2_OFFSET"]:.2f} s',y=1.25)
    note(fig,f'E1: +10% GREEN Through nominal · incremento real {changes.increment_s.min():.1f}–{changes.increment_s.max():.1f} s<br>E2: offset shift = {design["OFFSET_SHIFT_SECONDS"]:.2f} s · E3: E1 + offset E2',y=-.12)
    return fig

def departures(context='B2'):
    source='outputs/peachtree6/temporal_departures.csv';d=read_csv(source);d=d[d.context.eq(context)&d.direction.eq('ALL')]
    p=d.groupby(['scenario','bin_end_s']).cumulative_departures.mean().reset_index()
    fig=px.line(p,x='bin_end_s',y='cumulative_departures',color='scenario',color_discrete_map=COLORS,category_orders={'scenario':ORDER})
    # Exact quantiles are preserved in scenario_summary; temporal_departures contains 30s bins only.
    summary=read_csv(f'outputs/peachtree6/{context.lower()}_scenario_summary.csv')
    q=summary[summary.metric.isin(['departure_t50_s','departure_t90_s','departure_final_s'])].pivot(index='scenario',columns='metric',values='mean')
    lines=['<b>Escenario · t50 / t90 / tFinal (s)</b>']
    for mode in ORDER:
        r=q.loc[mode];lines.append(f'<span style="color:{COLORS[mode]}"><b>{mode}</b></span> · {r.departure_t50_s:.2f} / {r.departure_t90_s:.2f} / {r.departure_final_s:.2f}')
    style(fig,'Progresión de salidas acumuladas — '+context,source+f';outputs/peachtree6/{context.lower()}_scenario_summary.csv','Salidas acumuladas (vehículos)',
        f'Media de 30 réplicas · una salida más temprana indica mejor descarga temporal<br>{CONTEXT}<br>{SCENARIOS}')
    note(fig,'<br>'.join(lines),x=.02,y=.97);fig.layout.annotations[-1].xanchor='left'
    delta=q.loc['BASE','departure_final_s']-q.loc['E1','departure_final_s']
    note(fig,f'E1 adelanta la salida final media {delta:.2f} s frente a BASE.<br>Hitos exactos del resumen oficial; curvas agregadas en intervalos de 30 s.',y=-.13)
    fig.update_layout(margin=dict(t=230,b=160),legend=dict(y=1.10));fig.update_xaxes(title='Tiempo simulado (s)');return fig

def space_time(context='B2',mode='BASE',end_time=400):
    d=pd.read_parquet(ROOT/f'outputs/peachtree6/illustrative_{context}_{mode}.parquet');d=d[d.time.le(end_time)&d.frame.mod(5).eq(0)].copy()
    d['Dirección']=d.direction.map({2:'NB',4:'SB'})
    fig=px.line(d,x='time',y='y',line_group='id',color='Dirección',facet_col='Dirección',category_orders={'Dirección':['SB','NB']},color_discrete_map={'NB':'#008E84','SB':'#875F9A'},render_mode='svg')
    fig.update_traces(line_width=1,opacity=.55,showlegend=False)
    for a in fig.layout.annotations:a.text=a.text.replace('Dirección=','')
    refs=read_json('outputs/peachtree3u/structural_model_freeze.json')['signal_control_references']
    for col,di in [(1,4),(2,2)]:
        for i,street in [(2,'11th'),(3,'12th')]:
            fig.add_hline(y=refs[f'{i}/{di}'],line_dash='dot',line_color='#334155',line_width=1.5,row=1,col=col,
                annotation_text=f'{street} · {refs[f"{i}/{di}"]:.2f} ft',annotation_position='top left',annotation_font_size=14)
    style(fig,'Trayectorias espacio–tiempo — '+mode,f'outputs/peachtree6/illustrative_{context}_{mode}.parquet;outputs/peachtree3u/structural_model_freeze.json',
        subtitle=f'Seed 7000 ilustrativa · cada línea representa un vehículo · contexto {context}<br>{CONTEXT} · SB: sur · NB: norte<br>Controles efectivos empíricos: referencias del modelo, no barras pintadas')
    fig.update_xaxes(title='Tiempo simulado (s)');fig.update_yaxes(title='Posición longitudinal del frente, Local_Y (ft)')
    note(fig,'Cómo leer: línea inclinada → movimiento · tramo horizontal → detenido · líneas agrupadas → acumulación / cola',y=-.16)
    fig.update_layout(margin=dict(t=205,b=150),showlegend=False);return fig

def emergent_chart():
    keys=['RED_queue_mean','GREEN_queue_mean','peak_active','vehicles_multiple_stops']
    titles=['Cola media durante fase roja','Cola media durante fase verde','Máximo de vehículos activos','Vehículos con múltiples detenciones']
    d=read_csv('outputs/peachtree6/emergent_behavior.csv').groupby(['context','scenario'])[keys].mean().reset_index()
    fig=make_subplots(rows=2,cols=2,subplot_titles=titles,vertical_spacing=.25,horizontal_spacing=.12)
    for j,key in enumerate(keys):
        for c in ['B1','B2']:
            g=d[d.context.eq(c)].set_index('scenario').reindex(ORDER)
            fig.add_trace(go.Bar(x=ORDER,y=g[key],name=c+' — '+('VALIDATION' if c=='B1' else 'TRAIN'),legendgroup=c,
                marker_color=COLORS[c],offsetgroup=c,showlegend=j==0,text=[f'{v:.2f}' for v in g[key]],textposition='outside',cliponaxis=False,textfont_size=16),row=j//2+1,col=j%2+1)
        fig.update_yaxes(title='Vehículos en cola' if j<2 else 'Vehículos',range=[0,d[key].max()*1.35],row=j//2+1,col=j%2+1)
        fig.update_xaxes(title='Escenario',categoryorder='array',categoryarray=ORDER,row=j//2+1,col=j%2+1)
    style(fig,'Comportamiento colectivo: colas, acumulación y detenciones','outputs/peachtree6/emergent_behavior.csv',
        subtitle=f'Medias de 30 réplicas · los máximos son máximos por réplica promediados<br>{CONTEXT}<br>{SCENARIOS}')
    fig.update_layout(barmode='group',margin=dict(t=240,b=130),height=900,legend=dict(y=1.15))
    claims=[]
    for key,label in [('peak_active','acumulación máxima'),('vehicles_multiple_stops','vehículos con múltiples detenciones')]:
        if all(d[(d.context==c)&(d.scenario=='E1')][key].iloc[0]<d[(d.context==c)&(d.scenario=='BASE')][key].iloc[0] for c in ['B1','B2']):claims.append(label)
    if claims:note(fig,'E1 reduce '+' y '.join(claims)+' en ambos contextos.',y=-.18)
    return fig

def robustness_chart():
    d=read_csv('outputs/peachtree6/robustness_summary.csv');d=d[d.metric.eq('travel_mean_s')]
    fig=go.Figure()
    for c in ['B1','B2']:
        g=d.set_index('scenario').reindex(ORDER[1:]);v=g[c+'_effect']
        fig.add_trace(go.Bar(x=ORDER[1:],y=v,name=c+' — '+('VALIDATION' if c=='B1' else 'TRAIN'),marker_color=COLORS[c],text=[f'{x:+.2f} s' for x in v],textposition='outside',cliponaxis=False))
    style(fig,'Robustez del cambio en tiempo de recorrido','outputs/peachtree6/robustness_summary.csv','Cambio frente a BASE (s)',
        f'Media del efecto por contexto · negativo = mejora · positivo = empeora<br>{CONTEXT}<br>{SCENARIOS}')
    fig.update_layout(barmode='group',margin=dict(t=230,b=130),legend=dict(y=1.10));fig.update_xaxes(title='Escenario')
    fig.add_hline(y=0,line_color='#334155');vals=d[['B1_effect','B2_effect']].to_numpy();fig.update_yaxes(range=[vals.min()*1.3,vals.max()*1.3])
    note(fig,'E1 mejora ambos contextos; E2 y E3 mejoran B2, pero empeoran B1.',y=-.15);return fig

def validation_distribution(key):
    names={'speed':('Velocidad','ft/s'),'headway':('Distancia entre frentes','ft'),'travel':('Tiempo de recorrido','s'),'duration':('Duración de detenciones completas','s')}
    measure,unit=names[key];fig=go.Figure();lines=[];sources=[]
    for prefix,label,color in [('REAL','Observado B1','#C5762D'),('SIM','Simulado B1 · seed 6000','#486A95')]:
        source=f'outputs/peachtree5/{prefix}_B1_{key}.npy';sources.append(source);x=np.load(ROOT/source)
        support,count=np.unique(x,return_counts=True);cdf=np.cumsum(count)/len(x)
        fig.add_trace(go.Scatter(x=support,y=cdf,mode='lines',line=dict(shape='hv',color=color,width=2),name=label))
        lines.append(f'<b>{label}</b>: N {len(x):,} · Media {x.mean():.2f} · Mediana {np.median(x):.2f} · SD {x.std(ddof=1):.2f} {unit}')
    style(fig,measure+' — distribución de validación',';'.join(sources),'Proporción acumulada',
        subtitle='B1 — VALIDATION · observado frente a simulación ilustrativa predeclarada (seed 6000)<br>Curva acumulada: proporción de observaciones con valor menor o igual al del eje horizontal')
    fig.update_xaxes(title=measure+' ('+unit+')');fig.update_yaxes(tickformat='.0%',range=[0,1.04])
    note(fig,'<br>'.join(lines),x=1,y=.22)
    fig.update_layout(margin=dict(t=225),height=800);return fig

def validation_departures():
    fig=go.Figure();lines=[];sources=[]
    horizon=read_json('outputs/peachtree5/b1_exogenous_inputs.json')['horizon_s'];bins=np.arange(0,horizon+30,30)
    for prefix,label,color in [('REAL','Observado B1','#C5762D'),('SIM','Simulado B1 · seed 6000','#486A95')]:
        source=f'outputs/peachtree5/{prefix}_B1_exits.npy';sources.append(source);x=np.load(ROOT/source);counts,_=np.histogram(x,bins);j=int(np.argmax(counts))
        fig.add_trace(go.Scatter(x=bins[:-1],y=counts,mode='lines',line=dict(shape='hv',color=color,width=2),name=label))
        lines.append(f'<b>{label}</b>: {len(x)} salidas · máximo {counts[j]} veh/30 s en [{bins[j]:.0f}, {bins[j+1]:.0f}) s')
    style(fig,'Salidas por intervalo — validación B1',';'.join(sources),'Salidas (vehículos / 30 s)',
        subtitle='B1 — VALIDATION · observado frente a simulación ilustrativa predeclarada (seed 6000)<br>Intervalos de 30 s · conteo de cruces de salida del alcance congelado')
    fig.update_xaxes(title='Tiempo simulado (s)');note(fig,'<br>'.join(lines),x=1,y=1.03)
    fig.update_layout(margin=dict(t=225),height=800);return fig
