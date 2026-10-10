"""Refresh visual encoding only. Never rebuild statistics or scientific outputs."""
import hashlib,json,zipfile,re
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
from PIL import Image,ImageDraw,PngImagePlugin
from ui.presentation_data import *
from ui.static_charts import CONTEXT,SCENARIOS,note

TRANSLATIONS={'speed':'Velocidad','travel_time':'Tiempo de recorrido','Space_Headway':'Distancia entre frentes (headway)',
    'throughput_temporal_L1_normalized':'Error temporal de salidas (índice normalizado)',
    'scenario':'Escenario','PRE':'Antes de calibrar','FINAL':'Calibrado','REAL B2':'Observado B2','REAL B1':'Observado B1','SIM B1':'Simulado B1'}

def improve_cached(name,fig):
    source=fig.layout.meta['source_artifact'];title=fig.layout.title.text.split('<br>')[0]
    for old,new in TRANSLATIONS.items():title=title.replace(old,new)
    title=title.replace('tradeoffs','compromisos').replace('intervalos30s','intervalos de 30 s')
    subtitle='Evidencia y alcance del modelo · resultados congelados'
    if name.startswith('06_') or name in ['09_calibration','10_validation','12_scenario_table']:subtitle=CONTEXT
    old_annotations=[a for a in fig.layout.annotations if a.name!='static_reading' and not str(a.text).startswith(('SOURCE ARTIFACT:','Fuente:')) and not ('N ' in str(a.text) and 'SD ' in str(a.text))]
    fig.layout.annotations=old_annotations
    style(fig,title,source,subtitle=subtitle)
    for a in fig.layout.annotations:
        for old,new in TRANSLATIONS.items():a.text=a.text.replace(old,new)
    stats=table('descriptive_statistics.csv')
    if 'distribution' in name or 'boxplot' in name:
        variable=next(v for k,v in [('acceleration','acceleration'),('headway','Space_Headway'),('travel','travel_time'),('speed','speed')] if k in name)
        g=stats[stats.Variable.eq(variable)];unit=g.unit.iloc[0]
        measure={'speed':'Velocidad','acceleration':'Aceleración','Space_Headway':'Distancia entre frentes','travel_time':'Tiempo de recorrido'}[variable]
        label='Distribución de '+measure.lower() if 'distribution' in name else 'Resumen de '+measure.lower()
        fig.update_layout(title_text=label+'<br><sup>Observaciones reales · '+CONTEXT+'</sup>')
        lines=[]
        for c in ['B1','B2']:
            r=g[g.context.eq(c)].iloc[0]
            detail=f'Mediana {r.Median:.2f} · IQR {r.P75-r.P25:.2f} {unit}' if 'boxplot' in name else f'Media {r.Mean:.2f} · Mediana {r.Median:.2f} · SD {r.SD:.2f} {unit}'
            lines.append(f'<span style="color:{COLORS[c]}"><b>{c}</b></span> · N {int(r.N):,} · '+detail)
        note(fig,'<br>'.join(lines),x=1,y=1.02)
        fig.update_layout(margin=dict(t=215),legend=dict(y=1.12))
        if 'distribution' in name:
            fig.update_xaxes(title=measure+' ('+unit+')');fig.update_yaxes(title='Proporción de observaciones',tickformat='.0%')
        else:fig.update_xaxes(title='Contexto');fig.update_yaxes(title=measure+' ('+unit+')')
        for t in fig.data:
            c=t.name.split(' — ')[0];t.name=c+' — '+('VALIDATION' if c=='B1' else 'TRAIN')
            if 'boxplot' in name:t.x=[c]
        if 'boxplot' in name:fig.update_layout(boxmode='group',showlegend=False)
    elif name in ['09_calibration','10_validation']:
        for t in fig.data:
            t.name=TRANSLATIONS.get(t.name,t.name)
            t.x=[TRANSLATIONS.get(x,x) for x in t.x]
            t.text=[f'{y:.2f}' for y in t.y];t.textposition='outside';t.cliponaxis=False
            t.textfont=dict(size=17)
        for a in fig.layout.annotations:
            if a.text.startswith('Fuente:'):continue
            if 'throughput_' in a.text or 'Error temporal de salidas' in a.text:a.text='Error temporal de salidas (índice normalizado)'
        for k in fig.layout:
            if k.startswith('yaxis'):
                axis=getattr(fig.layout,k);axis.matches=None
                number=k.removeprefix('yaxis');traceaxis='y'+number if number else 'y'
                vals=[float(y) for t in fig.data if t.yaxis==traceaxis for y in t.y]
                if vals:axis.range=[0,max(vals)*1.3]
        fig.update_layout(margin=dict(t=210,b=110),legend=dict(y=1.18),height=850)
    elif name=='06_direction_frequency':
        for t in fig.data:
            t.text=[str(int(v)) for v in t.y];t.textposition='outside';t.cliponaxis=False
            c=t.name.split(' — ')[0];t.name=c+' — '+('VALIDATION' if c=='B1' else 'TRAIN')
        fig.update_yaxes(title='Vehículos',rangemode='tozero');fig.update_xaxes(title='Dirección · NB: norte · SB: sur')
    elif name=='06_arrivals':
        fig.update_xaxes(title='Tiempo simulado (s)');fig.update_yaxes(title='Llegadas (vehículos / 30 s)')
        lines=[]
        for t in fig.data:
            y=np.asarray(t.y,dtype=float);j=int(np.argmax(y));lines.append(f'{t.name}: máximo {y[j]:.0f} veh/30 s en {t.x[j]:.0f} s')
        note(fig,'<br>'.join(lines),x=1,y=.97)
    elif name=='12_scenario_table':
        h=list(fig.data[0].header.values);h[0]='Escenario';fig.data[0].header.values=h
        fig.update_layout(title_text='Resultados por escenario — B2<br><sup>Media de 30 réplicas · '+CONTEXT+'<br>'+SCENARIOS+'</sup>',margin=dict(t=190))
    elif name=='14_final_decision':
        fig.update_layout(title_text='Decisión: E1 recomendado dentro del alcance<br><sup>Mejora consistente en ambos contextos · '+CONTEXT+'</sup>')
        for a in fig.layout.annotations:
            a.text=a.text.replace('travel y stopping','recorrido y detenciones')
    elif name=='02_problem_scope':
        fig.update_xaxes(title='Posición longitudinal del frente, Local_Y (ft)')
        fig.update_layout(title_text='Corredor Peachtree Street: 11th–12th<br><sup>Alcance congelado · NB: norte · SB: sur · referencias de control efectivas, no barras pintadas</sup>')
    return fig

def export(name,fig):
    fig.update_layout(margin_b=210)
    if fig.layout.showlegend is not False:fig.update_layout(legend=dict(y=1.06,yanchor='bottom',x=0))
    for a in fig.layout.annotations:
        if str(a.text).startswith('Fuente:'):a.y=-.28
    fig.write_json(ASSETS/'charts'/(name+'.json'))
    fig.write_image(ASSETS/(name+'.png'),width=1920,height=1080,scale=1)
    with Image.open(ASSETS/(name+'.png')) as im:
        meta=PngImagePlugin.PngInfo();meta.add_text('source_artifact',fig.layout.meta['source_artifact']);im.save(ASSETS/(name+'.png'),pnginfo=meta)
    print(name,flush=True)

def audit(fig,name):
    annotations=' '.join(str(a.text) for a in fig.layout.annotations)
    title=fig.layout.title.text or ''
    kind='statistical_plot'
    if not fig.data:kind='explanatory_diagram'
    elif all(t.type=='table' for t in fig.data):kind='numeric_table'
    axes=[getattr(fig.layout,k) for k in fig.layout if k.startswith(('xaxis','yaxis'))]
    internal={'scenario','bin_end_s','value','metric','indicator','Valor','Unidades según indicador'}
    axes_clear=all(a.title.text not in internal for a in axes)
    bars=[t for t in fig.data if t.type=='bar']
    if 'distribution' in name:static=all(x in annotations for x in ['N ','Media','Mediana','SD'])
    elif 'boxplot' in name:static=all(x in annotations for x in ['N ','Mediana','IQR'])
    elif 'timeline' in name:static=all(x in annotations for x in ['V ','A ','C ','offset'])
    elif bars:static=all(t.text is not None and len(t.text)==len(t.y) for t in bars)
    elif 'paired' in name:static='IC95 [' in annotations
    elif 'departures' in name:static=all(x in annotations for x in ['t50','t90','tFinal'])
    elif 'space_time' in name:static='Cómo leer' in annotations and '11th' in annotations and '12th' in annotations
    elif 'arrivals' in name:static='máximo' in annotations
    else:static=bool(annotations) or kind=='numeric_table'
    fields=dict(filename=name+'.png',title_clear=bool(title and '<sup>' in title),axes_clear=axes_clear,
        units_visible=kind!='statistical_plot' or bool(re.search(r'\b(s|ft|vehículos|Vehículos|Proporción|índice|p\.p\.)\b|%',title+annotations+' '+' '.join(a.title.text or '' for a in axes))),
        static_values_visible=bool(static),legend_clear=all(t.name not in internal for t in fig.data),source_visible='Fuente:' in annotations,
        no_internal_labels=not any(x in title+annotations for x in ['Indicator=','Indicador=','context=','throughput_temporal_L1_normalized','Unidades según indicador']))
    fields['presentation_ready']=all(v for k,v in fields.items() if k!='filename')
    fields['figure_type']=kind;fields['source_artifact']=fig.layout.meta['source_artifact']
    return fields

def main(only=None):
    before=json.loads((ASSETS/'pre_chart_improvement_hashes.json').read_text())
    old={p.stem:hashlib.sha256(p.read_bytes()).hexdigest() for p in ASSETS.glob('*.png')}
    factories={'11_signal_timeline':lambda:timeline(),'12_travel_comparison':lambda:scenario_chart('B1+B2','travel_mean_s'),
        '12_stopping_comparison':lambda:scenario_chart('B1+B2','operational_stopped'),'12_directional_results':lambda:directional_chart('B1+B2'),
        '13_emergent_behavior':emergent_chart,'13_space_time_base':lambda:space_time(mode='BASE'),'13_space_time_e1':lambda:space_time(mode='E1'),
        '14_paired_effects':paired_chart,'14_paired_stopping':lambda:paired_chart('operational_stopped'),'14_robustness':robustness_chart,
        '12_departures_B1':lambda:departures('B1'),'12_departures_B2':lambda:departures('B2'),
        '10_validation_speed':lambda:validation_distribution('speed'),'10_validation_headway':lambda:validation_distribution('headway'),
        '10_validation_travel':lambda:validation_distribution('travel'),'10_validation_stopping':lambda:validation_distribution('duration'),
        '10_validation_throughput':validation_departures}
    names=sorted(set(p.stem for p in (ASSETS/'charts').glob('*.json'))|set(factories))
    rows=[]
    for name in names:
        if only is None or name in only:
            fig=factories[name]() if name in factories else improve_cached(name,assets_chart(name+'.json'))
            export(name,fig)
        else:fig=assets_chart(name+'.json')
        rows.append(audit(fig,name))
    after={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in before}
    assert before==after,'Scientific files changed'
    changed=[r['filename'] for r in rows if old.get(Path(r['filename']).stem)!=hashlib.sha256((ASSETS/r['filename']).read_bytes()).hexdigest()]
    report={'audited_figures':len(rows),'modified_or_added_figures':len(rows),'figures':rows,
        'scientific_files_verified':len(before),'scientific_result_hashes_intact':True,
        'temporal_source_note':'temporal_departures.csv supplies 30s curves; exact official mean t50/t90/tFinal are in scenario_summary.csv; no quantile inferred from bins.',
        'modified_files':changed,'export_dimensions':[1920,1080],'export_method':'Kaleido (no toolbar)',
        'visual_review':'pending','all_presentation_ready':all(r['presentation_ready'] for r in rows)}
    (ASSETS/'presentation_chart_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest=read_json('presentation_assets/presentation_manifest.json');manifest['chart_audit']='presentation_chart_audit.json'
    manifest['figures']=[{'filename':r['filename'],'source_artifact':r['source_artifact']} for r in rows]
    manifest['generated_PNG_count']=len(list(ASSETS.glob('*.png')))
    (ASSETS/'presentation_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    # Contact sheets for visual review, not presentation figures.
    for start in range(0,len(rows),6):
        sheet=Image.new('RGB',(1440,3*445),'white');draw=ImageDraw.Draw(sheet)
        for j,r in enumerate(rows[start:start+6]):
            with Image.open(ASSETS/r['filename']) as im:
                im.thumbnail((720,405));x=(j%2)*720;y=(j//2)*445;sheet.paste(im,(x,y));draw.text((x+10,y+410),r['filename'],fill='black')
        sheet.save(ASSETS/f'chart_review_{start//6+1}.jpg')
    print(json.dumps({k:report[k] for k in ['audited_figures','modified_or_added_figures','all_presentation_ready','scientific_result_hashes_intact']}))

if __name__=='__main__':main()
