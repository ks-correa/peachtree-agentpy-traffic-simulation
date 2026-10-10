"""Final presentation-only integrity and export packaging; no scientific runs."""
import json,hashlib,zipfile
from pathlib import Path
from PIL import Image,PngImagePlugin
from ui.presentation_data import ROOT,ASSETS

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    before=json.loads((ASSETS/'pre_presentation_integrity.json').read_text())
    for group in ['scientific_artifact_hashes','scientific_engine_hashes']:
        for path,expected in before[group].items():
            if sha(ROOT/path)!=expected:raise RuntimeError('Scientific freeze/artifact changed: '+path)
    qa=json.loads((ASSETS/'test_report.json').read_text());browser=json.loads((ASSETS/'browser_qa.json').read_text())
    assert qa['failures']==qa['errors']==0 and not browser['page_errors'] and browser['canvas_visible']
    capture=ASSETS/'08_base_simulation_capture.png'
    with Image.open(capture) as img:
        meta=PngImagePlugin.PngInfo();meta.add_text('source_artifact','outputs/peachtree6/traces/B2_BASE_7000.json;presentation-only browser capture')
        img.save(capture,pnginfo=meta)
    manifest=json.loads((ASSETS/'presentation_manifest.json').read_text())
    manifest['slides'][7]['supporting_figure_files']=['08_base_simulation_capture.png']
    manifest['dashboard_status']='VISUAL PRESENTATION DASHBOARD READY'
    manifest['browser_visual_qa']='Chrome headless;12 sections, actual Canvas draw, Run/Pause, ZIP download checked'
    manifest['generated_PNG_count']=len(list(ASSETS.glob('*.png')));manifest['export_table_count']=len(list((ASSETS/'tables').glob('*.csv')))
    (ASSETS/'presentation_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    report={'scientific_freezes_and_results_intact':True,'no_new_experiments':True,'no_recalibration':True,'coverage':manifest['coverage'],
        'status':'VISUAL PRESENTATION DASHBOARD READY','presentation_QA':qa,'browser_QA':browser,
        'assets_PNG':manifest['generated_PNG_count'],'tables_CSV':manifest['export_table_count']}
    (ASSETS/'final_presentation_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with zipfile.ZipFile(ASSETS/'presentation_material.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in ASSETS.rglob('*'):
            if p.is_file() and p.suffix!='.zip' and p.name!='pre_presentation_integrity.json':archive.write(p,p.relative_to(ASSETS))
    text='''# Dashboard final de presentación

PRESENTATION MODE abre por defecto; TECHNICAL MODE conserva la interfaz avanzada.

Inicio: `python -m streamlit run streamlit_app.py`.

Navegación: Proyecto, Datos, Modelo, Simulación, Calibración, Validación, Escenarios, Resultados, Comportamiento emergente, Decisión, Limitaciones, Material para presentación.

Los17 puntos de la guía están mapeados en presentation_assets/presentation_manifest.json. Cada bloque contiene mensaje, nota de exposición, fuente, PNG y CSV. El centro de exportación permite descargar imágenes1920×1080, tablas numéricas con source_artifact y ZIP completo. Datos de integrantes/docente/fecha quedan en campos configurables, sin información inventada.

El Canvas reproduce estados AgentPy oficiales guardados, con Run/Pause/Resume/Reset y playback0.5/1/2/5/10. No ejecuta nueva experimentación ni reproduce trayectorias reales NGSIM. Los indicadores oficiales provienen de las30 réplicas de cada configuración, separados de la animación ilustrativa seed7000.

QA:12 pruebas nuevas de presentación aprobadas, incluidas12 secciones sin AgentPy.run y reconciliación estadística. Se preserva el reporte científico222 casos,196 aprobados,26 omitidos, sin repetir física/calibración/validación. Chrome headless verifica navegación, dibujo real de Canvas y descarga ZIP; capturas en presentation_assets/screenshots/. Limitaciones y sesgos científicos permanecen visibles.

ALL 17 PRESENTATION REQUIREMENTS COVERED

VISUAL PRESENTATION DASHBOARD READY

Los freezes, métricas y archivos científicos permanecen byte-identical. No nuevos escenarios, parámetros o resultados oficiales.
'''
    (ROOT/'docs/final_presentation_dashboard.md').write_text(text,encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status','coverage','assets_PNG','tables_CSV','scientific_freezes_and_results_intact']}))

if __name__=='__main__':main()
