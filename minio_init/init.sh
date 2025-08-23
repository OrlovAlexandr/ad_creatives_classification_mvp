until mc alias set minio http://minio:9000 minioadmin minioadmin; do
  echo "Waiting for MinIO..."
  sleep 1
done

# Создаем бакеты
mc mb minio/creatives --ignore-existing
mc mb minio/models --ignore-existing

mc anonymous set none minio/creatives
mc anonymous set public minio/creatives
# mc anonymous set public minio/models

# Копируем начальные данные 
mc cp /minio_init/creatives/default.jpg minio/creatives/

mc cp /minio_init/models/yolov8m.pt minio/models/
mc cp /minio_init/models/best_multimodal_bert.pt minio/models/
mc cp -r /minio_init/models/easy_ocr minio/models/
