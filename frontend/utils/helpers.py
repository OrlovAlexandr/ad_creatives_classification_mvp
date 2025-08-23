from datetime import datetime
import uuid
import requests


def generate_group_id():
    now = datetime.now()
    return f"grp_{now.strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"


def generate_creative_id():
    return str(uuid.uuid4())

def format_seconds(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def format_seconds_short(seconds: float) -> str:
    seconds = int(seconds)
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"

def calculate_columns(thumb_width: int, estimated_width: int, min_cols: int, max_cols: int) -> int:
    calculated_cols = estimated_width // thumb_width
    return max(min_cols, min(calculated_cols, max_cols))

def is_image_available(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except:
        return False