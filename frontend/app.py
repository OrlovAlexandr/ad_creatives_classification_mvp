import json
import os
from datetime import datetime
from typing import Dict, Optional
import uuid
import time

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from icecream import ic
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
# from st_aggrid.shared import JsCode

from visualizer import draw_bounding_boxes

load_dotenv()

# Настройки
USE_MOCK = False  # использовать mock-данные вместо реального бэкенда
BACKEND_URL = os.getenv("BACKEND_URL") if not USE_MOCK else "http://localhost:8000"

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
    if USE_MOCK:
        try:
            with open("mocks/groups.json", "r", encoding="utf-8") as f:
                raw = json.load(f)
            for g in raw:
                try:
                    # Извлекаем временную метку из grp_20250807_143000_abc123
                    ts_part = g["group_id"].split('_', 3)[:3]  # ['grp', '20250807', '143000']
                    dt_str = f"{ts_part[1]}_{ts_part[2]}"
                    dt = datetime.strptime(dt_str, "%Y%m%d_%H%M%S")
                    g["display_name"] = dt.strftime("Группа %d.%m.%Y %H:%M:%S")
                except:
                    g["display_name"] = g["group_id"]
            return raw
        except Exception as e:
            st.error(f"Ошибка загрузки mock-данных: {e}")
            return []
    else:
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


def upload_files(files, group_id: str, creative_ids: list[str]):
    """Отправляет файлы на бэкенд в указанную группу."""
    if USE_MOCK:
        st.success(f"Загрузка успешна (режим имитации). Группа: {group_id}, файлов: {len(files)}")
        return {"uploaded": len(files), "group_id": group_id, "errors": []}
    else:
        try:
            url = f"{BACKEND_URL}/upload"
            files_data = []

            original_filenames = [f.name for f in files]

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
                data[f"original_filenames"] = original_filenames
                
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
    if USE_MOCK:
        try:
            with open(f"mocks/creative_{creative_id}.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            st.error(f"Mock для креатива {creative_id} не найден")
            return None
        except Exception as e:
            st.error(f"Ошибка: {e}")
            return None
    else:
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
    if USE_MOCK:
        try:
            with open(f"mocks/analytics_group_{group_id}.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            st.error(f"Mock для аналитики группы {group_id} не найден")
            return None
    else:
        try:
            response = requests.get(f"{BACKEND_URL}/analytics/group/{group_id}")
            response.raise_for_status()
            return response.json()
        except:
            st.error("Ошибка загрузки аналитики")
            return None


def fetch_creatives_by_group(group_id: str) -> Optional[list]:
    """Получает список креативов по ID группы"""
    if USE_MOCK:
        try:
            with open(f"mocks/creatives_group_{group_id}.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Mock для креативов группы {group_id} не найден: {e}")
            return []
    else:
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

# Страница: Загрузка креативов
def page_upload():
    st.header("Загрузка креативов")

    if "current_group_id" not in st.session_state:
        st.session_state.current_group_id = generate_group_id()
    
    st.text(f"Текущая группа: {st.session_state.current_group_id}")

    uploaded_files = st.file_uploader(
        "Выберите изображения (JPG, PNG, WebP)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="Поддерживаемые форматы: JPG, PNG, WebP. Макс. 10 файлов."
    )

    # Кнопка загрузки
def page_upload():
    st.header("Загрузка креативов")

    if "current_group_id" not in st.session_state:
        st.session_state.current_group_id = generate_group_id()
    
    st.text(f"Текущая группа: {st.session_state.current_group_id}")

    uploaded_files = st.file_uploader(
        "Выберите изображения (JPG, PNG, WebP)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="Поддерживаемые форматы: JPG, PNG, WebP. Макс. 10 файлов."
    )

    # Кнопка загрузки
    if uploaded_files and st.button("Загрузить", key="upload_btn"):
        with st.spinner("Идёт загрузка и обработка..."):
            creative_ids = [generate_creative_id() for _ in uploaded_files]
            result = upload_files(uploaded_files, st.session_state.current_group_id, creative_ids)

            if result:
                st.success(
                    f"Успешно загружено {result['uploaded']} файлов в группу {st.session_state.current_group_id}"
                    )
                st.session_state.uploaded_creatives = creative_ids
                st.session_state.pop("current_group_id", None)

                fetch_groups.clear()

                # st.json(result)  # ответ бэкенда
                st.rerun()
            else:
                # st.session_state.uploaded_creatives = []
                st.error("Ошибка загрузки")
            # st.cache_data.clear()  # Обновляет кэш
    
    if "uploaded_creatives" in st.session_state and st.session_state.uploaded_creatives:
        st.subheader("Статус обработки")
        status_table = st.empty()  # Контейнер для таблицы
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
                            "Время загрузки": data["upload_timestamp"],
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
                st.info("Мониторинг остановлен.")
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

        try:
            # Получаем OCR и объекты
            ocr_blocks = data.get("analysis", {}).get("ocr_blocks", [])
            detected_objects = data.get("analysis", {}).get("detected_objects", [])

            # Рисуем рамки
            image_with_boxes = draw_bounding_boxes(
                image_path=data["file_path"],
                ocr_blocks=ocr_blocks,
                detected_objects=detected_objects
            )

            # Отображаем
            st.image(image_with_boxes, width=600, caption="Анализ: OCR (зелёные) и объекты (жёлтые)")

        except Exception as e:
            st.error(f"Ошибка при отрисовке: {e}")
            st.image(data["file_path"], width=300, caption="Оригинал")

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

        dominant_colors = data.get('analysis', {}).get('dominant_colors', [])
        if dominant_colors:
            st.subheader("Доминирующие цвета")
            cols = st.columns(len(dominant_colors))
            for i, c in enumerate(dominant_colors):
                with cols[i]:
                    st.color_picker(f"{c['hex']}", c["hex"], disabled=True)
                    st.caption(f"{c['percent']}%")
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
