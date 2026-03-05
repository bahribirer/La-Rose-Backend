const masterList = [
    { cat: "YÜZ BAKIM", id: "3770000717006" },
    { cat: "YÜZ BAKIM", id: "3770000717013" },
    { cat: "YÜZ BAKIM", id: "3770000717075" },
    { cat: "YÜZ BAKIM", id: "3770000717327" },
    { cat: "YÜZ BAKIM", id: "3770000717310" },
    { cat: "YÜZ BAKIM", id: "3770000717815" },
    { cat: "YÜZ BAKIM", id: "3770000717822" },
    { cat: "YÜZ BAKIM", id: "3770000717839" },
    { cat: "YÜZ BAKIM", id: "3667235000525" },
    { cat: "YÜZ BAKIM", id: "3667235000686" },
    { cat: "YÜZ BAKIM", id: "3770000717211" },
    { cat: "YÜZ BAKIM", id: "3770000717051" },
    { cat: "YÜZ BAKIM", id: "3770000717068" },
    { cat: "YÜZ BAKIM", id: "3770000717020" },
    { cat: "YÜZ BAKIM", id: "3770000717082" },
    { cat: "YÜZ BAKIM", id: "3770000717242" },
    { cat: "YÜZ BAKIM", id: "3667235000648" },
    { cat: "VÜCUT BAKIM", id: "3770000717044" },
    { cat: "VÜCUT BAKIM", id: "3770000717594" },
    { cat: "VÜCUT BAKIM", id: "3770000717099" },
    { cat: "VÜCUT BAKIM", id: "3770000717389" },
    { cat: "VÜCUT BAKIM", id: "3770000717037" },
    { cat: "VÜCUT BAKIM", id: "3770000717532" },
    { cat: "VÜCUT BAKIM", id: "3770000717198" },
    { cat: "VÜCUT BAKIM", id: "3770000717617" },
    { cat: "VÜCUT BAKIM", id: "3770000717112" },
    { cat: "DUDAK BAKIM", id: "3770000717693" },
    { cat: "DUDAK BAKIM", id: "3770000717709" },
    { cat: "DUDAK BAKIM", id: "3770000717297" },
    { cat: "DUDAK BAKIM", id: "3770000717679" },
    { cat: "HİJYEN", id: "3770000717518" },
    { cat: "HİJYEN", id: "3770000717662" },
    { cat: "HİJYEN", id: "3770000717372" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717570" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717563" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717587" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717334" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717549" },
    { cat: "GÜNEŞ SERİSİ", id: "3770000717402" },
    { cat: "Mon Petit LR", id: "3770000717129" },
    { cat: "Mon Petit LR", id: "3770000717396" },
    { cat: "Mon Petit LR", id: "3770000717150" },
    { cat: "Mon Petit LR", id: "3770000717624" },
    { cat: "Mon Petit LR", id: "3770000717143" },
    { cat: "Mon Petit LR", id: "3770000717136" },
    { cat: "Mon Petit LR", id: "3770000717303" },
    { cat: "Mon Petit LR", id: "3770000717631" }
];

db = db.getSiblingDB('rosap_db');
let updated = 0;

for (const item of masterList) {
    const res = db.products.updateOne(
        { id: item.id },
        { $set: { category: item.cat } }
    );
    if (res.modifiedCount > 0 || res.matchedCount > 0) {
        updated++;
    }
}

console.log(`Successfully forced categories for ${updated} products.`);
const unspecifiedCount = db.products.countDocuments({ category: { $in: [null, "", "Belirtilmemiş", "belirtilmemiş"] } });
console.log(`Unspecified categories remaining: ${unspecifiedCount}`);
