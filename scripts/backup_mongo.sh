#!/bin/bash
# ============================================================
# La Rosee MongoDB Backup
# Cron: 0 3 * * * /home/ec2-user/la-rosee/scripts/backup_mongo.sh
# ============================================================
set -e

BACKUP_DIR="/home/ec2-user/backups/mongo"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# S3 bucket (opsiyonel)
S3_BUCKET="${S3_BUCKET:-}"

mkdir -p "$BACKUP_DIR"

echo "📦 MongoDB Backup: $DATE"

# Docker container'dan dump
docker exec rosap-mongo mongodump \
  --username="${MONGO_USER:-rosap_admin}" \
  --password="${MONGO_PASS}" \
  --authenticationDatabase=admin \
  --db=rosap_db \
  --out="/backup/${DATE}"

# Container'dan host'a kopyala
docker cp rosap-mongo:/backup/${DATE} "${BACKUP_DIR}/${DATE}"

# Sıkıştır
tar -czf "${BACKUP_DIR}/${DATE}.tar.gz" -C "${BACKUP_DIR}" "${DATE}"
rm -rf "${BACKUP_DIR}/${DATE}"

echo "✅ Backup: ${BACKUP_DIR}/${DATE}.tar.gz"

# S3'e yükle (bucket tanımlıysa)
if [ -n "$S3_BUCKET" ]; then
  aws s3 cp "${BACKUP_DIR}/${DATE}.tar.gz" "s3://${S3_BUCKET}/mongo-backups/${DATE}.tar.gz"
  echo "☁️  S3'e yüklendi: s3://${S3_BUCKET}/mongo-backups/${DATE}.tar.gz"
fi

# Eski backupları temizle
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete
echo "🧹 ${RETENTION_DAYS} günden eski backuplar silindi"
