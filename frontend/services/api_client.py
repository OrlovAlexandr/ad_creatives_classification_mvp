import requests

def get_backend_url():
    from config import BACKEND_URL
    return BACKEND_URL

def make_request(method, endpoint, **kwargs):
    url = f"{get_backend_url()}{endpoint}"
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка запроса к {url}: {e}")
        return None
