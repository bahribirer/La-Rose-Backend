import json
import re
from groq import Groq
from app.core.config import settings

# Initialize Groq Client
client = Groq(api_key=settings.GROQ_API_KEY)

def run_llm(sys_prompt, user_data):
    """
    Executes a prompt against Groq / Llama 3.3.
    Returns clean string content (hopefully JSON).
    """
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"BELGE METNİ:\n{user_data}\n\nLütfen sadece geçerli bir JSON döndür."}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.0
        )
        content = completion.choices[0].message.content.strip()
        
        # Clean Markdown code blocks if present
        match = re.search(r"```(?:json)?\s*(\[.*\]|\{.*\})\s*```", content, re.DOTALL)
        if match: return match.group(1)
        
        # Try to find JSON object in raw text
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            return content[start:end+1]
            
        return content
    except Exception as e:
        print(f"❌ GROQ LLM ERROR: {e}")
        return json.dumps({"error": str(e)})

def diagnose_layout(raw_text):
    """
    Phase 1: Diagnosis
    Determines if the document layout is STANDARD (Horizontal) or SCATTERED (Vertical/Broken).
    """
    print("--- 🧠 Groq Diagnosis: Analyzing Layout Structure... ---")
    
    system_prompt = """
    Sen bir "Veri Yapısı Dedektifi"sin. OCR metninin AKIŞ DÜZENİNİ tespit et.
    
    ANALİZ KRİTERLERİ:

    1. **STANDARD (Sıralı/Satır Bazlı):** - Veriler birbiri ardına mantıklı bir satır düzeninde akıyor mu?
       - Örn: `Tarih -> Barkod -> İsim -> Fiyat` ...sonraki satır... `Tarih -> Barkod...`
       - Küçük kaymalar olsa bile genel akış "Yatay" (Horizontal) mı?

    2. **SCATTERED (Dağınık/Parçalı/Sütun Bazlı):** - Veriler arasındaki bağ kopuk mu? 
       - **Senaryo A (Blok Blok):** Sayfadaki TÜM İsimler alt alta gelmiş, Fiyatlar bambaşka bir yerde toplanmış.
       - **Senaryo B (Parçalı):** Barkodlar bir yanda, İsimler başka bir yanda, Fiyatlar alakasız satırlarda çıkıyor.
       - **Senaryo C (Okuma Hatası):** Bir ürünün fiyatı, ürün isminden 3-4 satır aşağıda veya yukarıda kalmış.
    
    KARAR MANTIĞI:
    - Eğer emin değilsen veya metin çok karışıksa, güvenli liman olarak "SCATTERED" seç.

    Sadece şu JSON'ı döndür:
    { "layout_type": "STANDARD" }  veya { "layout_type": "SCATTERED" }
    """
    
    # Analyze only the first 2500 chars to save tokens/time
    result = run_llm(system_prompt, raw_text[:2500]) 
    try:
        parsed = json.loads(result)
        return parsed.get("layout_type", "STANDARD")
    except:
        return "STANDARD"

def strategy_standard(raw_text):
    print("   -> Teşhis: STANDARD. 'Konumsal Sütun Eşleştirici' (Positional Column Mapper)...")
    
    system_prompt = """
    Sen "Evrensel Tablo Okuyucusu"sun. 
    Görevin: Belgedeki SÜTUN SIRASINI çözmek ve verileri bu sıraya göre eşleştirmek.

    PRENSİP: "İSİMLERE DEĞİL, SIRAYA GÜVEN."
    Belgede "Maliyet" başta ise, satırdaki ilk para Maliyettir. "Fiyat" sondaysa, son para Fiyattır. Tahmin yapma, sırayı takip et.

    ADIM 1: BAŞLIK HARİTASINI ÇIKAR (HEADER MAPPING)
    - Metnin en tepesindeki sütun başlıklarını OKUMA SIRASINA göre tespit et.
    - Örn: Belgede sıra `A -> B -> C -> D` ise, senin şablonun budur.
    - Başlıkları `snake_case` formatına çevir (Örn: "Satış Fiyatı" -> `satis_fiyati`).

    ADIM 2: SATIRLARI VE BLOKLARI AYRIŞTIR
    - Satırları belirlemek için "Çapa" (Tarih/Barkod/SıraNo) mantığını kullan.
    - Her satırın içindeki verileri (Sayılar, Metinler) soldan sağa doğru listele.

    ADIM 3: EŞLEŞTİRME (MAPPING)
    - Bulduğun sayıları, ADIM 1'de çıkardığın başlık sırasına göre dağıt.
    - Örnek: Başlıklar ["maliyet", "kar", "fiyat"] ise;
      * Satırdaki 1. Para -> `maliyet`
      * Satırdaki 2. Para -> `kar`
      * Satırdaki 3. Para -> `fiyat`
    
    - **Küçük Tamsayılar (1, 2, 5):** Bunlar genelde "Miktar" veya "Adet" başlığının altına gelir. Yerini ona göre bul.
    - **Barkod:** 13 haneli sayıyı her zaman `barkod` anahtarına at.

    ÇIKTI FORMATI (JSON):
    {
      "metadata": { ... },
      "dip_toplamlar": { ... },
      "urunler": [
        {
           // ANAHTARLAR, BELGEDEKİ BAŞLIKLARIN KENDİSİ OLACAK
           "belgedeki_baslik_1": "...", 
           "belgedeki_baslik_2": "...",
           "barkod": "..."
        }
      ]
    }
    """
    return run_llm(system_prompt, raw_text)

def strategy_scattered(raw_text):
    print("   -> Teşhis: SCATTERED. 'Esnek Fermuar' (Flexible Zipper)...")
    
    system_prompt = """
    Sen "Esnek Veri Birleştirme Uzmanı"sın. Metin dağınık (sütun sütun) gelmiş.
    Görevin: Metindeki veri tiplerini tespit et ve BARKODLARI ve İSİMLERİ merkez alarak hizalamak.

    ADIM 1: MEVCUT VERİ TİPLERİNİ HAVUZLA (POOLING)
    Metni tara ve şu listeleri oluştur:
    - [ZORUNLU] **Barkodlar:** (13 haneli sayılar). En güvenilir hizalama aracıdır.
    - [ZORUNLU] **Ürün İsimleri:** (Büyük harfli metin blokları).
    - [ZORUNLU] **Paralar:** (Virgüllü sayılar).
    
    - [OPSİYONEL] **Tarihler:** (Varsa al, yoksa zorlama).
    - [OPSİYONEL] **Miktarlar:** (Küçük tamsayılar).
    - [OPSİYONEL] **Sıra No:** (1, 2, 3... düzenli artanlar).

    ADIM 2: EŞLEŞTİRME (ANCHOR ZIPPING)
    - En güvenilir listen hangisiyse (Barkod veya İsim) onu temel al.
    - 1. İsim + 1. Barkod + 1. Para Grubu'nu eşleştir.
    - Eğer Barkod sayısı ile İsim sayısı tutmuyorsa, hizalamayı Barkodlara göre yap (İsimler bazen bölünür, barkod bölünmez).

    ADIM 3: PARA AYRIŞTIRMA
    - Eğer her ürün için 2 para değeri düşüyorsa: Küçük=`birim_fiyat`, Büyük=`toplam_tutar`.
    - Eğer tek para varsa: `tutar` kabul et.
    - Eğer "Paralar" listesinden hariç, satır sonlarında ayrı bir "Toplam" sütunu varsa onu da al.

    ADIM 4: DİNAMİK BAŞLIKLAR
    - JSON anahtarlarını belgedeki sütun isimlerine göre ver (Örn: `stok_mik`).

    ÇIKTI FORMATI (JSON):
    {
      "metadata": { ... },
      "dip_toplamlar": { ... },
      "urunler": [
        {
          "barkod": "...", 
          "urun_adi": "...",
          "belgeden_gelen_sutunlar...": "..."
        }
      ]
    }
    """
    return run_llm(system_prompt, raw_text)

def process_text_adaptive(raw_text: str):
    """
    Main entry point for Groq Refinement.
    Takes OCR raw text -> Returns Dictionary of products
    """
    if not, raw_text: return None

    # Debug logs can be printed here, but better to return structured data
    # diagnose
    layout_type = diagnose_layout(raw_text)
    
    # Strategy
    json_str = ""
    if layout_type == "SCATTERED":
        json_str = strategy_scattered(raw_text)
    else:
        json_str = strategy_standard(raw_text)
        
    try:
        final_data = json.loads(json_str)
        print(f"✅ GROQ SUCCESS ({layout_type})")
        return final_data
    except json.JSONDecodeError:
        print(f"❌ GROQ JSON ERROR: {json_str[:100]}...")
        return None
