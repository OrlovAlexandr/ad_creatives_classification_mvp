import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from collections import Counter
import logging
import colorsys
from icecream import ic
from config import PALETTE_HEX, COLOR_CLASSES, MONOCHROME_HEX_SET

logger = logging.getLogger(__name__)

def rgb_to_hsv_array(rgb_array):
    rgb_norm = rgb_array / 255.0
    hsv_array = np.apply_along_axis(lambda rgb: colorsys.rgb_to_hsv(rgb[0], rgb[1], rgb[2]), 1, rgb_norm)
    return hsv_array

def rgb_to_hex(rgb_tuple):
    return "#{:02x}{:02x}{:02x}".format(int(rgb_tuple[0]), int(rgb_tuple[1]), int(rgb_tuple[2]))

# RGB (0-255) в HSV (H: 0-360, S: 0-100, V: 0-100)
def rgb_to_hsv_single(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
    return h * 360, s * 100, v * 100

PALETTE_RGB = np.array([tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) for hex_color in PALETTE_HEX])
PALETTE_HSV = rgb_to_hsv_array(PALETTE_RGB)
MONOCHROME_INDICES = [i for i, hex_color in enumerate(PALETTE_HEX) if hex_color in MONOCHROME_HEX_SET]
NON_MONOCHROME_INDICES = [i for i, hex_color in enumerate(PALETTE_HEX) if hex_color not in MONOCHROME_HEX_SET]

HEX_TO_CLASS = {}
for class_name, hex_colors in COLOR_CLASSES.items():
    for hex_color in hex_colors:
        HEX_TO_CLASS[hex_color] = class_name

def get_top_colors(
        image_path: str, 
        n_dominant: int=3, 
        n_secondary: int=3, 
        resize_size: tuple=(300, 300), 
        n_coeff: float=1.0
        ) -> dict:
    try:
        logger.info(f"[Цвета] Начало обработки изображения: {image_path}")
        image = Image.open(image_path).convert('RGB')
        image = image.resize(resize_size)
        logger.info(f"[Цвета] Изображение загружено и уменьшено до {resize_size}")

        data = np.array(image)
        h, w, _ = data.shape
        data = data.reshape((h * w, 3))
        total_pixels = data.shape[0]
        logger.info(f"[Цвета] Данные пикселей подготовлены. Размер: {data.shape}")

        total_clusters = n_dominant + n_secondary
        if total_clusters <= 0:
            logger.warning("[Цвета] Запрошено 0 кластеров. Возвращаю пустые списки.")
            return {"dominant_colors": [], "secondary_colors": []}

        kmeans_k = min(total_clusters, len(data))
        kmeans_k = int(round(kmeans_k * n_coeff))
        kmeans = KMeans(n_clusters=kmeans_k, n_init=10, random_state=42)
        kmeans.fit(data)
        logger.info(f"[Цвета] K-means выполнен с k={kmeans_k}")

        # Получение центроидов
        centroids = kmeans.cluster_centers_
        labels = kmeans.labels_
        label_counts = Counter(labels)

        # Сортировка кластеров
        sorted_clusters = sorted(label_counts.items(), key=lambda item: item[1], reverse=True)
        logger.info(f"[Цвета] Кластеры отсортированы по количеству пикселей: {[c[1] for c in sorted_clusters]}")

        all_colors = []
        for i, (label, count) in enumerate(sorted_clusters):
            centroid = centroids[label]
            percentage = round((count / total_pixels) * 100, 2)

            all_colors.append({
                "rgb": [int(c) for c in centroid],
                "hex": rgb_to_hex(centroid),
                "percent": percentage
            })
            logger.info(f"[Цвета] Цвет {i+1}: RGB {centroid} -> HEX {rgb_to_hex(centroid)} ({percentage}%)")

        dominant_colors = all_colors[:n_dominant]
        secondary_colors = all_colors[n_dominant:n_dominant + n_secondary]

        logger.info(f"[Цвета] Обработка завершена. Доминирующие: {len(dominant_colors)}, Второстепенные: {len(secondary_colors)}")
        return {
            "dominant_colors": dominant_colors,
            "secondary_colors": secondary_colors
        }

    except Exception as e:
        logger.error(f"[Цвета] Ошибка при определении цветов для {image_path}: {e}", exc_info=True)
        return {
            "dominant_colors": [],
            "secondary_colors": []
        }

def classify_colors_by_palette(colors_result: dict) -> dict:
    try:
        logger.info("[Классификация] Начало классификации цветов по палитре (HSV, новый порядок).")
        classified_colors = {}

        all_colors_to_process = colors_result.get("dominant_colors", []) + colors_result.get("secondary_colors", [])

        if not all_colors_to_process:
            logger.info("[Классификация] Нет цветов для классификации.")
            return {}

        for color_info in all_colors_to_process:
            hex_color = color_info.get("hex", "").lstrip("#") # Убираем '#'
            rgb_color = np.array(color_info.get("rgb", []))
            percent = color_info.get("percent", 0.0)

            if not hex_color or len(rgb_color) != 3:
                logger.warning(f"[Классификация] Пропущен цвет с некорректными данными: {color_info}")
                continue

            final_hex = hex_color # По умолчанию, если что-то пойдет не так
            final_rgb_in_palette = rgb_color # По умолчанию, цвет из палитры

            hsv_color = rgb_to_hsv_array(rgb_color.reshape(1, -1))[0] # (H, S, V)
            _, s, v = hsv_color
            saturation_percent = s * 100
            value_percent = v * 100

            # Если V <= 15%, то Черный
            if value_percent <= 15:
                logger.debug(f"[Классификация] Цвет {hex_color} очень темный. Присваиваем класс 'Черный'.")
                final_hex = "000000"
                final_rgb_in_palette = PALETTE_RGB[PALETTE_HEX.index(final_hex)]
            # Если S <= 15%, то ищем близость к монохромным цветам
            elif saturation_percent <= 15:
                logger.debug(f"[Классификация] Цвет {hex_color} имеет низкую насыщенность. Ищем ближайший монохромный.")
                if MONOCHROME_INDICES:
                    palette_hsv_mono = PALETTE_HSV[MONOCHROME_INDICES]
                    distances = np.linalg.norm(palette_hsv_mono - hsv_color, axis=1)
                    closest_idx_in_mono = np.argmin(distances)

                    closest_idx_in_full_palette = MONOCHROME_INDICES[closest_idx_in_mono]
                    final_hex = PALETTE_HEX[closest_idx_in_full_palette]
                    final_rgb_in_palette = PALETTE_RGB[closest_idx_in_full_palette]
                    logger.debug(
                        f"[Классификация] Цвет {hex_color} притянут к монохромному {final_hex} (расстояние: {distances[closest_idx_in_mono]:.4f})"
                        )
                else:
                     logger.warning(f"[Классификация] Нет монохромных цветов в палитре для {hex_color}. Оставляем как есть.")
            # Иначе ищем близость к цветным
            else:
                logger.debug(f"[Классификация] Цвет {hex_color} цветной (S > 15%, V > 15%). Ищем ближайший немонохромный.")
                if NON_MONOCHROME_INDICES:
                    palette_hsv_non_mono = PALETTE_HSV[NON_MONOCHROME_INDICES]
                    distances = np.linalg.norm(palette_hsv_non_mono - hsv_color, axis=1)
                    closest_idx_in_non_mono = np.argmin(distances)

                    closest_idx_in_full_palette = NON_MONOCHROME_INDICES[closest_idx_in_non_mono]
                    final_hex = PALETTE_HEX[closest_idx_in_full_palette]
                    final_rgb_in_palette = PALETTE_RGB[closest_idx_in_full_palette]
                    logger.debug(f"[Классификация] Цвет {hex_color} притянут к цветному {final_hex} (расстояние: {distances[closest_idx_in_non_mono]:.4f})")
                else:
                     logger.warning(f"[Классификация] Нет немонохромных цветов в палитре для {hex_color}. Оставляем дефолт.")

            # Классификация по палитре
            color_class = HEX_TO_CLASS.get(final_hex, "Неизвестно")
            logger.info(f"[Классификация] Цвет {hex_color} ({percent}%) -> Палитра {final_hex} -> Класс {color_class}")

            # Суммируем повторяющиеся классы
            if color_class in classified_colors:
                classified_colors[color_class]["percent"] += percent
                classified_colors[color_class]["hex"] = f"#{final_hex}"
            else:
                classified_colors[color_class] = {
                    "percent": percent,
                    "hex": f"#{final_hex}" # Добавляем '#'
                }

        for class_name in classified_colors:
            classified_colors[class_name]["percent"] = round(classified_colors[class_name]["percent"], 2)

        logger.info(f"[Классификация] Классификация завершена. Результат: {classified_colors}")
        return classified_colors

    except Exception as e:
        logger.error(f"[Классификация] Ошибка при классификации цветов: {e}", exc_info=True)
        return {}
