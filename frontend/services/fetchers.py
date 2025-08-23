from .api_client import make_request, get_backend_url
from datetime import datetime
import streamlit as st
import requests

@st.cache_data(ttl=600)
def fetch_groups():
    """Получает список групп креативов с бэкенда"""
    data = make_request("GET", "/groups")
    if not data:
        return []
    for g in data:
        try:
            ts_part = g["group_id"].split('_', 3)[:3]
            dt_str = f"{ts_part[1]}_{ts_part[2]}"
            dt = datetime.strptime(dt_str, "%Y%m%d_%H%M%S")
            g["display_name"] = dt.strftime("Группа %d.%m.%Y %H:%M:%S")
        except:
            g["display_name"] = g["group_id"]
    return data

def fetch_analytics(group_id):
    return make_request("GET", f"/analytics/group/{group_id}")

def fetch_analytics_all():
    return make_request("GET", "/analytics/all")

def fetch_creatives_by_group(group_id):
    return make_request("GET", f"/groups/{group_id}/creatives")

def fetch_creative_details(creative_id):
    return make_request("GET", f"/creatives/{creative_id}")

def upload_files(files, group_id, creative_ids, original_filenames):
    url = f"{get_backend_url()}/upload"
    files_data = []
    for file, cid in zip(files, creative_ids):
        ext = file.name.split(".")[-1].lower()
        filename = f"{cid}.{ext}"
        files_data.append(("files", (filename, file, file.type)))

    data = {
        "group_id": group_id,
        "creative_ids": creative_ids,
        "original_filenames": original_filenames
    }

    # Попробовать потом убрать блок кода, выше раскомментить
    # for i, cid in enumerate(creative_ids):
    #     data[f"creative_ids"] = creative_ids  # FastAPI автоматически соберёт список
    # for i, name in enumerate(original_filenames):
    #     data.setdefault("original_filenames", []).append(name)
    
    try:
        response = requests.post(url, files=files_data, data=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Ошибка загрузки: {e}")
        return None
