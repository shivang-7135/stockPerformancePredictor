import streamlit as st

HTML = open("stitch_dashboard.html").read()

my_comp = st.components.v2.component(
    "stitch_dashboard",
    html=HTML,
    isolate_styles=True
)

my_comp()
