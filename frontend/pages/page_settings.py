import streamlit as st
import requests
from config import BACKEND_URL
import logging

logger = logging.getLogger(__name__)

def page_settings():
    st.header("Настройки приложения")

    try:
        response = requests.get(f"{BACKEND_URL}/settings/")
        if response.status_code == 200:
            settings_data = response.json()
        else:
            st.error(f"Ошибка получения настроек: {response.status_code}")
            settings_data = {}
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка сети при получении настроек: {e}")
        settings_data = {}

    st.subheader("Настройки цветового анализа")

    current_dominant = settings_data.get("DOMINANT_COLORS_COUNT", 3)
    new_dominant = st.number_input(
        "Количество доминирующих цветов",
        min_value=1,
        max_value=10,
        value=int(current_dominant),
        key="dominant_colors_count"
    )

    current_secondary = settings_data.get("SECONDARY_COLORS_COUNT", 3)
    new_secondary = st.number_input(
        "Количество второстепенных цветов",
        min_value=1,
        max_value=10,
        value=int(current_secondary),
        key="secondary_colors_count"
    )

    # Кнопка сохранения
    if st.button("Сохранить настройки"):
        updates = {}
        if new_dominant != current_dominant:
            updates["DOMINANT_COLORS_COUNT"] = new_dominant
        if new_secondary != current_secondary:
            updates["SECONDARY_COLORS_COUNT"] = new_secondary

        if updates:
            try:
                response = requests.put(f"{BACKEND_URL}/settings/", json=updates)
                if response.status_code == 200:
                    st.success("Настройки успешно сохранены!")
                    st.rerun()
                else:
                    st.error(f"Ошибка сохранения настроек: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Ошибка сети при сохранении настроек: {e}")
        else:
            st.info("Нет изменений для сохранения.")
