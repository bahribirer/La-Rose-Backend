# 🌐 Nginx Service

Bu klasör, **reverse proxy ve statik frontend servislerini sunan Nginx yapılandırmasını** içerir.  

Nginx, aşağıdaki yönlendirmeleri yapar:  
- `/api/` → **Backend (FastAPI)**  
- `/connection/websocket` → **Centrifugo WebSocket**  
- `/grafana/` → **Grafana (sub-path)**  
- `/` → **Frontend (statik HTML/JS)**  

---

## 📂 İçerik

- `nginx.conf` → Tüm proxy kurallarını tanımlar  
- `frontend/` → Statik frontend dosyaları (index.html vb.)  

---

## 🚀 Çalıştırma

docker compose up nginx


## 🚀 Backend API Testi

curl http://localhost/api/
{"message": "📡 Stock Backend is running!"}

## 🚀 Centrifugo WebSocket Testi
Tarayıcı konsolundan (veya websocat CLI ile):

✅ Connected yazısı görünmelidir.

## 🚀 Grafana Proxy Testi
Tarayıcıdan: http://localhost/grafana/

Login ekranı gelmeli (admin/admin)

Sub-path yönlendirmesi (/grafana/) doğru çalışmalı


## 🚀 Frontend Testi
Tarayıcıdan: http://localhost/
frontend/index.html açılmalı

API çağrıları /api/... üzerinden backend’e gitmeli

