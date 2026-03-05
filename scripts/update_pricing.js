const pricingData = [
    { id: "3770000717006", psf: 1180, esf: 700, wsf: 1280, eur: 6.17 },
    { id: "3770000717013", psf: 1180, esf: 700, wsf: 1280, eur: 6.14 },
    { id: "3770000717075", psf: 2180, esf: 1290, wsf: 2380, eur: 7.69 },
    { id: "3770000717327", psf: 2280, esf: 1360, wsf: 2480, eur: 9.45 },
    { id: "3770000717310", psf: 1980, esf: 1180, wsf: 2180, eur: 8.27 },
    { id: "3770000717815", psf: 1880, esf: 1120, wsf: 1980, eur: 7.88 }, // YÜZ BAKIM (fixed barcode conflict)
    { id: "3770000717822", psf: 880, esf: 520, wsf: 980, eur: 4.10 },
    { id: "3770000717839", psf: 720, esf: 430, wsf: 780, eur: 3.43 },
    { id: "3667235000525", psf: 1080, esf: 640, wsf: 1180, eur: 4.90 },
    { id: "3667235000686", psf: 490, esf: 290, wsf: 540, eur: 2.75 },
    { id: "3770000717211", psf: 1980, esf: 1180, wsf: 2180, eur: 7.15 },
    { id: "3770000717051", psf: 1180, esf: 700, wsf: 1280, eur: 4.76 },
    { id: "3770000717068", psf: 1280, esf: 760, wsf: 1380, eur: 5.50 },
    { id: "3770000717020", psf: 1180, esf: 700, wsf: 1280, eur: 4.67 },
    { id: "3770000717082", psf: 1480, esf: 880, wsf: 1580, eur: 5.70 },
    { id: "3770000717242", psf: 1480, esf: 880, wsf: 1580, eur: 6.08 },
    { id: "3667235000648", psf: 1380, esf: 820, wsf: 1480, eur: 6.20 },
    { id: "3770000717044", psf: 1180, esf: 700, wsf: 1280, eur: 6.84 },
    { id: "3770000717594", psf: 2180, esf: 1290, wsf: 2380, eur: 11.51 },
    { id: "3770000717099", psf: 460, esf: 270, wsf: 480, eur: 2.01 },
    { id: "3770000717389", psf: 1680, esf: 998, wsf: 1780, eur: 7.68 },
    { id: "3770000717037", psf: 1080, esf: 640, wsf: 1180, eur: 5.23 },
    { id: "3770000717532", psf: 1880, esf: 1120, wsf: 1980, eur: 7.55 },
    { id: "3770000717198", psf: 1180, esf: 700, wsf: 1280, eur: 4.90 },
    { id: "3770000717617", psf: 1880, esf: 1120, wsf: 1980, eur: 8.90 },
    { id: "3770000717112", psf: 580, esf: 340, wsf: 620, eur: 2.70 },
    { id: "3770000717693", psf: 520, esf: 310, wsf: 580, eur: 2.79 },
    { id: "3770000717709", psf: 420, esf: 250, wsf: 460, eur: 2.45 },
    { id: "3770000717297", psf: 690, esf: 410, wsf: 760, eur: 3.55 },
    { id: "3770000717679", psf: 600, esf: 360, wsf: 660, eur: 3.15 },
    { id: "3770000717518", psf: 480, esf: 285, wsf: 520, eur: 2.41 },
    { id: "3770000717662", psf: 880, esf: 520, wsf: 980, eur: 4.25 },
    { id: "3770000717372", psf: 780, esf: 460, wsf: 880, eur: 3.42 },
    { id: "3770000717570", psf: 1180, esf: 700, wsf: 1280, eur: 5.80 },
    { id: "3770000717563", psf: 1280, esf: 760, wsf: 1380, eur: 6.90 },
    { id: "3770000717587", psf: 1280, esf: 760, wsf: 1380, eur: 6.15 }, // GÜNEŞ SERİSİ
    { id: "3770000717334", psf: 1480, esf: 880, wsf: 1580, eur: 8.80 },
    { id: "3770000717549", psf: 880, esf: 520, wsf: 980, eur: 5.13 },
    { id: "3770000717402", psf: 1280, esf: 760, wsf: 1380, eur: 6.15 },
    { id: "3770000717129", psf: 980, esf: 580, wsf: 1080, eur: 4.15 },
    { id: "3770000717396", psf: 1680, esf: 990, wsf: 1780, eur: 6.90 },
    { id: "3770000717150", psf: 680, esf: 398, wsf: 740, eur: 4.54 },
    { id: "3770000717624", psf: 820, esf: 480, wsf: 880, eur: 4.00 },
    { id: "3770000717143", psf: 940, esf: 560, wsf: 980, eur: 4.40 },
    { id: "3770000717136", psf: 1080, esf: 640, wsf: 1180, eur: 4.20 },
    { id: "3770000717303", psf: 1180, esf: 700, wsf: 1280, eur: 4.90 },
    { id: "3770000717631", psf: 480, esf: 285, wsf: 540, eur: 2.68 }
];

db = db.getSiblingDB('rosap_db');
const EUR_RATE = 51;
const TAX_RATE = 1.20;

let updated = 0;

for (const p of pricingData) {
    const price_51 = Math.round(p.eur * EUR_RATE);
    const cost = Math.round(price_51 * TAX_RATE);

    db.products.updateOne(
        { id: p.id },
        {
            $set: {
                psf_price: p.psf,
                esf_price: p.esf,
                wsf_price: p.wsf,
                price_eur: p.eur,
                price_51: price_51,
                cost: cost
            }
        }
    );
    updated++;
}

console.log(`Updated pricing for ${updated} products.`);
