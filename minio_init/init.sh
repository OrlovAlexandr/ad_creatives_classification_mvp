#!/bin/sh
set -e

# Ждём готовности MinIO (пока не ответит на запрос)
until mc ls minio/; do
  echo "Waiting for MinIO..."
  sleep 10
done

mc mb minio/${MINIO_BUCKET:-creatives} --ignore-existing
mc mb minio/${MODELS_BUCKET:-models} --ignore-existing

mc anonymous set public minio/${MINIO_BUCKET:-creatives}
mc anonymous set public minio/${MODELS_BUCKET:-models}

if [ -d "/minio_init/models" ]; then
  echo "Uploading models to MinIO..."
  mc cp -r /minio_init/models/ minio/${MODELS_BUCKET:-models}/
fi

if [ -d "/minio_init/creatives" ]; then
  echo "Uploading sample creatives to MinIO..."
  mc cp -r /minio_init/creatives/ minio/${MINIO_BUCKET:-creatives}/
fi

echo "MinIO initialization completed successfully"
