#!/bin/bash
# ============================================================
# La Rosee Deploy Script
# Kullanım: ./scripts/deploy.sh
# ============================================================
set -e

EC2_HOST="${EC2_HOST:-ec2-user@your-ec2-ip}"
EC2_KEY="${EC2_KEY:-~/.ssh/your-key.pem}"
PROJECT_DIR="/home/ec2-user/la-rosee"

echo "🚀 La Rosee Deploy başlıyor..."
echo "   Host: $EC2_HOST"
echo ""

# 1. Git push (lokal)
echo "📦 1/4 — Git push..."
git push origin main

# 2. SSH → Pull + Rebuild
echo "🔄 2/4 — EC2'de git pull..."
ssh -i "$EC2_KEY" "$EC2_HOST" << 'EOF'
  cd /home/ec2-user/la-rosee
  git pull origin main
EOF

# 3. Docker rebuild
echo "🐳 3/4 — Docker rebuild..."
ssh -i "$EC2_KEY" "$EC2_HOST" << 'EOF'
  cd /home/ec2-user/la-rosee
  docker compose -f docker-compose.rosap.yml build backend
  docker compose -f docker-compose.rosap.yml up -d --no-deps backend
EOF

# 4. Health check
echo "🏥 4/4 — Health check..."
sleep 5
ssh -i "$EC2_KEY" "$EC2_HOST" "curl -sf http://localhost:8000/health || echo '❌ Health check failed'"

echo ""
echo "✅ Deploy tamamlandı!"
