const mapping = [
    { cat: "YÜZ BAKIM", id: "3770000717006", name: "Organik Shea Yağlı Nemlendirici Yüz Kremi", ml: "60ml" },
    { cat: "YÜZ BAKIM", id: "3770000717013", name: "Organik Salatalık Özlü Nemlendirici Jel-Krem", ml: "60ml" },
    { cat: "YÜZ BAKIM", id: "3770000717075", name: "5 Organik Bitkisel Yağlı Dolgunlaştırıcı Yüz Serumu", ml: "30ml" },
    { cat: "YÜZ BAKIM", id: "3770000717327", name: "Organik Havuç ve Kayısı Özlü Parlaklık Veren Yüz Serumu", ml: "30ml" },
    { cat: "YÜZ BAKIM", id: "3770000717310", name: "Hyaluronic Asit Bazlı Nemlendirici Yüz Serumu", ml: "30ml" },
    { cat: "YÜZ BAKIM", id: "3770000717815", name: "Çinko ve Organik Meyve Asitli Leke Karşıtı Arındırıcı Serum", ml: "30ml" },
    { cat: "YÜZ BAKIM", id: "3770000717822", name: "Leke Önleyici Renkli Kapatıcılı Stik", ml: "4,5g" },
    { cat: "YÜZ BAKIM", id: "3770000717839", name: "Sivilce Karşıtı Renkli Düzeltici Stik yedeği", ml: "4,5g" },
    { cat: "YÜZ BAKIM", id: "3667235000525", name: "Sivilce Karşıtı Yüz Temizleme Jeli - YEDEĞİ", ml: "400ml" },
    { cat: "YÜZ BAKIM", id: "3667235000686", name: "Sivilce Karşıtı Yüz Temizleme Jel Şişesi", ml: "200ml" },
    { cat: "YÜZ BAKIM", id: "3770000717211", name: "Organik Aloe Veralı Yorgunluk Karşıtı Göz Çevresi Stik", ml: "15ml" },
    { cat: "YÜZ BAKIM", id: "3770000717051", name: "Ultra Yumuşak Organik Çiçek Solüsyonlu Makyaj Temizleyici Misel Jel", ml: "195ml" },
    { cat: "YÜZ BAKIM", id: "3770000717068", name: "Organik Papatya Çiçekli Nemlendirici Tonik Losyon", ml: "200ml" },
    { cat: "YÜZ BAKIM", id: "3770000717020", name: "Organik Aloe Veralı Yumuşak Yüz Peelingi", ml: "60ml" },
    { cat: "YÜZ BAKIM", id: "3770000717082", name: "Beyaz Kil İçeren 3'ü 1 Arada Yenileyici Stik Maske", ml: "75ml" },
    { cat: "YÜZ BAKIM", id: "3770000717242", name: "Organik Tatlı Badem Yağı İçeren Besleyici Stik Maske", ml: "50ml" },
    { cat: "YÜZ BAKIM", id: "3667235000648", name: "Makyaj Temizleme Balmı", ml: "90ml" },
    { cat: "VÜCUT BAKIM", id: "3770000717044", name: "Organik Ayçiçek Çekirdeği Yağlı Temizleyici Duş Yağı", ml: "400ml" },
    { cat: "VÜCUT BAKIM", id: "3770000717594", name: "Organik Ayçiçek Çekirdeği Yağlı Temizleyici Duş Yağı - YEDEĞİ", ml: "800ml" },
    { cat: "VÜCUT BAKIM", id: "3770000717099", name: "Organik Shea Yağlı Ultra Hafif Besleyici ve Nemlendirici Sabun", ml: "100g" },
    { cat: "VÜCUT BAKIM", id: "3770000717389", name: "Şeker ve Organik Bitkisel Yağlı Besleyici Vücut Peelingi", ml: "200g" },
    { cat: "VÜCUT BAKIM", id: "3770000717037", name: "Organik Shea Yağlı Nemlendirici Vücut Kremi", ml: "200ml" },
    { cat: "VÜCUT BAKIM", id: "3770000717532", name: "Organik Shea Yağlı Nemlendirici Vücut Kremi", ml: "400ml" },
    { cat: "VÜCUT BAKIM", id: "3770000717198", name: "Bitkisel Yağlar ve Bal Mumlu SOS Onarıcı Balmı", ml: "20g" },
    { cat: "VÜCUT BAKIM", id: "3770000717617", name: "Organik Bitkisel Yağlı Besleyici Bakım Yağı", ml: "100ml" },
    { cat: "VÜCUT BAKIM", id: "3770000717112", name: "Organik Şifalı Bitkili Ultra Onarıcı El Kremi", ml: "50ml" },
    { cat: "DUDAK BAKIM", id: "3770000717693", name: "Organik Shea Yağı İçeren Besleyici Dudak Stik Balmı", ml: "4,5g" },
    { cat: "DUDAK BAKIM", id: "3770000717709", name: "Organik Shea Yağı İçeren Besleyici Dudak Stik Balmı - YEDEĞİ", ml: "4,5g" },
    { cat: "DUDAK BAKIM", id: "3770000717297", name: "Organik Shea Yağlı Besleyici Renkli Dudak Balmı", ml: "4,5g" },
    { cat: "DUDAK BAKIM", id: "3770000717679", name: "Organik Shea Yağı İçeren Besleyici Renkli Dudak Stik Balmı - YEDEĞİ", ml: "4,5g" },
    { cat: "HİJYEN", id: "3770000717518", name: "Organik Nane Aromalı Diş Macunu", ml: "75ml" },
    { cat: "HİJYEN", id: "3770000717662", name: "Probiyotikli Ferahlatıcı Deodorant", ml: "50ml" },
    { cat: "HİJYEN", id: "3770000717372", name: "Probiyotikli Ferahlatıcı Deodorant - YEDEĞİ", ml: "50ml" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717570", name: "Organik Kayısı Yağlı SPF 30 Yüksek Korumalı Güneş Koruyucu Süt", ml: "150ml" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717563", name: "Organik Kayısı Yağı İçeren SPF 30 Yüksek Korumalı Güneş Koruyucu Yağı", ml: "150ml" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717587", name: "Organik Kayısı Yağlı SPF 50+ Çok Yüksek Koruma Sağlayan Güneş Koruyucu Süt", ml: "150ml" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717334", name: "Organik Kayısı Yağlı SPF 50 Yüksek Korumalı Güneş Koruyucu Yağı", ml: "150ml" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717549", name: "Organik Kayısı Yağlı SPF 50 Yüksek Korumalı Güneş Koruyucu Stik", ml: "15ml" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717402", name: "Organik Kayısı Yağlı SPF 50+ Çok Yüksek Korumalı Çocuk Güneş Koruyucu Süt", ml: "125ml" },
    { cat: "Mon Petit LR", id: "3770000717129", name: "MPLR Organik Bitkisel Gliserin İçeren Ultra Hassas Yıkama Jeli", ml: "400ml" },
    { cat: "Mon Petit LR", id: "3770000717396", name: "MPLR Bio Bitkisel Gliserin İçeren Ultra Hassas Temizleme Jeli", ml: "800ml" },
    { cat: "Mon Petit LR", id: "3770000717150", name: "MPLR Rahatlatıcı Sıvı Merhem Sızma Zeytinyağı", ml: "400ml" },
    { cat: "Mon Petit LR", id: "3770000717624", name: "MPLR Organik Aloe Veralı Temizleme Suyu", ml: "400ml" },
    { cat: "Mon Petit LR", id: "3770000717143", name: "MPLR Organik Tatlı Badem Yağlı Temizleme Sütü", ml: "400ml" },
    { cat: "Mon Petit LR", id: "3770000717136", name: "MPLR Organik Shea Yağı ve Aloe Veralı Nemlendirici Krem", ml: "200ml" },
    { cat: "Mon Petit LR", id: "3770000717303", name: "MPKR Bitkisel Yağlar ve Bal Mumlu SOS Onarıcı Balsam", ml: "20g" },
    { cat: "Mon Petit LR", id: "3770000717631", name: "MPLR Organik Çilekli Diş Macunu", ml: "50ml" }
];

db = db.getSiblingDB('rosap_db');
let updatedCount = 0;
let upsertedCount = 0;

for (const item of mapping) {
    const result = db.products.updateOne(
        { id: item.id },
        {
            $set: {
                name: item.name,
                tr_name: item.name,
                category: item.cat,
                volume: item.ml,
                gtin: item.id
            }
        },
        { upsert: true }
    );
    if (result.matchedCount > 0) {
        console.log(`Updated: ${item.id} -> ${item.name}`);
        updatedCount++;
    } else if (result.upsertedCount > 0) {
        console.log(`Upserted: ${item.id} -> ${item.name}`);
        upsertedCount++;
    }
}

console.log(`Migration completed. Total updated: ${updatedCount}, Total new (upserted): ${upsertedCount}`);
