"""
Migration: 47 ürüne slug ve name_tr alanlarını ekle
Çalıştırma: python migrate_product_web_fields.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Web sitesindeki products.json'dan alınan barkod → {slug, name_tr} eşlemesi
WEB_PRODUCTS = {
    "3770000717006": {"slug": "moisturizing-cream-organic-shea-butter", "name_tr": "Organik Shea Yağlı Nemlendirici Yüz Kremi"},
    "3770000717013": {"slug": "moisturizing-cream-gel-organic-cucumber", "name_tr": "Organik Salatalık Özlü Nemlendirici Jel-Krem"},
    "3770000717075": {"slug": "plumping-face-serum-5-organic-vegetal-oils", "name_tr": "5 Organik Bitkisel Yağlı Dolgunlaştırıcı Yüz Serumu"},
    "3770000717327": {"slug": "radiance-concentrate-organic-carrot-and-apricot", "name_tr": "Organik Havuç ve Kayısı Özlü Parlaklık Veren Yüz Serumu"},
    "3770000717310": {"slug": "hydrating-face-serum-hyaluronic-acid", "name_tr": "Hyaluronic Asit Bazlı Nemlendirici Yüz Serumu"},
    "3770000717815": {"slug": "purifying-anti-blemish-serum-zinc-and-organic-fruit-acide", "name_tr": "Çinko ve Organik Meyve Asitli Leke Karşıtı Arındırıcı Serum"},
    "3770000717822": {"slug": "refillable-anti-blemish-tinted-concealer-stick", "name_tr": "Leke Önleyici Renkli Kapatıcılı Stick"},
    "3770000717839": {"slug": "anti-blemish-tinted-concealer-stick-refill", "name_tr": "Leke Önleyici Renkli Kapatıcılı Stick - REFİLL"},
    "3770000717211": {"slug": "anti-fatigue-eye-contour-organic-aloe-vera", "name_tr": "Organik Aloe Veralı Yorgunluk Karşıtı Göz Çevresi Stick"},
    "3770000717365": {"slug": "nourishing-body-oil-organic-rose-hip", "name_tr": "Organik Kuşburnu Yağlı Besleyici Vücut Yağı"},
    "3770000717372": {"slug": "nourishing-body-butter-organic-cocoa-butter", "name_tr": "Organik Kakao Yağlı Besleyici Vücut Yağı"},
    "3770000717389": {"slug": "rehydrating-shower-gel-organic-aloe-vera", "name_tr": "Organik Aloe Vera Özlü Nemlendirici Duş Jeli"},
    "3770000717396": {"slug": "smoothing-body-scrub-organic-cane-sugar", "name_tr": "Organik Kamış Şekeri İçeren Pürüzsüzleştirici Vücut Peelingi"},
    "3770000717402": {"slug": "silky-body-lotion-organic-aloe-vera", "name_tr": "Organik Aloe Vera Özlü İpeksi Vücut Losyonu"},
    "3770000717419": {"slug": "intensive-nourishing-body-balm-organic-shea-butter", "name_tr": "Organik Shea Yağlı Yoğun Besleyici Vücut Balmı"},
    "3770000717228": {"slug": "purifying-cleansing-gel-organic-aloe-vera", "name_tr": "Organik Aloe Vera İçeren Arındırıcı Temizleme Jeli"},
    "3770000717235": {"slug": "gentle-cleansing-micellar-water-organic-aloe-vera", "name_tr": "Organik Aloe Vera İçeren Nazif Temizleyici Misel Suyu"},
    "3770000717242": {"slug": "gentle-exfoliating-scrub-organic-aloe-vera", "name_tr": "Organik Aloe Vera İçeren Nazif Peeling"},
    "3770000717426": {"slug": "nourishing-hand-cream-organic-shea-butter", "name_tr": "Organik Shea Yağlı Besleyici El Kremi"},
    "3770000717433": {"slug": "repairing-foot-cream-organic-shea-butter", "name_tr": "Organik Shea Yağlı Onarıcı Ayak Kremi"},
    "3770000717440": {"slug": "2-in-1-shampoo-and-conditioner-organic-aloe-vera", "name_tr": "Organik Aloe Vera İçeren 2'si 1 Arada Şampuan ve Saç Kremi"},
    "3770000717457": {"slug": "nourishing-hair-mask-organic-argan-oil", "name_tr": "Organik Argan Yağlı Besleyici Saç Maskesi"},
    "3770000717464": {"slug": "nourishing-hair-oil-organic-argan-oil", "name_tr": "Organik Argan Yağlı Besleyici Saç Yağı"},
    "3770000717150": {"slug": "very-high-protection-sun-cream-spf50", "name_tr": "Çok Yüksek Korumalı Güneş Kremi SPF50"},
    "3770000717167": {"slug": "very-high-protection-sun-milk-spf50-for-body", "name_tr": "Vücut İçin Çok Yüksek Korumalı Güneş Sütü SPF50"},
    "3770000717174": {"slug": "very-high-protection-sun-stick-spf50", "name_tr": "Çok Yüksek Korumalı Güneş Çubuğu SPF50"},
    "3770000717181": {"slug": "spf50-sun-mist-for-face-and-body", "name_tr": "Yüz ve Vücut İçin SPF50 Güneş Sisi"},
    "3770000717198": {"slug": "after-sun-soothing-gel-organic-aloe-vera", "name_tr": "Organik Aloe Vera İçeren Güneş Sonrası Sakinleştirici Jel"},
    "3770000717471": {"slug": "moisturizing-baby-lotion-organic-chamomile", "name_tr": "Organik Papatya İçeren Nemlendirici Bebek Losyonu"},
    "3770000717488": {"slug": "gentle-cleansing-baby-gel-organic-chamomile", "name_tr": "Organik Papatya İçeren Nazif Temizleyici Bebek Jeli"},
    "3770000717495": {"slug": "protective-baby-balm-organic-calendula", "name_tr": "Organik Calendula İçeren Koruyucu Bebek Balmı"},
    "3770000717501": {"slug": "ultra-gentle-baby-cleansing-gel-organic-chamomile", "name_tr": "Organik Papatya İçeren Ultra Nazif Bebek Temizleme Jeli"},
    "3770000717518": {"slug": "gentle-baby-massage-oil-organic-chamomile", "name_tr": "Organik Papatya İçeren Nazif Bebek Masaj Yağı"},
    "3770000717099": {"slug": "moisturizing-bb-cream-spf15", "name_tr": "Nemlendirici BB Krem SPF15"},
    "3770000717105": {"slug": "fluid-foundation-spf20", "name_tr": "Akışkan Fondöten SPF20"},
    "3770000717112": {"slug": "mattifying-primer-base", "name_tr": "Matlaştırıcı Astar Baz"},
    "3770000717129": {"slug": "long-lasting-mascara", "name_tr": "Uzun Süre Kalıcı Maskara"},
    "3770000717136": {"slug": "long-lasting-lip-gloss", "name_tr": "Uzun Süre Kalıcı Dudak Parlatıcısı"},
    "3770000717143": {"slug": "mattifying-loose-powder", "name_tr": "Matlaştırıcı Loose Pudra"},
    "3770000717525": {"slug": "daily-intimate-hygiene-gel-organic-aloe-vera", "name_tr": "Organik Aloe Vera İçeren Günlük İntim Hijyen Jeli"},
    "3770000717532": {"slug": "deodorant-spray-24h-organic-aloe-vera", "name_tr": "Organik Aloe Vera İçeren 24 Saat Deodorant Spreyi"},
    "3770000717549": {"slug": "roll-on-deodorant-48h-organic-aloe-vera", "name_tr": "Organik Aloe Vera İçeren 48 Saat Roll-On Deodorant"},
    "3770000717556": {"slug": "lip-balm-organic-shea-butter", "name_tr": "Organik Shea Yağlı Dudak Balmı"},
    "3770000717785": {"slug": "illuminating-fluid-organic-saffron-and-vitamin-c", "name_tr": "Organik Safran ve C Vitamini İçeren Aydınlatıcı Fluid"},
    "3770000717792": {"slug": "radiance-booster-organic-rose-water", "name_tr": "Organik Gül Suyu ile Parlaklık Güçlendirici"},
    "3770000717808": {"slug": "detox-face-mask-organic-white-clay", "name_tr": "Organik Beyaz Kil ile Detoks Yüz Maskesi"},
    "3770000717563": {"slug": "morning-ritual-set", "name_tr": "Sabah Ritüeli Seti"},
    "3770000717570": {"slug": "evening-ritual-set", "name_tr": "Akşam Ritüeli Seti"},
}


async def run():
    from app.core.database import db

    matched = 0
    not_found = []

    for gtin, web_data in WEB_PRODUCTS.items():
        result = await db.products.update_one(
            {"id": gtin},
            {"$set": {
                "slug": web_data["slug"],
                "name_tr": web_data["name_tr"],
            }}
        )
        if result.matched_count > 0:
            matched += 1
            print(f"✅ {gtin} → {web_data['slug']}")
        else:
            not_found.append(gtin)
            print(f"⚠️  {gtin} — DB'de bulunamadı")

    print(f"\nToplam: {matched}/{len(WEB_PRODUCTS)} ürün güncellendi")
    if not_found:
        print(f"Bulunamayanlar: {not_found}")


if __name__ == "__main__":
    asyncio.run(run())
