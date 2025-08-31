import pandas as pd
import streamlit as st
from components.analytics_charts import create_color_pie_chart
from components.analytics_charts import create_topic_color_stacked_bar
from config import TOPIC_TRANSLATIONS
from services.fetchers import fetch_analytics
from services.fetchers import fetch_analytics_all
from services.fetchers import fetch_groups
from utils.helpers import format_seconds
from utils.helpers import format_seconds_short


def _display_summary_section(data_group, data_all):
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown(
            '<div style="font-size: 17px; font-weight: bold;">По группе</div>',
            unsafe_allow_html=True,
        )
        a1, a2 = st.columns(2)
        a1.metric("Креативов", data_group["summary"]["total_creatives"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Ср. уверенность \n(OCR)", f"{data_group['summary']['avg_ocr_confidence']:.2f}")
        c2.metric("Ср. уверенность \n(объекты)", f"{data_group['summary']['avg_object_confidence']:.2f}")
        c3.metric("Ср. уверенность \n(топики)", f"{data_group['summary']['avg_topic_confidence']:.2f}")

    with col_right:
        st.markdown(
            '<div style="font-size: 17px; font-weight: bold;">По всем креативам</div>',
            unsafe_allow_html=True,
        )
        if data_all:
            a1, a2 = st.columns(2)
            a1.metric("Групп", len(fetch_groups()))
            a2.metric("Креативов", data_all["summary"]["total_creatives"])
            c1, c2, c3 = st.columns(3)
            c1.metric("Ср. уверенность (OCR)", f"{data_all['summary']['avg_ocr_confidence']:.2f}")
            c2.metric("Ср. уверенность (объекты)", f"{data_all['summary']['avg_object_confidence']:.2f}")
            c3.metric("Ср. уверенность (топики)", f"{data_all['summary']['avg_topic_confidence']:.2f}")


def _display_topic_distribution(data_group, data_all):
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Распределение топиков")
        topics_group = data_group.get("topics", [])
        if topics_group:
            df_topics = pd.DataFrame([
                {"topic": TOPIC_TRANSLATIONS.get(t["topic"], t["topic"]), "count": t["count"]}
                for t in topics_group
            ])
            st.bar_chart(df_topics.set_index("topic")["count"], height=300, horizontal=True)
        else:
            st.info("Нет данных о тематиках.")

    with col_right:
        st.subheader(" ")
        if data_all:
            topics_all = data_all.get("topics", [])
            if topics_all:
                df_topics_all = pd.DataFrame([
                    {"topic": TOPIC_TRANSLATIONS.get(t["topic"], t["topic"]), "count": t["count"]}
                    for t in topics_all
                ])
                st.bar_chart(df_topics_all.set_index("topic")["count"], height=300, horizontal=True)
            else:
                st.info("Нет данных о тематиках.")
        else:
            st.info("Нет данных по всем креативам.")


def _display_color_distribution(data_group, data_all):
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Распределение цветов")
        if data_group.get("color_class_distribution"):
            fig_group = create_color_pie_chart(
                data_group["color_class_distribution"],
                title="Цвета в группе",
            )
            st.plotly_chart(fig_group, use_container_width=True)
        else:
            st.info("Нет данных о цветах для построения диаграммы.")

    with col_right:
        st.subheader(" ")
        if data_all and "color_class_distribution" in data_all and data_all["color_class_distribution"]:
            fig_all = create_color_pie_chart(
                data_all["color_class_distribution"],
                title="Цвета во всех креативах",
            )
            st.plotly_chart(fig_all, use_container_width=True)
        else:
            st.info("Нет данных о цветах для построения диаграммы.")


def _display_topic_color_distribution(data_group, data_all):
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Топ-5 цветов по топикам")
        if data_group.get("topic_color_distribution"):
            fig_group = create_topic_color_stacked_bar(
                data_group["topic_color_distribution"],
                title="По группе",
            )
            st.plotly_chart(fig_group, use_container_width=True)
        else:
            st.info("Нет данных о цветах по топикам.")

    with col_right:
        st.subheader(" ")
        if data_all and "topic_color_distribution" in data_all and data_all["topic_color_distribution"]:
            fig_all = create_topic_color_stacked_bar(
                data_all["topic_color_distribution"],
                title="По всем креативам",
            )
            st.plotly_chart(fig_all, use_container_width=True)
        else:
            st.info("Нет данных о цветах по топикам.")


def _display_analytics_tables(data_group, data_all):
    st.subheader("Аналитика по группе")
    if data_group.get("topics_table"):
        df_group = pd.DataFrame(data_group["topics_table"])
        st.dataframe(df_group, use_container_width=True)

        st.markdown(
            f"**Общее время на обработку креативов в группе:** `{format_seconds(data_group['total_processing_time'])}`",
        )
        if data_group["total_creatives_in_group"] > 0:
            avg_per_creative = data_group['total_processing_time'] / data_group['total_creatives_in_group']
            st.markdown(f"**Среднее время на обработку одного креатива:** `{format_seconds_short(avg_per_creative)}`")
    else:
        st.info("Нет данных для таблицы по группе.")

    st.subheader("Аналитика общая")
    if data_all and "topics_table" in data_all and data_all["topics_table"]:
        df_all = pd.DataFrame(data_all["topics_table"])
        st.dataframe(df_all, use_container_width=True)

        st.markdown(
            f"**Общее время на обработку всех креативов:** `{format_seconds(data_all['total_processing_time'])}`",
        )
        if data_all.get("total_creatives_in_group", 0) > 0:
            avg_per_creative = data_all['total_processing_time'] / data_all['total_creatives_in_group']
            st.markdown(f"**Среднее время на обработку одного креатива:** `{format_seconds_short(avg_per_creative)}`")
    else:
        st.info("Нет данных для общей таблицы.")


def page_analytics():
    st.header("Аналитика")

    groups = fetch_groups()
    if not groups:
        st.info("Нет доступных групп")
        return

    group_display_map = {g["group_id"]: g["display_name"] for g in groups}
    group_ids = list(group_display_map.keys())
    default_index = 0 if group_ids else None

    selected = st.selectbox(
        "Выберите группу",
        options=group_ids,
        format_func=lambda gid: group_display_map[gid],
        index=default_index,
        key="selected_group_analytics",
    )

    if not selected:
        return

    data_group = fetch_analytics(selected)
    data_all = fetch_analytics_all()

    if not data_group:
        st.error("Не удалось загрузить аналитику по группе.")
        return

    if not data_all:
        st.warning("Не удалось загрузить общую аналитику.")
        data_all = None

    _display_summary_section(data_group, data_all)
    _display_topic_distribution(data_group, data_all)
    _display_color_distribution(data_group, data_all)
    _display_topic_color_distribution(data_group, data_all)
    _display_analytics_tables(data_group, data_all)
