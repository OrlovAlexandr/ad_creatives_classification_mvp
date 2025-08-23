#!/bin/sh

# Ожидание готовности MinIO
until mc alias set minio http://minio:9000 "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}"; do
    echo "Waiting for MinIO..."
    sleep 1
done

# Создаем бакеты
mc mb minio/creatives --ignore-existing
mc mb minio/models --ignore-existing

# Устанавливаем политики доступа
mc anonymous set none minio/creatives
mc anonymous set public minio/creatives

# Копируем начальные данные
if [ -f "/minio_init/creatives/default.jpg" ]; then
    mc cp /minio_init/creatives/default.jpg minio/creatives/
fi

if [ -f "/minio_init/models/yolov8m.pt" ]; then
    mc cp /minio_init/models/yolov8m.pt minio/models/
fi

if [ -f "/minio_init/models/best_multimodal_bert.pt" ]; then
    mc cp /minio_init/models/best_multimodal_bert.pt minio/models/
fi

if [ -d "/minio_init/models/easy_ocr" ]; then
    mc cp -r /minio_init/models/easy_ocr minio/models/
fi

echo "MinIO initialization completed successfully"