from datetime import datetime
import streamlit as st


from pages import page_upload, page_analytics, page_details

st.set_page_config(page_title="Классификатор креативов", layout="wide")

page = st.navigation(
    {
        "Меню": [
            st.Page(page_upload, title="Загрузка"),
            st.Page(page_analytics, title="Аналитика"),
            st.Page(page_details, title="Детали креатива"),
        ]
    }
)
page.run()

st.sidebar.caption(f"Последнее действие: {datetime.now().strftime('%H:%M:%S')}")
