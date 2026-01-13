# 📡 Backend Service

Bu klasör, **FastAPI tabanlı Backend API**’yi içerir.  
Backend, PostgreSQL veritabanına bağlanır, hisse senedi fiyatları ve subscriber metric verilerini API üzerinden sunar.

---

## 📂 İçerik

- `Dockerfile` → Backend servisi için imaj tanımı  
- `requirements.txt` → Python bağımlılıkları  
- `main.py` → FastAPI uygulaması (API endpoint’leri)  

---

## 🧪 Lokal Test
curl http://localhost/api/

{"message": "📡 Stock Backend is running!"}

## 🧪 Metric listesi
GET /metrics/subscriber?limit=50

En son subscriber_metrics kayıtlarını getirir.

curl "http://localhost/api/metrics/subscriber?limit=5"

[
  {"ts":"2025-09-07 05:46:04","flush_duration_ms":12.34,"records_flushed":7},
  {"ts":"2025-09-07 05:47:01","flush_duration_ms":9.11,"records_flushed":5}
]

## 🧪 Metric kaydetme
POST /metrics

Subscriber’dan gelen flush loglarını DB’ye kaydeder.

curl -X POST http://localhost/api/metrics \
  -H "Content-Type: application/json" \
  -d '{"flush_duration_ms": 12.34, "records_flushed": 7, "ts": "2025-09-07T05:46:04"}'

  
  {"status": "ok"}


## 🧪 Son fiyat
GET /latest/{stock_name}

Belirtilen hissenin en güncel fiyat kaydını döner.

curl http://localhost/api/latest/AAPL

{
  "timestamp": "2025-09-07 05:46:04.469220+00:00",
  "stock": "AAPL",
  "exchange": "NASDAQ",
  "price": 229.14
}

## 🧪 Zaman aralığında fiyatlar
GET /prices/{stock_name}?start_time=...&end_time=...
Belirli tarih aralığındaki tüm fiyat kayıtlarını getirir.
Tarih formatı: YYYY-MM-DDTHH:MM:SS

curl "http://localhost/api/prices/AAPL?start_time=2025-09-07T00:00:00&end_time=2025-09-07T23:59:59"

[
  {"timestamp":"2025-09-07 05:46:04","stock":"AAPL","exchange":"NASDAQ","price":229.14},
  {"timestamp":"2025-09-07 06:10:00","stock":"AAPL","exchange":"NASDAQ","price":230.42}
]

## 🧪 Ortalama fiyat
GET /average/{stock_name}?start_time=...&end_time=...
Belirli tarih aralığındaki ortalama fiyatı döner.

curl "http://localhost/api/average/AAPL?start_time=2025-09-07T00:00:00&end_time=2025-09-07T23:59:59"

{
  "stock": "AAPL",
  "average_price": 229.78,
  "start_time": "2025-09-07T00:00:00",
  "end_time": "2025-09-07T23:59:59"
}




