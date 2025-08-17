until mc alias set minio http://minio:9000 minioadmin minioadmin; do
  echo "Waiting for MinIO..."
  sleep 1
done

# Создаем бакеты
mc mb minio/creatives --ignore-existing
mc mb minio/models --ignore-existing

# Копируем начальные данные 
mc cp /minio_init/models/yolov8n.pt minio/models/
mc cp /minio_init/creatives/default.jpg minio/creatives/