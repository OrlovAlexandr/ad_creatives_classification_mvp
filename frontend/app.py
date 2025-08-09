import json
import os
from datetime import datetime
from typing import Dict, Optional
import uuid

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from icecream import ic

from visualizer import draw_bounding_boxes

load_dotenv()

# Настройки
USE_MOCK = False  # использовать mock-данные вместо реального бэкенда
BACKEND_URL = os.getenv("BACKEND_URL") if not USE_MOCK else "http://localhost:8000"

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
                    g["display_name"] = dt.strftime("Группа %d.%m.%Y %H:%M")
                except:
                    g["display_name"] = g["group_id"]
            return raw
        except Exception as e:
            st.error(f"Ошибка загрузки mock-данных: {e}")
            return []
    else:
        try:
            response = requests.get(f"{BACKEND_URL}/groups")
            response.raise_for_status()
            raw = response.json()
            for g in raw:
                try:
                    ts_part = g["group_id"].split('_', 3)[:3]
                    dt_str = f"{ts_part[1]}_{ts_part[2]}"
                    dt = datetime.strptime(dt_str, "%Y%m%d_%H%M%S")
                    g["display_name"] = dt.strftime("Группа %d.%m.%Y %H:%M")
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
    """
    Отправляет файлы на бэкенд в указанную группу.
    TODO: генерация случайного id группы.
    """
    if USE_MOCK:
        st.success(f"✅ Загрузка успешна (режим имитации). Группа: {group_id}, файлов: {len(files)}")
        return {"uploaded": len(files), "group_id": group_id, "errors": []}
    else:
        try:
            url = f"{BACKEND_URL}/upload"
            files_data = []
            for file, cid in zip(files, creative_ids):
                ext = file.name.split(".")[-1].lower()
                # Используем UUID как имя файла
                filename = f"{cid}.{ext}"
                files_data.append(("files", (filename, file, file.type)))


            # files_data = [("files", (f.name, f, f.type)) for f in files]
            data = {
                "group_id": group_id,
                "creative_ids": creative_ids  # Передаём ID креативов
            }
            response = requests.post(url, files=files_data, data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Ошибка загрузки: {e}")
            return None


@st.cache_data(ttl=300)
def fetch_creative_details(creative_id: int) -> Optional[Dict]:
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


# Страница: Загрузка креативов
def page_upload():
    st.header("Загрузка креативов")

    if "current_group_id" not in st.session_state:
        st.session_state.current_group_id = generate_group_id()
    
    st.text(f"Текущая группа: {st.session_state.current_group_id}")

    # group_id = st.text_input("ID группы", value="101")  # TODO: генерация случайного id
    uploaded_files = st.file_uploader(
        "Выберите изображения (JPG, PNG, WebP)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="Поддерживаемые форматы: JPG, PNG, WebP. Макс. 10 файлов."
    )

    # Кнопка загрузки
    if uploaded_files and st.button("Загрузить"):
        with st.spinner("Идёт загрузка и обработка..."):
            creative_ids = [generate_creative_id() for _ in uploaded_files]

            result = upload_files(uploaded_files, st.session_state.current_group_id, creative_ids)

            if result:
                st.success(
                    f"Успешно загружено {result['uploaded']} файлов в группу {st.session_state.current_group_id}"
                    )
                st.json(result)  # Показывает ответ бэкенда
            st.cache_data.clear()  # Обновляет кэш групп
            st.session_state.pop("current_group_id", None)  # Удаляет группу из сессии


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
    # group_options = [(g["display_name"], g["group_id"]) for g in groups]
    # display_names = [item[0] for item in group_options]
    # group_ids = [item[1] for item in group_options]

    selected = st.selectbox(
        "Выберите группу",
        options=group_ids,
        format_func=lambda gid: group_display_map[gid],
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
                df_topics = pd.DataFrame(topics)
                if "topic" in df_topics.columns:
                    st.bar_chart(df_topics.set_index("topic")["count"])
                else:
                    st.error("Ошибка: в данных нет колонки 'topic'.")
                    st.write("Доступные колонки:", df_topics.columns.tolist())
                    st.write("Пример данных:", topics)

            st.subheader("Цвета")
            colors = [c["hex"] for c in data["dominant_colors"]]
            st.write("Доминирующие цвета:", ", ".join(colors))


# Страница: Детали креатива
def page_details():
    st.header("🔍 Детали креатива")
    creative_id = st.number_input("ID креатива", min_value=1, step=1)
    if st.button("Загрузить"):
        data = fetch_creative_details(creative_id)  # Детали креатива
        if data:
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

            main_topic = data.get('analysis', {}).get('main_topic', '—')
            st.write(f"**Основная тема:** {main_topic}")

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
st.sidebar.title("📋 Меню")
page = st.sidebar.radio("Выберите раздел", ["Загрузка", "Аналитика", "Детали креатива"])

if page == "Загрузка":
    page_upload()
elif page == "Аналитика":
    page_analytics()
elif page == "Детали креатива":
    page_details()

# Логирование действий
st.sidebar.divider()
st.sidebar.caption(f"Последнее действие: {datetime.now().strftime('%H:%M:%S')}")
