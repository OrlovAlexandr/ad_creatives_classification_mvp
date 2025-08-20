import streamlit as st
import pandas as pd

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

from components.visualizer import draw_bounding_boxes
from components.color_block import color_block_horizontal
from config import TOPIC_TRANSLATIONS, MINIO_BUCKET, MINIO_PUBLIC_URL
from services.fetchers import fetch_creatives_by_group, fetch_creative_details, fetch_groups
from utils.helpers import is_image_available

def page_details():
    st.header("Детали креатива")

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
        key="selected_group_analytics"
    )

    if not selected_group:
        return

    # Получаем креативы
    with st.spinner("Загрузка креативов..."):
        creatives = fetch_creatives_by_group(selected_group)

    if not creatives:
        st.info("В этой группе нет креативов.")
        return
    
    # Табличка с креативами выбранной группы
    df_creatives = pd.DataFrame([
        {
            "ID": c["creative_id"],
            "Оригинальное имя": c["original_filename"],
            "Файл": f"{c['creative_id']}.{c['file_format']}",
            "Размер": f"{c['image_width']}x{c['image_height']}",
            "Время загрузки": c["upload_timestamp"].split(".")[0].replace("T", " "),
            "Статус": "Готово" if c.get("analysis") else "В обработке"
        }
        for c in creatives
    ])
    df_creatives.reset_index(drop=True, inplace=True)

    gb = GridOptionsBuilder.from_dataframe(df_creatives)
    gb.configure_default_column(editable=False, wrapText=True, autoHeight=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(domLayout="autoHeight", suppressRowClickSelection=False)

    grid_options = gb.build()

    grid_response = AgGrid(
        df_creatives,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=min(300, 50 * len(df_creatives) + 50),
        theme="streamlit",
        key="aggrid_creatives"
    )

    selected_rows = grid_response.get("selected_rows", None)

    if selected_rows is not None and len(selected_rows) > 0:
        row = selected_rows.iloc[0]
        selected_creative_id = row.get("ID")

        if not selected_creative_id:
            st.error("Не удалось получить ID креатива.")
            return

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

        minio_image_url = f"{MINIO_PUBLIC_URL}/{data['file_path']}"
        if is_image_available(minio_image_url):
            try:
                ocr_blocks = data.get("analysis", {}).get("ocr_blocks", [])
                detected_objects = data.get("analysis", {}).get("detected_objects", [])

                image_with_boxes = draw_bounding_boxes(
                    image_path_or_url=minio_image_url,
                    ocr_blocks=ocr_blocks,
                    detected_objects=detected_objects
                )

                st.image(image_with_boxes, width=600, caption="Анализ: OCR (зелёные) и объекты (жёлтые)")

            except Exception as e:
                st.error(f"Ошибка при отрисовке: {e}")
                st.image(minio_image_url, width=300, caption="Оригинал")
        else:
            st.warning("Изображение недоступно")
            st.code(minio_image_url)

        st.write(f"**Файл:** {data['original_filename']}")
        st.write(f"**Размер:** {data['file_size']} байт")
        st.write(f"**Формат:** {data['file_format']}")
        st.write(f"**Размеры:** {data['image_width']}x{data['image_height']}")
        st.write(f"**Дата загрузки:** {data['upload_timestamp']}")

        orig_topic = data.get('analysis', {}).get('main_topic', '—')
        translated_topic = TOPIC_TRANSLATIONS.get(
            orig_topic, orig_topic
            ) if orig_topic != '—' else orig_topic

        st.write(f"**Основная тема:** {translated_topic}")

        ocr_text = data.get('analysis', {}).get('ocr_text', '—')
        st.subheader("Распознанный текст")
        st.text_area("OCR", ocr_text, height=150)

        ocr_blocks = data.get('analysis', {}).get('ocr_blocks', [])
        if ocr_blocks:
            st.write("Блоки текста:")
            st.dataframe(pd.DataFrame(ocr_blocks))
        else:
            st.info("Текст не распознан.")

        detected_objects = data.get('analysis', {}).get('detected_objects', [])
        if detected_objects:
            st.subheader("Обнаруженные объекты")
            st.dataframe(pd.DataFrame(detected_objects))
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
                        "class_name": cls
                    }
                    for cls, info in palette_colors.items()
                ]
                color_block_horizontal(palette_list, "По палитре", show_percent=True, show_rgb=True)
        else:
            st.info("Цвета не определены.")
