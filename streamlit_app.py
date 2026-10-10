import streamlit as st
st.set_page_config(page_title='NGSIM Peachtree · Presentación',page_icon='◈',layout='wide')
mode=st.sidebar.selectbox('Modo',['PRESENTATION MODE','TECHNICAL MODE'],key='dashboard_mode')
if mode=='PRESENTATION MODE':
    from ui.presentation_app import main
else:
    from ui.simulation_view import render_simulation
    def main():
        st.html('<style>.stApp{background:#ffffff;color:#102a43}[data-testid="stSidebar"]{background:#f4f7fb}.block-container{padding-top:4.5rem}</style>')
        st.title('NGSIM Peachtree · Simulación técnica')
        render_simulation(technical=True)
main()
if mode=='TECHNICAL MODE':
    st.html('<style>[data-testid="stWidgetLabel"] p,[role="tab"],[data-testid="stMetricValue"],[data-testid="stMetricLabel"]{color:#102a43!important}</style>')
    with st.expander('Parámetros completos y artefactos de integridad'):
        import json
        import pandas as pd
        from ui.presentation_data import ROOT
        values=json.loads((ROOT/'outputs/peachtree4/final_parameters.json').read_text())['values']
        st.dataframe(pd.DataFrame([values]).style.format(precision=17))
        checks=json.loads((ROOT/'presentation_assets/pre_presentation_integrity.json').read_text())
        st.caption('Snapshot previo a la capa de presentación; los resultados científicos no se regeneran.')
        st.json(checks,expanded=False)
