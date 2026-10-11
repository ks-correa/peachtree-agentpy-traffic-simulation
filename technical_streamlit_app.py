"""Direct entry point for the current light technical simulation view."""
import streamlit as st
from ui.simulation_view import render_simulation

st.set_page_config(page_title='NGSIM Peachtree · Simulación técnica',page_icon='◈',layout='wide')
st.html('<style>.stApp{background:#ffffff;color:#102a43}[data-testid="stSidebar"]{background:#f4f7fb}.block-container{padding-top:4.5rem}</style>')
st.title('NGSIM Peachtree · Simulación técnica')
render_simulation(technical=True)
