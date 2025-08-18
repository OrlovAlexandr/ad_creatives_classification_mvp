import json
import os
from datetime import datetime
from typing import Dict, Optional
import uuid
import time
import io

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from dotenv import load_dotenv
from icecream import ic
from PIL import Image
# from st_aggrid.shared import JsCode

from visualizer import draw_bounding_boxes

load_dotenv()

# Настройки
BACKEND_URL = os.getenv("BACKEND_URL")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_SECURE = os.getenv("MINIO_SECURE").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET")
if MINIO_SECURE:
    MINIO_BASE_URL = f"https://{MINIO_ENDPOINT}"
else:

    MINIO_BASE_URL = f"http://{MINIO_ENDPOINT}"
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL")
if not MINIO_PUBLIC_URL:
    MINIO_PUBLIC_URL = MINIO_BASE_URL 

# Настройки для отображения миниатюр
THUMBNAIL_WIDTH = 120
ESTIMATED_CONTENT_WIDTH = 1000
MAX_COLUMNS = 10
MIN_COLUMNS = 1

TOPIC_TRANSLATIONS = {
    'tableware': 'Столовые приборы',
    'ties': 'Галстуки',
    'bags': 'Сумки',
    'cups': 'Чашки',
    'clocks': 'Часы'
}

st.set_page_config(page_title="Классификатор креативов", layout="wide")


def generate_group_id():
    now = datetime.now()
    return f"grp_{now.strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"


def generate_creative_id():
    return str(uuid.uuid4())

# Вспомогательные функции
@st.cache_data(ttl=600)
def fetch_groups():
    """Получает список групп креативов с бэкенда (или из mock)"""
    try:
        # st.write(f"Запрос к: {BACKEND_URL}/groups")  # ← DEBUG
        response = requests.get(f"{BACKEND_URL}/groups")
        # st.write("Ответ /groups:", response.status_code, response.text)  # ← DEBUG
        response.raise_for_status()
        raw = response.json()
        
        for g in raw:
            try:
                ts_part = g["group_id"].split('_', 3)[:3]
                dt_str = f"{ts_part[1]}_{ts_part[2]}"
                dt = datetime.strptime(dt_str, "%Y%m%d_%H%M%S")
                g["display_name"] = dt.strftime("Группа %d.%m.%Y %H:%M:%S")
            except:
                g["display_name"] = g["group_id"]
        return raw
    except Exception:
        st.error("Бэкенд недоступен. Включён режим имитации.")
        return fetch_groups_mock()


def fetch_groups_mock():
    """Заглушка, если mock-данные не загрузились"""
    return [
        {"group_id": 101, "count": 3, "created_at": "2024-08-10T12:00:00"},
        {"group_id": 102, "count": 2, "created_at": "2024-08-11T14:30:00"}
    ]


def upload_files(files, group_id: str, creative_ids: list[str], original_filenames: list[str]):
    """Отправляет файлы на бэкенд в указанную группу."""
    try:
        url = f"{BACKEND_URL}/upload"
        files_data = []

        # original_filenames = [f.name for f in files]

        for file, cid in zip(files, creative_ids):
            ext = file.name.split(".")[-1].lower()
            filename = f"{cid}.{ext}"  # Называем файлы по ID креатива
            files_data.append(("files", (filename, file, file.type)))

        # import json as json_module
        data = {
            "group_id": group_id,
            # "creative_ids": creative_ids,
            # "original_filenames": original_filenames
        }
        for i, cid in enumerate(creative_ids):
            data[f"creative_ids"] = creative_ids  # FastAPI автоматически соберёт список
        for i, name in enumerate(original_filenames):
            # data[f"original_filenames"] = original_filenames
            data.setdefault("original_filenames", []).append(name)
            
        response = requests.post(
            url, 
            files=files_data, 
            data=data,
            )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Ошибка загрузки: {e}")
        return None


@st.cache_data(ttl=30)
def fetch_creative_details(creative_id: str) -> Optional[Dict]:  # был int
    """Получает детали креатива с бэкенда (или из mock)"""
    try:
        response = requests.get(f"{BACKEND_URL}/creatives/{creative_id}")
        response.raise_for_status()
        # data = response.json()  # для отладки
        # st.json(data)  # для отладки, выводит полученные данные на страницу
        return response.json()
    except Exception as e:
        st.error(f"Ошибка загрузки креатива {creative_id}: {e}")
        return None


def fetch_analytics(group_id):
    """Получает аналитику по группе креативов с бэкенда (или из mock)"""
    try:
        response = requests.get(f"{BACKEND_URL}/analytics/group/{group_id}")
        response.raise_for_status()
        return response.json()
    except:
        st.error("Ошибка загрузки аналитики")
        return None


def fetch_creatives_by_group(group_id: str) -> Optional[list]:
    """Получает список креативов по ID группы"""
    try:
        response = requests.get(f"{BACKEND_URL}/groups/{group_id}/creatives")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Ошибка загрузки креативов группы {group_id}: {e}")
        return []    


def style_status(val):
    if "SUCCESS" in str(val):
        return "background-color: #d4edda; color: #155724"
    elif "PROCESSING" in str(val):
        return "background-color: #fff3cd; color: #856404"
    elif val == "PENDING":
        return "background-color: #f8f9fa; color: #6c757d"
    return ""

def style_topic(val):
    return "font-weight: bold; font-size: 15px"


def calculate_columns(thumb_width: int, estimated_width: int, min_cols: int, max_cols: int) -> int:
    calculated_cols = estimated_width // thumb_width
    return max(min_cols, min(calculated_cols, max_cols))

def display_uploaded_thumbnails(files_list):
    if not files_list:
        st.info("Файлы не выбраны.")
        return

    num_columns = calculate_columns(THUMBNAIL_WIDTH, ESTIMATED_CONTENT_WIDTH, MIN_COLUMNS, MAX_COLUMNS)

    total_files = len(files_list)
    files_to_remove_indices = []

    for i in range(0, total_files, num_columns):
        cols = st.columns(num_columns) 
        for j in range(num_columns):
            idx = i + j
            if idx < total_files: 
                uploaded_file_obj = files_list[idx]
                file_unique_id = uploaded_file_obj.get("unique_id")
                
                with cols[j]: 
                    try:
                        # st.text(uploaded_file_obj["name"][:20]) 
                        st.markdown(f"<small>{uploaded_file_obj['name'][:20]}</small>", unsafe_allow_html=True)
                        
                        if (uploaded_file_obj["type"] and 
                            uploaded_file_obj["type"].startswith('image/')):
                            image_bytes = uploaded_file_obj["file_obj"].getvalue() 
                            image = Image.open(io.BytesIO(image_bytes))
                            image.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_WIDTH * 2)) # Ограничиваем высоту
                            st.image(image, width=THUMBNAIL_WIDTH) 
                        else:
                            st.info(f"Файл: {uploaded_file_obj['type'] or 'Неизвестный тип'}")
                        
                        if st.button("Удалить", key=f"del_btn_{file_unique_id}"):
                            files_to_remove_indices.append(idx)
                            
                    except Exception as e:
                        st.error(f"Ошибка отображения {uploaded_file_obj['name']}: {e}")
            else:
                with cols[j]:
                    st.empty() 

    if files_to_remove_indices:
        files_to_remove_indices.sort(reverse=True)
        for idx in files_to_remove_indices:
            if 0 <= idx < len(st.session_state.selected_files):
                st.session_state.selected_files.pop(idx)
        
        st.rerun() 

# Страница: Загрузка креативов
def page_upload():
    st.header("Загрузка креативов")

    if "current_group_id" not in st.session_state:
        st.session_state.current_group_id = generate_group_id()
    
    st.text(f"Текущая группа: {st.session_state.current_group_id}")

    if "selected_files" not in st.session_state:
        st.session_state.selected_files = []
    
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = str(uuid.uuid4())

    # File uploader
    new_uploads = st.file_uploader(
        "Выберите изображения (JPG, PNG, WebP)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key=st.session_state.uploader_key, # Используем динамический ключ
        help="Поддерживаемые форматы: JPG, PNG, WebP. Можете выбрать несколько файлов."
    )

    if new_uploads:
        added_any = False
        existing_names = {f["name"] for f in st.session_state.selected_files}
        for file in new_uploads:
            if file.name not in existing_names:
                unique_id = str(uuid.uuid4())
                st.session_state.selected_files.append({
                    "unique_id": unique_id,
                    "name": file.name,
                    "type": file.type,
                    "size": file.size,
                    "file_obj": file
                })
                existing_names.add(file.name)
                added_any = True
        
        if added_any:
            st.session_state.uploader_key = str(uuid.uuid4())
            st.rerun()

    st.subheader("Выбранные файлы")
    display_uploaded_thumbnails(st.session_state.selected_files)

    # Кнопка загрузки
    if st.session_state.selected_files and st.button("Загрузить", key="upload_btn"):
        with st.spinner("Идёт загрузка и обработка..."):
            files_for_upload = []
            creative_ids = []
            original_filenames = []

            for file_info in st.session_state.selected_files:
                file_obj = file_info["file_obj"]
                file_obj.seek(0) 
                files_for_upload.append(file_obj)
                creative_ids.append(generate_creative_id())
                original_filenames.append(file_info["name"])

            result = upload_files(files_for_upload, st.session_state.current_group_id, creative_ids, original_filenames)
            if result:
                st.success(
                    f"Успешно загружено {result['uploaded']} файлов в группу {st.session_state.current_group_id}"
                )
                st.session_state.uploaded_creatives = creative_ids
                # Очищаем список выбранных файлов после успешной загрузки
                st.session_state.selected_files = [] 
                # Также сбрасываем ключ виджета на всякий случай
                st.session_state.uploader_key = str(uuid.uuid4())
                st.session_state.pop("current_group_id", None)  # Очищаем прежний Group ID
                fetch_groups.clear()
                st.rerun()
            else:
                st.error("Ошибка загрузки")

    if "uploaded_creatives" in st.session_state and st.session_state.uploaded_creatives:
        st.subheader("Статус обработки")
        status_table = st.empty()
        while True:
            statuses = []
            finished_count = 0 
            total_count = len(st.session_state.uploaded_creatives)
            
            for cid in st.session_state.uploaded_creatives:
                try:
                    resp = requests.get(f"{BACKEND_URL}/status/{cid}")
                    if resp.status_code == 200:
                        data = resp.json()

                        original_topic = data["main_topic"]
                        translated_topic = TOPIC_TRANSLATIONS.get(
                            original_topic, original_topic
                            ) if original_topic else "PENDING"
                        
                        statuses.append({
                            "ID": cid[:8] + "...",
                            "Оригинальное имя": data["original_filename"],
                            "Размер": data["file_size"],
                            "Разрешение": data["image_size"],
                            "Время загрузки": data["upload_timestamp"].split(".")[0].replace("T", " "),
                            "OCR-распознавание": data["ocr_status"],
                            "Детекция объектов": data["detection_status"],
                            "Классификация": data["classification_status"],
                            "Топик": translated_topic or "PENDING",
                            "Confidence": f"{data['topic_confidence']:.2f}" if data["topic_confidence"] else "PENDING",
                            "Статус": data["overall_status"]
                        })
                        if str(data["overall_status"]).startswith(("SUCCESS", "ERROR")):
                            finished_count += 1
                    else:
                        statuses.append({"ID": cid[:8] + "...", "Ошибка": f"Статус {resp.status_code}"})
                except requests.exceptions.RequestException as e:
                    statuses.append({"ID": cid[:8] + "...", "Ошибка": f"Сеть: {type(e).__name__}"})
                except Exception as e:
                    statuses.append({"ID": cid[:8] + "...", "Ошибка": f"Ошибка: {type(e).__name__}"})

            df = pd.DataFrame(statuses)
            styled_df = df.style.map(style_status, subset=[
                "OCR-распознавание",
                "Детекция объектов",
                "Классификация",
                "Статус"
            ]).map(style_topic, subset=["Топик"])
            status_table.dataframe(styled_df, use_container_width=True)
            # st.write(f"DEBUG: finished_count = {finished_count}, total_count = {total_count}") #  Временный вывод
            
            if finished_count == total_count and total_count > 0:
                st.success("Все креативы обработаны!")
                st.session_state.uploaded_creatives = [] 
                # st.info("Мониторинг остановлен.")
                return 
            else:
                time.sleep(1)


# Страница: Просмотр аналитики по группе
def page_analytics():
    """
    Страница: Просмотр аналитики по группе
    TODO: продумать архитектуру страницы, что мы хотим видеть на странице
    """
    st.header("Аналитика по группе")
    groups = fetch_groups()  # Список групп
    if not groups:
        st.info("Нет доступных групп")
        return


    group_display_map = {g["group_id"]: g["display_name"] for g in groups}
    group_ids = list(group_display_map.keys())

    default_index = 0 if group_ids else None  # бэк уже сортирует

    selected = st.selectbox(
        "Выберите группу",
        options=group_ids,
        format_func=lambda gid: group_display_map[gid],
        index=default_index,
        key="selected_group_analytics"
    )

    if selected:
        data = fetch_analytics(selected)  # Аналитика по группе
        ic(data)
        if data:
            st.subheader("Сводка")
            col1, col2, col3 = st.columns(3)
            col1.metric("Креативов", data["summary"]["total_creatives"])
            col2.metric("Средняя уверенность (OCR)", f"{data['summary']['avg_ocr_confidence']:.2f}")
            col3.metric("Средняя уверенность (объекты)", f"{data['summary']['avg_object_confidence']:.2f}")

            st.subheader("Тематики")
            # df_topics = pd.DataFrame(data["topics"])
            # st.bar_chart(df_topics.set_index("topic"))
            topics = data.get("topics", [])
            if not topics:
                st.info("Нет данных о тематиках.")
            else:
                translated_topics = []
                for topic_data in topics:
                    original_topic = topic_data.get("topic", "")
                    translated_topic = TOPIC_TRANSLATIONS.get(original_topic, original_topic)
                    translated_item = topic_data.copy()
                    translated_item["topic"] = translated_topic
                    translated_topics.append(translated_item)

                df_topics = pd.DataFrame(translated_topics)
                if "topic" in df_topics.columns:
                    st.bar_chart(df_topics.set_index("topic")["count"])
                else:
                    st.error("Ошибка: в данных нет колонки 'topic'.")
                    st.write("Доступные колонки:", df_topics.columns.tolist())
                    st.write("Пример данных:", translated_topics)

            st.subheader("Цвета")
            colors = [c["hex"] for c in data["dominant_colors"]]
            st.write("Доминирующие цвета:", ", ".join(colors))


def color_block(hex_color, label, percent):
    """Отображает цвет как блок с подписью"""
    st.markdown(
        f"""
        <div style="
            display: inline-block;
            width: 40px;
            height: 40px;
            background-color: {hex_color};
            border: 2px solid #ddd;
            border-radius: 8px;
            margin: 5px;
            text-align: center;
            font-size: 12px;
            color: {'white' if is_dark(hex_color) else 'black'};
            line-height: 40px;
            font-weight: bold;
        " title="{label}: {percent}%">
            {percent:.0f}%
        </div>
        """,
        unsafe_allow_html=True
    )

def color_block_horizontal(colors, title="Цвета", show_percent=True, show_rgb=False):
    """
    Отображает цвета в колонках.
    :param colors: Список словарей с 'hex', 'percent', 'rgb'
    :param title: Заголовок блока
    :param show_percent: Показывать процент
    :param show_rgb: Показывать RGB
    """
    if not colors:
        return
    st.markdown(" ")
    st.markdown(f"**{title}**")

    # 🔥 Сортируем по проценту (от большего к меньшему)
    sorted_colors = sorted(colors, key=lambda x: x.get("percent", 0), reverse=True)

    n_cols = max(1, min(len(sorted_colors), 10))
    cols = st.columns(n_cols, gap="medium")

    for c, col in zip(sorted_colors, cols):
        with col:
            # Цветной блок
            st.markdown(
                f"""
                <div style="
                    width: 50px;
                    height: 50px;
                    background-color: {c['hex']};
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                "></div>
                """,
                unsafe_allow_html=True
            )
            # Подпись: HEX + класс + процент + RGB
            label_parts = [f"<b>{c['hex'].upper()}</b>"]
            # Если есть 'class_name' (например, из palette_colors), показываем
            if 'class_name' in c:
                label_parts.append(f"<medium>{c['class_name']}</medium>")
            if show_percent:
                label_parts.append(f"<medium>{c['percent']:.1f}%</medium>")
            if show_rgb and 'rgb' in c:
                label_parts.append(f"<small>RGB({c['rgb'][0]}, {c['rgb'][1]}, {c['rgb'][2]})</small>")

            label_html = "<br>".join(label_parts)
            st.markdown(
                f"<div style='text-align: left; font-size: 13px; line-height: 1.3;'>{label_html}</div>",
                unsafe_allow_html=True
            )

def is_dark(hex_color):
    """Определяет, тёмный ли цвет (для выбора цвета текста)"""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return brightness < 128


# Страница: Детали креатива
def page_details():
    st.header("Детали креатива")

    # Получаем группы
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

        ### Если не надо, удалить
        if data["file_path"].startswith(f"{MINIO_BUCKET}/"):             
             minio_object_key = data["file_path"][len(f"{MINIO_BUCKET}/"):] # Убираем "creatives/"
        else:
             minio_object_key = data["file_path"] # Пусть будет как есть, если формат такой
        minio_image_url = f"{MINIO_PUBLIC_URL}/{data['file_path']}"

        try:
            # Получаем OCR и объекты
            ocr_blocks = data.get("analysis", {}).get("ocr_blocks", [])
            detected_objects = data.get("analysis", {}).get("detected_objects", [])

            # Рисуем рамки
            image_with_boxes = draw_bounding_boxes(
                image_path_or_url=minio_image_url,
                ocr_blocks=ocr_blocks,
                detected_objects=detected_objects
            )

            # Отображаем
            st.image(image_with_boxes, width=600, caption="Анализ: OCR (зелёные) и объекты (жёлтые)")

        except Exception as e:
            st.error(f"Ошибка при отрисовке: {e}")
            # st.image(data["file_path"], width=300, caption="Оригинал")
            st.image(minio_image_url, width=300, caption="Оригинал (из MinIO)")

        # Метаданные
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

        # dominant_colors = data.get('analysis', {}).get('dominant_colors', [])
        # if dominant_colors:
        #     st.subheader("Доминирующие цвета")
        #     cols = st.columns(len(dominant_colors))
        #     for i, c in enumerate(dominant_colors):
        #         with cols[i]:
        #             st.color_picker(f"{c['hex']}", c["hex"], disabled=True)
        #             st.caption(f"{c['percent']}%")
        # else:
        #     st.info("Цвета не определены.")

        dominant_colors = data.get('analysis', {}).get('dominant_colors', [])
        secondary_colors = data.get('analysis', {}).get('secondary_colors', [])
        palette_colors = data.get('analysis', {}).get('palette_colors', {})

        if dominant_colors or secondary_colors or palette_colors:
            st.subheader("Цвета")

            # Доминирующие цвета
            if dominant_colors:
                color_block_horizontal(dominant_colors, "Доминирующие цвета", show_percent=True, show_rgb=True)

            # Второстепенные цвета
            if secondary_colors:
                color_block_horizontal(secondary_colors, "Второстепенные цвета", show_percent=True, show_rgb=True)

            # Цвета по палитре
            if palette_colors:
                # Преобразуем словарь в список и добавляем class_name
                palette_list = [
                    {
                        "hex": info["hex"],
                        "percent": info["percent"],
                        "class_name": cls  # Добавляем название класса
                    }
                    for cls, info in palette_colors.items()
                ]
                color_block_horizontal(palette_list, "По палитре", show_percent=True, show_rgb=True)
        else:
            st.info("Цвета не определены.")


# Боковое меню
st.sidebar.title("Меню")
page = st.sidebar.radio(
    "Выберите раздел", ["Загрузка", "Аналитика", "Детали креатива"], 
    key="main_page_selector")

# Очистка состояния при смене страницы
if "last_page" in st.session_state and st.session_state.last_page != page:
    st.session_state.pop("uploaded_creatives", None)
st.session_state.last_page = page

if page == "Загрузка":
    page_upload()
elif page == "Аналитика":
    page_analytics()
elif page == "Детали креатива":
    page_details()

# Логирование действий
st.sidebar.divider()
st.sidebar.caption(f"Последнее действие: {datetime.now().strftime('%H:%M:%S')}")
