const mapping = {
    "3770000717044": { tr: "CLEANSING OIL 200 ML", cat: "Yüz Temizleme" }, // Actually shower oil in DB, but mapping to Oil
    "3770000717389": { tr: "CLEANSING FOAM 150 ML", cat: "Yüz Temizleme" },
    "3770000717020": { tr: "GENTLE SCRUB 75 ML", cat: "Yüz Temizleme" },
    "3770000717051": { tr: "TONIC LOTION 200 ML", cat: "Yüz Temizleme" },
    "3770000717150": { tr: "PURIF. MASK 75 ML", cat: "Arındırıcı Bakım" },
    "3770000717022": { tr: "MOIST. MASK 75 ML", cat: "Nemlendirici Bakım" },
    "3770000717006": { tr: "HYDRATING CREAM 60 ML", cat: "Nemlendirici Bakım" },
    "3770000717013": { tr: "HYDRATING GEL 60 ML", cat: "Nemlendirici Bakım" },
    "3770000717372": { tr: "PULPE DE VIE CREAM 40 ML", cat: "Nemlendirici Bakım" },
    "3770000717174": { tr: "REP. CREAM 40 ML", cat: "Nemlendirici Bakım" },
    "3770000717181": { tr: "NOURISHING CREAM 60 ML", cat: "Besleyici Bakım" },
    "3770000717480": { tr: "REGEN. MASK 75 ML", cat: "Yenileyici Bakım" },
    "3770000717211": { tr: "EYE CONTOUR 15 ML", cat: "Göz Çevresi Bakımı" },
    "3770000717501": { tr: "ANTI-IMPERF. SERUM 30 ML", cat: "Serumlar" },
    "3770000717068": { tr: "VIT. RADIANCE SERUM 30 ML", cat: "Serumlar" },
    "3770000717310": { tr: "REP. SERUM 30 ML", cat: "Serumlar" },
    "3770000717365": { tr: "NOUR. FACE OIL 30 ML", cat: "Yüz Yağları" },
    "3770000717060": { tr: "SHOWER CREAM 200 ML", cat: "Vücut Bakımı" },
    "3770000717112": { tr: "BODY SCRUB 200 ML", cat: "Vücut Bakımı" },
    "3770000717077": { tr: "MOIST. BODY MILK 200 ML", cat: "Vücut Bakımı" },
    "3770000717473": { tr: "REP. BODY BALM 200 ML", cat: "Vücut Bakımı" },
    "3770000717084": { tr: "HAND CREAM 50 ML", cat: "El ve Tırnak Bakımı" },
    "3770000717143": { tr: "REGEN. HAND CREAM 50 ML", cat: "El ve Tırnak Bakımı" },
    "3770000717091": { tr: "DEODORANT 50 ML", cat: "Kişisel Hijyen" },
    "3770000717198": { tr: "SUN CREAM SPF30 50 ML", cat: "Güneş Bakımı" },
    "3770000717204": { tr: "SUN CREAM SPF50 50 ML", cat: "Güneş Bakımı" },
    "3770000717213": { tr: "STICK SPF50 15 ML", cat: "Güneş Bakımı" },
    "3770000717327": { tr: "CLEANSING GEL KIDS 400 ML", cat: "Bebek & Çocuk" },
    "3770000717334": { tr: "MOIST. CREAM KIDS 200 ML", cat: "Bebek & Çocuk" },
    "3770000717358": { tr: "MASSAGE OIL KIDS 100 ML", cat: "Bebek & Çocuk" }
};

db = db.getSiblingDB('rosap_db');
let updatedCount = 0;

for (const [id, meta] of Object.entries(mapping)) {
    const result = db.products.updateOne(
        { id: id },
        { $set: { name: meta.tr, category: meta.cat } }
    );
    if (result.matchedCount > 0) {
        console.log(`Updated ID: ${id} -> ${meta.tr}`);
        updatedCount++;
    } else {
        console.log(`Warning: Product ID ${id} not found in DB.`);
    }
}

// Final touch: If name still contains English fragments, try one last replace
db.products.updateMany(
    { name: /Organic/i },
    [{ $set: { name: { $ifNull: ["$tr_name", "$name"] } } }]
);

console.log(`Migration completed. Total exact matches updated: ${updatedCount}`);
