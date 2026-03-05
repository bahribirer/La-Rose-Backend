#!/bin/bash
# ============================================================
# La Rosee MongoDB Auth Setup
# EC2 sunucusunda çalıştırılacak
# ============================================================
set -e

MONGO_USER="rosap_admin"
MONGO_PASS=$(openssl rand -hex 16)
DB_NAME="rosap_db"

echo "🔐 MongoDB Auth Kurulumu"
echo "========================"

# 1. Admin user oluştur
mongosh --eval "
  use admin
  db.createUser({
    user: '${MONGO_USER}',
    pwd: '${MONGO_PASS}',
    roles: [
      { role: 'readWrite', db: '${DB_NAME}' },
      { role: 'dbAdmin', db: '${DB_NAME}' }
    ]
  })
  print('✅ User created')
"

echo ""
echo "============================================"
echo "✅ MongoDB user oluşturuldu!"
echo ""
echo "📋 .env dosyasını şu şekilde güncelleyin:"
echo "MONGO_URI=mongodb://${MONGO_USER}:${MONGO_PASS}@localhost:27017/${DB_NAME}?authSource=admin"
echo ""
echo "⚠️  SONRA mongod'u --auth ile yeniden başlatın:"
echo "    sudo systemctl stop mongod"
echo "    sudo sed -i 's/#security:/security:\\n  authorization: enabled/' /etc/mongod.conf"
echo "    sudo systemctl start mongod"
echo "============================================"
