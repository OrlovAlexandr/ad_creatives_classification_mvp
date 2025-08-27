import logging

import pandas as pd
import streamlit as st
from components.color_block import color_block_horizontal
from components.visualizer import draw_bounding_boxes
from config import MINIO_ENDPOINT
from config import MINIO_PUBLIC_URL
from config import TOPIC_TRANSLATIONS
from services.fetchers import fetch_creative_details
from services.fetchers import fetch_creatives_by_group
from services.fetchers import fetch_groups
from utils.helpers import is_image_available


logger = logging.getLogger(__name__)


def page_details():
    st.header("Детали креатива")

    if "selected_creative_id_from_table" not in st.session_state:
        st.session_state.selected_creative_id_from_table = None

    groups = fetch_groups()
    if not groups:
        st.info("Нет доступных групп")
        return

    group_display_map = {g["group_id"]: g["display_name"] for g in groups}
    group_ids = list(group_display_map.keys())

    default_index = 0 if group_ids else None  # бэк уже сортирует

    selected_group = st.selectbox(
        "Выберите группу",
        options=group_ids,
        format_func=lambda gid: group_display_map[gid],
        index=default_index,
        key="selected_group_analytics",
    )

    if not selected_group:
        st.session_state.selected_creative_id_from_table = None
        return

    with st.spinner("Загрузка креативов..."):
        creatives = fetch_creatives_by_group(selected_group)

    if not creatives:
        st.info("В этой группе нет креативов.")
        st.session_state.selected_creative_id_from_table = None
        return

    # Табличка с креативами выбранной группы
    df_display = pd.DataFrame([
        {
            "ID": c["creative_id"],
            "Оригинальное имя": c["original_filename"],
            "Файл": f"{c['creative_id']}.{c['file_format']}",
            "Размер": f"{c['image_width']}x{c['image_height']}",
            "Время загрузки": c["upload_timestamp"].split(".")[0].replace("T", " "),
            "Статус": "Готово" if c.get("analysis") else "В обработке",
        }
        for c in creatives
    ])

    for _, row in df_display.iterrows():
        col1, col2, col3, col4, col5 = st.columns([3, 1, 2, 1, 2])
        with col1:
            st.write(f"**{row['Оригинальное имя']}**")
        with col2:
            st.write(row['Размер'])
        with col3:
            st.write(row['Время загрузки'])
        with col4:
            st.write(row['Статус'])
        with col5:
            if st.button("Детали", key=f"details_btn_{row['ID']}"):
                st.session_state.selected_creative_id_from_table = row['ID']
                st.rerun()

    st.divider()

    selected_creative_id = st.session_state.selected_creative_id_from_table

    if selected_creative_id:
        if st.button("Назад к списку"):
            st.session_state.selected_creative_id_from_table = None
            st.rerun()

        st.success(f"Выбран креатив: {selected_creative_id}")

        with st.spinner("Загрузка деталей креатива..."):
            data = fetch_creative_details(selected_creative_id)

        if not data:
            st.error("Не удалось загрузить данные креатива или данные некорректны.")
            if st.button("Повторить попытку"):
                st.rerun()
            return

        analysis_data = data.get("analysis")
        if not analysis_data:
            st.warning("Данные анализа креатива еще не готовы или произошла ошибка при обработке.")
            if st.button("Повторить попытку"):
                st.rerun()
            st.image(data.get("file_path"), caption="Оригинал", width=300)
            st.subheader(f"Детали креатива: {selected_creative_id}")
            st.write(f"**Файл:** {data.get('original_filename', 'N/A')}")
            st.write(f"**Размер:** {data.get('file_size', 'N/A')} байт")
            return

        st.divider()
        st.subheader(f"Детали креатива: {selected_creative_id}")

        minio_image_url = f"{data['file_path']}"
        minio_endpoint_url = minio_image_url.replace(MINIO_PUBLIC_URL, MINIO_ENDPOINT)
        if is_image_available(minio_endpoint_url):
            try:
                ocr_blocks = data.get("analysis", {}).get("ocr_blocks", [])
                detected_objects = data.get("analysis", {}).get("detected_objects", [])

                image_with_boxes = draw_bounding_boxes(
                    image_path_or_url=minio_endpoint_url,
                    ocr_blocks=ocr_blocks,
                    detected_objects=detected_objects,
                )

                st.image(image_with_boxes, width=600, caption="Анализ: OCR (зелёные) и объекты (жёлтые)")

            except Exception as e:
                logger.exception("Ошибка при отрисовке")
                st.error(f"Ошибка при отрисовке: {e}")
                st.image(minio_image_url, width=300, caption="Оригинал")
        else:
            logger.warning(f"Изображение недоступно: {minio_image_url}")
            st.warning("Изображение недоступно")
            st.code(minio_image_url)


        st.write(f"**Файл:** {data['original_filename']}")
        st.write(f"**Размер:** {data['file_size']} байт")
        st.write(f"**Формат:** {data['file_format']}")
        st.write(f"**Разрешение:** {data['image_width']}x{data['image_height']}")
        st.write(f"**Дата загрузки:** {data['upload_timestamp'].split('.')[0].replace('T', ' ')}")

        orig_topic = data.get('analysis', {}).get('main_topic', '—')
        translated_topic = TOPIC_TRANSLATIONS.get(
            orig_topic, orig_topic,
        ) if orig_topic != '—' else orig_topic

        st.write(f"**Основная тема:** {translated_topic}")

        topic_confidence = data.get('analysis', {}).get('topic_confidence', '—')
        # округлим до 3 знаков
        topic_confidence = round(topic_confidence, 3) if topic_confidence != '—' else '—'
        st.write(f"**Уверенность:** {topic_confidence}")

        ocr_text = data.get('analysis', {}).get('ocr_text', '—')
        st.subheader("Распознанный текст")
        st.text_area("OCR", ocr_text, height=150)

        ocr_blocks = data.get('analysis', {}).get('ocr_blocks', [])

        if ocr_blocks:
            for block in ocr_blocks:
                block['bbox'] = [round(x, 4) for x in block['bbox']]

            st.write("Блоки текста:")
            st.dataframe(pd.DataFrame(ocr_blocks, columns=['text', 'bbox', 'confidence']))
        else:
            st.info("Текст не распознан.")

        detected_objects = data.get('analysis', {}).get('detected_objects', [])
        if detected_objects:
            for obj in detected_objects:
                obj['bbox'] = [round(x, 4) for x in obj['bbox']]
            st.subheader("Обнаруженные объекты")
            st.dataframe(pd.DataFrame(detected_objects, columns=['class', 'bbox', 'confidence']))
        else:
            st.info("Объекты не обнаружены.")

        dominant_colors = data.get('analysis', {}).get('dominant_colors', [])
        secondary_colors = data.get('analysis', {}).get('secondary_colors', [])
        palette_colors = data.get('analysis', {}).get('palette_colors', {})

        if dominant_colors or secondary_colors or palette_colors:
            st.subheader("Цвета")

            if dominant_colors:
                color_block_horizontal(dominant_colors, "Доминирующие цвета", show_percent=True, show_rgb=True)

            if secondary_colors:
                color_block_horizontal(secondary_colors, "Второстепенные цвета", show_percent=True, show_rgb=True)

            if palette_colors:
                palette_list = [
                    {
                        "hex": info["hex"],
                        "percent": info["percent"],
                        "class_name": cls,
                    }
                    for cls, info in palette_colors.items()
                ]
                color_block_horizontal(palette_list, "По палитре", show_percent=True, show_rgb=True)
        else:
            st.info("Цвета не определены.")
