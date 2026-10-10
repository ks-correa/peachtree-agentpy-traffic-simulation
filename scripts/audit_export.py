"""Reopen I-80 feasibility from an immutable export; retain raw numeric tokens.

This audit profiles all rows and deliberately stops dependent analyses when the
requested location is absent. It must not silently reuse another site's data.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import time
from collections import Counter
from pathlib import Path

from scripts.evaluate_local import digest, peak_memory_mb

ROOT = Path(__file__).resolve().parents[1]
MISSING = {'', 'NA', 'N/A', 'NULL', 'NAN'}
INTEGER = re.compile(r'[+-]?\d+')
DECIMAL = re.compile(r'[+-]?\d+\.\d+')
US_GROUPED = re.compile(r'[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?')
COMMA_EXP = re.compile(r'[+-]?\d+,\d+[eE][+-]?\d+')
DOT_GROUPED = re.compile(r'[+-]?\d{1,3}(?:\.\d{3}){2,}')
BLOCKED = 'NO_I80_ROWS_IN_EXPORT'
EQUIVALENTS = {
    'Vehicle_ID':'Vehicle_ID', 'Frame_ID':'Frame_ID', 'Total_Frames':'Total_Frames',
    'Global_Time':'Global_Time', 'Local_X':'Local_X', 'Local_Y':'Local_Y',
    'Global_X':'Global_X', 'Global_Y':'Global_Y', 'Vehicle_Length':'v_length',
    'Vehicle_Width':'v_Width', 'Vehicle_Class':'v_Class', 'Velocity':'v_Vel',
    'Acceleration':'v_Acc', 'Lane_ID':'Lane_ID', 'Preceding':'Preceding',
    'Following':'Following', 'Space_Headway':'Space_Headway', 'Time_Headway':'Time_Headway',
}


def token_kind(value):
    value = value.strip()
    if value.upper() in MISSING: return 'missing'
    if INTEGER.fullmatch(value): return 'integer_literal'
    if DECIMAL.fullmatch(value): return 'dot_decimal_literal'
    if US_GROUPED.fullmatch(value): return 'comma_grouped_candidate'
    if COMMA_EXP.fullmatch(value): return 'comma_decimal_scientific'
    if DOT_GROUPED.fullmatch(value): return 'multiple_dot_groups_ambiguous'
    return 'text_or_other'


def i80_location(value):
    # Exact site identity, allowing only presentation whitespace/case.
    return value.strip().casefold() == 'i-80'


def read_rows(path):
    with path.open('r', encoding='utf-8-sig', newline='') as stream:
        sample = stream.read(16384)
        stream.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=';,\t')
        reader = csv.reader(stream, dialect)
        header = next(reader)
        yield header, dialect.delimiter
        for row in reader:
            if row: yield row


def profile_export(source, subset):
    iterator = read_rows(source)
    columns, delimiter = next(iterator)
    if len(set(columns)) != len(columns): raise ValueError('Duplicate column names')
    index = {name:i for i,name in enumerate(columns)}
    if 'Location' not in index: raise ValueError('Missing Location: cannot certify site')
    kinds = {c:Counter() for c in columns}
    missing = Counter(); examples = {c:{} for c in columns}
    locations = Counter(); ids = {}; frames = {}; timestamps = {}; lanes = {}
    malformed = 0; total = 0; selected = 0
    subset.parent.mkdir(parents=True, exist_ok=True)
    with subset.open('w', encoding='utf-8', newline='') as target:
        writer = csv.writer(target, delimiter=delimiter); writer.writerow(columns)
        for row in iterator:
            total += 1
            if len(row) != len(columns): malformed += 1; continue
            location = row[index['Location']]
            locations[location] += 1
            for col, value in zip(columns, row):
                kind = token_kind(value); kinds[col][kind] += 1
                if kind == 'missing': missing[col] += 1
                if kind not in examples[col]: examples[col][kind] = value
            ids.setdefault(location,set()).add(row[index['Vehicle_ID']])
            frames.setdefault(location,set()).add(row[index['Frame_ID']])
            timestamps.setdefault(location,Counter())[row[index['Global_Time']]] += 1
            lanes.setdefault(location,set()).add(row[index['Lane_ID']])
            if i80_location(location):
                selected += 1; writer.writerow(row)
    sites = {}
    for site, n in locations.items():
        raw_times = timestamps[site]
        raw_integers = sorted(int(v) for v in raw_times if INTEGER.fullmatch(v))
        deltas = Counter(b-a for a,b in zip(raw_integers,raw_integers[1:]))
        raw_frames = frames[site]
        integer_frames = [int(v) for v in raw_frames if INTEGER.fullmatch(v)]
        sites[site] = {
            'rows':n, 'unique_vehicle_id_literals':len(ids[site]),
            'unique_frame_id_literals':len(raw_frames),
            'frame_id_integer_literal_min':min(integer_frames) if integer_frames else None,
            'frame_id_integer_literal_max':max(integer_frames) if integer_frames else None,
            'frame_id_noninteger_literals':sorted(v for v in raw_frames if not INTEGER.fullmatch(v))[:10],
            'unique_global_time_literals':len(raw_times),
            'global_time_most_common_literals':raw_times.most_common(5),
            'global_time_integer_literal_min':raw_integers[0] if raw_integers else None,
            'global_time_integer_literal_max':raw_integers[-1] if raw_integers else None,
            'global_time_unique_integer_delta_modes':deltas.most_common(5),
            'global_time_other_examples':[v for v in raw_times if not INTEGER.fullmatch(v)][:5],
            'lane_id_literals':sorted(lanes[site]),
            'calendar_time_and_sampling_hz':'NOT_CERTIFIABLE_FROM_THIS_TRANSFORMED_EXPORT',
        }
    return {
        'file_bytes':source.stat().st_size, 'delimiter':delimiter, 'rows':total,
        'column_count':len(columns), 'columns_exact':columns, 'malformed_rows':malformed,
        'missing_token_policy':sorted(MISSING),
        'column_profiles':{c:{'storage_type':'CSV_TEXT','lexical_types':dict(kinds[c]),
            'missing_count':missing[c], 'examples_by_type':examples[c]} for c in columns},
        'locations_exact':dict(locations), 'site_profiles':sites,
        'equivalent_columns':{k:v if v in index else None for k,v in EQUIVALENTS.items()},
        'i80_rows':selected, 'i80_vehicle_ids':len(set().union(*(v for k,v in ids.items() if i80_location(k)))) if selected else 0,
        'rows_plus_header_equals_1048576':total+1 == 1048576,
    }


def write_csv(path, columns, rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns); writer.writeheader(); writer.writerows(rows)


def preserve_previous(root):
    archive=root/'outputs/archive/audit_without_trajectories'
    marker=archive/'manifest.json'
    if marker.exists(): return json.loads(marker.read_text(encoding='utf-8'))
    archive.mkdir(parents=True,exist_ok=True)
    sources=[root/'docs/ngsim_i80_feasibility.md']
    sources += list((root/'outputs').glob('*.csv')) + list((root/'outputs').glob('*.json'))
    sources += [root/'outputs/ngsim_final_feasibility_report.md',root/'outputs/figures/README.md']
    files={}
    for source in sources:
        if source.exists():
            rel=source.relative_to(root); dest=archive/rel
            dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,dest)
            files[str(rel)]=digest(source)
    result={'label':'AUDIT_WITHOUT_TRAJECTORIES','files_sha256':files}
    marker.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def blocked_outputs(out):
    write_csv(out/'i80_period_summary.csv',
        ['period','start','end','rows','vehicles','frames','duration','lanes','status'],
        [dict(period='NONE_DETECTED',start='',end='',rows=0,vehicles=0,frames=0,duration='',lanes='',status=BLOCKED)])
    write_csv(out/'i80_car_following_summary.csv',
        ['metric','n','value','pearson','spearman','status'],
        [dict(metric=m,n=0,value='',pearson='',spearman='',status=BLOCKED) for m in
         ['valid_leader_percentage','valid_follower_percentage','missing_leader_references','missing_follower_references','reciprocity','acceleration_vs_space_headway','acceleration_vs_relative_speed','acceleration_vs_ego_speed','space_headway_distribution','time_headway_distribution']])
    write_csv(out/'i80_lane_change_summary.csv',
        ['metric','value','status'],[dict(metric=m,value='',status=BLOCKED) for m in
        ['total_changes','vehicles_with_changes','changes_per_vehicle','origin_destination','speed_at_change','headway_before','headway_after','event_time']])
    write_csv(out/'i80_train_test_comparison.csv',
        ['strategy','train','test','train_rows','test_rows','train_vehicles','test_vehicles','vehicle_id_overlap','traffic_condition','distribution_shift','leakage','status'],
        [dict(strategy=s,train=tr,test=te,train_rows='',test_rows='',train_vehicles='',test_vehicles='',vehicle_id_overlap='',traffic_condition='NOT_EVALUABLE',distribution_shift='NOT_EVALUABLE',leakage='NOT_VERIFIABLE',status=BLOCKED)
         for s,tr,te in [('A','P1+P2','P3'),('B','P1','P2'),('C','Earlier complete trajectory blocks','Later complete trajectory block')]])
    write_csv(out/'i80_transferability.csv',
        ['indicator','train_n','test_n','difference_mean','difference_median','ks','wasserstein','status'],
        [dict(indicator=m,train_n=0,test_n=0,difference_mean='',difference_median='',ks='',wasserstein='',status=BLOCKED)
         for m in ['speed','acceleration','space_headway','time_headway','vehicle_class','lane_change_frequency']])
    params=[('desired_free_speed','CALIBRATED','Free-flow candidates are not observed desired speed'),
        ('acceleration_behavior','DATASET_DERIVED','Empirical acceleration; condition on ego and leader'),
        ('braking_behavior','DATASET_DERIVED','Empirical negative acceleration'),
        ('gap_response','CALIBRATED','Conditional response; causal reaction not identified by correlation'),
        ('relative_speed_response','CALIBRATED','Conditional acceleration response'),
        ('headway_distribution','DATASET_DERIVED','Valid non-sentinel same-time interactions'),
        ('vehicle_classes','DATASET_DERIVED','Per-vehicle class proportions'),
        ('arrivals','DATASET_DERIVED','Boundary crossings, not arbitrary first observation'),
        ('lane_change_frequency','DATASET_DERIVED','Contiguous transitions per vehicle exposure'),
        ('merge_behavior','CALIBRATED','Requires I-80 geometry and trajectory evidence')]
    write_csv(out/'i80_parameter_identifiability.csv',
        ['parameter','source','method','classification','identifiable','future_use','status'],
        [dict(parameter=p,source='I80 TRAIN (absent)',method=m,classification=c,identifiable=False,
            future_use='Conditional future method; no parameter estimated',status=BLOCKED) for p,c,m in params])


def build_report(audit):
    p=audit['export']; lines=[
        '# Reevaluación de factibilidad NGSIM I-80 con export.csv',
        '', '**C. NOT_VIABLE_FOR_AGENTPY para las fuentes locales actuales.**',
        '', 'La decisión se recalculó tras leer todas las filas de export.csv. El archivo sí contiene registros con estructura de trayectorias, pero sus únicas ubicaciones son peachtree y us-101. No contiene I-80. El nuevo motivo es NO_I80_ROWS_IN_EXPORT, no la ausencia general de un archivo de trayectorias.',
        '', '## Fuente, alcance y preservación',
        '', f"Archivo: `data/export.csv`, {p['file_bytes']:,} bytes, SHA-256 `{audit['source_sha256']}`. La procedencia oficial es declarada por el usuario; no se verificó una URL o checksum remoto. Se auditó el archivo local íntegro, sin muestreo ni modificación.",
        '', 'La auditoría anterior SIN trayectorias está conservada en `outputs/archive/audit_without_trajectories/`, con manifest.json y hashes. Los CSV/JSON antiguos permanecen en outputs como resultados históricos; los resultados vigentes usan el prefijo i80_.',
        '', 'El ZIP de apoyo ya inventariado no contiene trayectorias. Su integridad frente al hash anterior se comprobó. Falta I-80 Metadata Documentation.pdf. El PDF de US-101 no se utilizó para interpretar I-80. Su ausencia por sí sola no determinaría una clasificación negativa si hubiera trayectorias I-80.',
        '', '## 1. Inspección completa del CSV',
        '', f"{p['rows']:,} filas de datos; {p['column_count']} columnas; separador `{p['delimiter']}`; {p['malformed_rows']} filas con ancho incorrecto. Los tipos son perfiles léxicos del CSV, sin coerción numérica destructiva.",
        '', '| Location exacto | Filas | Vehicle_ID literales distintos | Frame_ID literales distintos | Global_Time literales distintos |',
        '|---|---:|---:|---:|---:|']
    for site,s in p['site_profiles'].items():
        lines.append(f"| {site} | {s['rows']} | {s['unique_vehicle_id_literals']} | {s['unique_frame_id_literals']} | {s['unique_global_time_literals']} |")
    lines += ['', 'IDs distintos no equivalen a vehículos físicos únicos si hay reinicios de IDs entre periodos. No se mezclaron ubicaciones ni se analizaron sus interacciones como sustituto de I-80.',
        '', '| Columna exacta | Tipos léxicos y conteos | Faltantes (vacío/NA/N/A/NULL/NAN) |', '|---|---|---:|']
    for col,v in p['column_profiles'].items():
        lines.append(f"| {col} | {', '.join(f'{k}: {n}' for k,n in v['lexical_types'].items())} | {v['missing_count']} |")
    lines += ['', 'Equivalencias por nombre presentes: `v_length` → Vehicle_Length; `v_Width` → Vehicle_Width; `v_Class` → Vehicle_Class; `v_Vel` → Velocity; `v_Acc` → Acceleration. Las demás variables solicitadas tienen su nombre esperado. Esto confirma esquema, no unidades o calidad.',
        '', '### Tiempo y riesgos del formato',
        '', 'Se conservan tokens como `1,11885E+12`, `1,156`, `2,195.462` y `2.230.502.921`. Hay mezcla de notación científica con coma, agrupación con comas y múltiples puntos. No se eliminaron separadores ni se reconstruyeron dígitos perdidos.',
        '', 'El número de filas más cabecera es exactamente 1.048.576, y los formatos son compatibles con una transformación mediante hoja de cálculo. Es una señal de posible límite/truncamiento y transformación, no prueba de qué programa o proceso lo causó. No se certifica esta copia como exportación completa o fiel del recurso oficial.']
    for site,s in p['site_profiles'].items():
        lines += ['', f"**{site}:** Frame_ID enteros literales entre {s['frame_id_integer_literal_min']} y {s['frame_id_integer_literal_max']}; Global_Time enteros literales entre {s['global_time_integer_literal_min']} y {s['global_time_integer_literal_max']}; otros ejemplos: {s['global_time_other_examples']}. Tokens temporales más frecuentes: {s['global_time_most_common_literals']}. Diferencias más frecuentes entre valores enteros distintos: {s['global_time_unique_integer_delta_modes']} (unidades crudas, no Hz)."]
    lines += ['', 'No puede certificarse un rango calendario ni frecuencia vehicular física desde estos tiempos transformados. En particular, un timestamp constante o abreviado no permite reconstruir subsegundos; Frame_ID por sí solo tampoco certifica una tasa física. Ningún tiempo de otra ubicación se presenta como periodo I-80.',
        '', '## 2–3. Filtro I-80 y periodos',
        '', 'Filtro reproducible: Location.strip().casefold() == "i-80". Los únicos valores reales son peachtree y us-101. Resultado: **0 filas y 0 identificadores I-80 en este archivo**. Se escribió `outputs/working/i80_trajectories_raw.csv` con cabecera y cero filas, junto con un manifiesto explícito de subconjunto vacío. No se identificó ningún valor que represente I-80.',
        '', 'No se detectaron periodos I-80. Los nombres 16:00–16:15, 17:00–17:15 y 17:15–17:30 del ZIP son referencias de informes históricos, no bloques observados en export.csv. No se asignaron cortes temporales ficticios.',
        '', '## 4–9. Trayectorias, interacciones y dinámica I-80',
        '', 'Duplicados Vehicle_ID+Frame_ID, monotonicidad, gaps, posiciones, duraciones, aceleración, carriles, cambios de carril, reciprocidad y referencias leader/follower: NOT_EVALUABLE para I-80. Observaciones por vehículo y porcentaje de trayectorias con gaps son nulos, no cero. Las columnas Preceding/Following y headways existen globalmente, pero no hay población I-80 sobre la cual calcular porcentajes.',
        '', 'Interacciones utilizables: no calculable (denominador I-80 = 0), no 0 %. Correlaciones Pearson/Spearman, bins y distribuciones car-following no se ejecutaron. Cambios de carril: no calculables; no se afirma ausencia de eventos reales.',
        '', 'Incorporación: sin evidencia vehicular I-80; geometría e interpretación de rampa PENDING_I80_METADATA, adicionalmente bloqueadas por NO_I80_ROWS_IN_EXPORT. Los archivos CAD/GIS no bastan para inventar eventos.',
        '', 'Congestión: velocidad media/mediana/P10/P90, headways, vehículos activos, flujo, densidad, frenadas, colas y cambios de carril I-80 no calculables. No se asignan etiquetas free flow/transición/congestión.',
        '', '## 10–11. TRAIN/TEST y transferibilidad',
        '', 'A: P1+P2 → P3; B: P1 → P2; C: bloques tempranos → bloque posterior. Ninguna puede materializarse: no hay periodos I-80. Los conteos de particiones y solapamiento son desconocidos/no aplicables, no resultados de una partición exitosa. No se efectuó random split ni se usó otro sitio como TRAIN o TEST.',
        '', 'A queda como candidato condicional si se obtienen los tres bloques completos. Antes de elegirlo, comprobar identidad física/IDs entre periodos y posibles trayectorias en la frontera, asignando cada trayectoria íntegra a una sola partición o excluyendo las que crucen fronteras según una regla previa. Prefijar IDs por periodo no demuestra independencia física. No puede recomendarse una estrategia efectiva hoy.',
        '', 'PRE-MODEL TRANSFERABILITY CHECK: NOT_RUN. Diferencias de media/mediana, KS y Wasserstein vacíos para speed, acceleration, space_headway, time_headway, vehicle_class y lane_change_frequency. Clase vehicular requeriría comparar proporciones categóricas; no corresponde tratar sus códigos como magnitudes continuas. No se fijaron umbrales de aceptación.',
        '', '## 12–14. Parámetros, validación y escenarios',
        '', 'No se estimó ningún parámetro I-80. Con TRAIN adecuado, distribuciones de aceleración/frenado/headway, clases, llegadas en fronteras y tasas de cambios serían DATASET_DERIVED. Desired/free speed, respuesta a gap/velocidad relativa y aceptación de incorporaciones requerirían CALIBRATED, con identificabilidad explícita. Headway observado no equivale a tiempo de reacción; velocidad en congestión no equivale a velocidad deseada. Unidades, geometría o respuesta latente sin evidencia serían ASSUMPTION, no valores inventados.',
        '', 'Ningún indicador tiene TEST I-80 disponible. Candidatos PRIMARY futuros: velocidad/distribución, flujo por sección, headway, tiempo de recorrido entre fronteras y throughput. SECONDARY: aceleración, cambios de carril, densidad y congestión/cola. Se aceptarían sólo con medición equivalente en simulación y datos; recorrido requiere cobertura de ambas fronteras, densidad exige longitud/carriles y colas una definición operacional.',
        '', 'E1 modificaría ingreso por rampa; E2 reglas/objetivos de velocidad; E3 ambos. Sus parámetros serían EXPERIMENTAL y sus resultados contrafactuales sobre un baseline primero calibrado con TRAIN y validado con TEST. No se afirma validación directa de estas intervenciones con NGSIM histórico. Aquí son posibilidades conceptuales, no escenarios implementables con evidencia suficiente.',
        '', '## Pruebas y reproducción',
        '', 'Ejecutar desde la raíz: `python -m scripts.audit_export`; pruebas: `python -m unittest discover -s tests -v`. El auditor usa biblioteca estándar, conserva tokens originales y hashes, recorre todas las filas y crea sólo resultados de factibilidad. Los tests verifican parser, clasificación de formatos, filtro de ubicación, exclusión de otros sitios, nulos en métricas bloqueadas, preservación histórica, integridad y resultados reproducibles. Las pruebas sobre interacciones/periodos reales I-80 permanecen pendientes por ausencia de esa población.',
        '', 'Resultados de la suite ejecutada: `outputs/i80_test_summary.json`; detalle: `outputs/i80_test_results.txt`. Las pruebas omitidas pertenecen a la auditoría histórica y no certifican interacciones I-80. La verificación independiente de ubicación vuelve a recorrer el CSV completo.',
        '', f"Rendimiento de esta ejecución: {audit['performance']['elapsed_seconds']} s, {audit['performance']['peak_process_working_set_mb']} MB de peak working set del proceso; {p['rows']} filas inspeccionadas. No representa rendimiento del futuro ABM.",
        '', '## 15. Decisión',
        '', '**C. NOT_VIABLE_FOR_AGENTPY — DESCARTAR NGSIM con la copia local actual para el proyecto I-80.** Se reabrió la evaluación y se obtuvo evidencia nueva: export.csv contiene otros sitios y señales de transformación numérica. Esta conclusión no rechaza el conjunto oficial completo ni determina la viabilidad de un proyecto distinto con US-101/Peachtree.',
        '', 'Para reabrir la factibilidad I-80 hace falta una descarga que incluya explícitamente Location=i-80, sin límite de filas ni conversión por hoja de cálculo, preservando timestamps completos. La metadata I-80 sigue pendiente y debe documentar unidades/rampa. No se construyeron AgentPy, escenarios, modelos de seguimiento ni interfaz.', '']
    return '\n'.join(lines)


def main():
    start=time.perf_counter(); source=ROOT/'data/export.csv'; out=ROOT/'outputs'
    before=digest(source); history=preserve_previous(ROOT)
    p=profile_export(source,out/'working/i80_trajectories_raw.csv')
    if p['i80_rows']:
        raise RuntimeError('I-80 now present: run a full trajectory analysis; absent-site report must not be reused')
    supporting=ROOT/'data/I-80-Emeryville-CA.zip'
    old=json.loads((out/'data_quality_audit.json').read_text(encoding='utf-8'))
    old_zip_hash=next(v for k,v in old['sources'].items() if k.endswith('.zip'))
    supporting_unchanged=digest(supporting)==old_zip_hash
    if not supporting_unchanged: raise RuntimeError('Supporting ZIP changed; repeat its inventory')
    assert digest(source)==before,'Source changed during audit'
    checks=['vehicle_frame_duplicates','vehicle_time_monotonicity','temporal_continuity','position_monotonicity','trajectory_duration','observations_per_vehicle','trajectories_with_gaps','velocity','acceleration','lane_id','leader_validity','follower_validity','reciprocity','headways','car_following_correlations','lane_changes','congestion','train_test_isolation','physical_vehicle_overlap']
    audit={'audit_scope':'LOCAL_EXPORT_REOPENED_I80','classification':'NOT_VIABLE_FOR_AGENTPY',
        'reason':BLOCKED,'source':'data/export.csv','source_sha256':before,'source_unchanged':True,
        'supporting_zip_unchanged':supporting_unchanged,'previous_audit_archive':'outputs/archive/audit_without_trajectories',
        'export':p,'i80_periods':[], 'i80_metadata_status':'MISSING',
        'ramp_metadata_status':'PENDING_I80_METADATA',
        'i80_checks':{k:{'status':'NOT_EVALUABLE','value':None,'reason':BLOCKED} for k in checks},
        'transferability_status':'NOT_RUN',
        'performance':{'elapsed_seconds':round(time.perf_counter()-start,3),'peak_process_working_set_mb':peak_memory_mb()}}
    (out/'i80_trajectory_audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'working/i80_subset_manifest.json').write_text(json.dumps({'source_sha256':before,'filter':'Location.strip().casefold() == i-80','rows':0,'status':BLOCKED,'subset_sha256':digest(out/'working/i80_trajectories_raw.csv')},indent=2),encoding='utf-8')
    blocked_outputs(out)
    report=build_report(audit)
    for dest in [ROOT/'docs/ngsim_i80_feasibility.md',out/'ngsim_final_feasibility_report.md']:
        dest.write_text(report,encoding='utf-8')
    print(json.dumps({'rows':p['rows'],'locations':p['locations_exact'],'sites':p['site_profiles'],'performance':audit['performance']},indent=2))


if __name__=='__main__': main()
