const mapping = {
    "3770000717006": "Organik Shea Yağlı Nemlendirici Yüz Kremi",
    "3770000717013": "Organik Salatalık Özlü Nemlendirici Jel-Krem",
    "3770000717075": "5 Organik Bitkisel Yağlı Dolgunlaştırıcı Yüz Serumu",
    "3770000717327": "Organik Havuç ve Kayısı Özlü Parlaklık Veren Yüz Serumu",
    "3770000717310": "Hyaluronic Asit Bazlı Nemlendirici Yüz Serumu",
    "3770000717815": "Çinko ve Organik Meyve Asitli Leke Karşıtı Arındırıcı Serum",
    "3770000717822": "Leke Önleyici Renkli Kapatıcılı Stik",
    "3770000717839": "Sivilce Karşıtı Renkli Düzeltici Stik yedeği",
    "3667235000525": "Sivilce Karşıtı Yüz Temizleme Jeli - YEDEĞİ",
    "3667235000686": "Sivilce Karşıtı Yüz Temizleme Jel Şişesi",
    "3770000717211": "Organik Aloe Veralı Yorgunluk Karşıtı Göz Çevresi Stik",
    "3770000717051": "Ultra Yumuşak Organik Çiçek Solüsyonlu Makyaj Temizleyici Misel Jel",
    "3770000717068": "Organik Papatya Çiçekli Nemlendirici Tonik Losyon",
    "3770000717020": "Organik Aloe Veralı Yumuşak Yüz Peelingi",
    "3770000717082": "Beyaz Kil İçeren 3'ü 1 Arada Yenileyici Stik Maske",
    "3770000717242": "Organik Tatlı Badem Yağı İçeren Besleyici Stik Maske",
    "3667235000648": "Makyaj Temizleme Balmı",
    "3770000717044": "Organik Ayçiçek Çekirdeği Yağlı Temizleyici Duş Yağı",
    "3770000717594": "Organik Ayçiçek Çekirdeği Yağlı Temizleyici Duş Yağı - YEDEĞİ",
    "3770000717099": "Organik Shea Yağlı Ultra Hafif Besleyici ve Nemlendirici Sabun",
    "3770000717389": "Şeker ve Organik Bitkisel Yağlı Besleyici Vücut Peelingi",
    "3770000717037": "Organik Shea Yağlı Nemlendirici Vücut Kremi",
    "3770000717532": "Organik Shea Yağlı Nemlendirici Vücut Kremi",
    "3770000717198": "Bitkisel Yağlar ve Bal Mumlu SOS Onarıcı Balmı",
    "3770000717617": "Organik Bitkisel Yağlı Besleyici Bakım Yağı",
    "3770000717112": "Organik Şifalı Bitkili Ultra Onarıcı El Kremi",
    "3770000717693": "Organik Shea Yağı İçeren Besleyici Dudak Stik Balmı",
    "3770000717709": "Organik Shea Yağı İçeren Besleyici Dudak Stik Balmı - YEDEĞİ",
    "3770000717297": "Organik Shea Yağlı Besleyici Renkli Dudak Balmı",
    "3770000717679": "Organik Shea Yağı İçeren Besleyici Renkli Dudak Stik Balmı - YEDEĞİ",
    "3770000717518": "Organik Nane Aromalı Diş Macunu",
    "3770000717662": "Probiyotikli Ferahlatıcı Deodorant",
    "3770000717372": "Probiyotikli Ferahlatıcı Deodorant - YEDEĞİ",
    "3770000717570": "Organik Kayısı Yağlı SPF 30 Yüksek Korumalı Güneş Koruyucu Süt",
    "3770000717563": "Organik Kayısı Yağı İçeren SPF 30 Yüksek Korumalı Güneş Koruyucu Yağı",
    "3770000717587": "Organik Kayısı Yağlı SPF 50+ Çok Yüksek Koruma Sağlayan Güneş Koruyucu Süt",
    "3770000717334": "Organik Kayısı Yağlı SPF 50 Yüksek Korumalı Güneş Koruyucu Yağı",
    "3770000717549": "Organik Kayısı Yağlı SPF 50 Yüksek Korumalı Güneş Koruyucu Stik",
    "3770000717402": "Organik Kayısı Yağlı SPF 50+ Çok Yüksek Korumalı Çocuk Güneş Koruyucu Süt",
    "3770000717129": "MPLR Organik Bitkisel Gliserin İçeren Ultra Hassas Yıkama Jeli",
    "3770000717396": "MPLR Bio Bitkisel Gliserin İçeren Ultra Hassas Temizleme Jeli",
    "3770000717150": "MPLR Rahatlatıcı Sıvı Merhem Sızma Zeytinyağı",
    "3770000717624": "MPLR Organik Aloe Veralı Temizleme Suyu",
    "3770000717143": "MPLR Organik Tatlı Badem Yağlı Temizleme Sütü",
    "3770000717136": "MPLR Organik Shea Yağı ve Aloe Veralı Nemlendirici Krem",
    "3770000717303": "MPKR Bitkisel Yağlar ve Bal Mumlu SOS Onarıcı Balsam",
    "3770000717631": "MPLR Organik Çilekli Diş Macunu"
};

db = db.getSiblingDB('rosap_db');
let updatedCount = 0;

for (const [id, trName] of Object.entries(mapping)) {
    const result = db.products.updateOne(
        { id: id },
        { $set: { name: trName } }
    );
    if (result.matchedCount > 0) {
        console.log(`Updated ID: ${id} -> ${trName}`);
        updatedCount++;
    } else {
        console.log(`Warning: GTIN ${id} not found in DB.`);
    }
}

console.log(`Migration completed. Total updated: ${updatedCount}`);
