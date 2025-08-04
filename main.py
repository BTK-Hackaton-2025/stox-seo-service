from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import io
from PIL import Image
import uvicorn
from typing import Dict
import base64

# .env dosyasından çevre değişkenlerini yükle
load_dotenv()

app = FastAPI(
    title="Product Image Analyzer",
    description="Google Gemini 2.0 Flash kullanarak ürün görseli analizi yapan mikroservis",
    version="1.0.0"
)

# CORS middleware ekle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Üretimde spesifik domainleri belirtin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Gemini API'yi yapılandır
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY çevre değişkeni ayarlanmamış")

# Desteklenen resim formatları
SUPPORTED_FORMATS = {"jpeg", "jpg", "png", "gif", "bmp", "webp"}

def validate_image(file: UploadFile) -> bool:
    """Resim dosyasının geçerli olup olmadığını kontrol et"""
    if not file.content_type or not file.content_type.startswith("image/"):
        return False
    
    # Dosya uzantısını kontrol et
    if file.filename:
        extension = file.filename.lower().split(".")[-1]
        return extension in SUPPORTED_FORMATS
    
    return False

def create_prompt() -> str:
    """Gemini için ürün analizi prompt'u oluştur"""
    return """
Bu görseldeki ürünü analiz et ve şu adımları takip et:

1. Önce görseldeki ürünü tanımla
2. Bu ürün hakkında güncel pazar bilgilerini aramak için web araması yap
3. Benzer ürünlerin fiyat aralıklarını ve özelliklerini araştır
4. Elde ettiğin bilgileri kullanarak aşağıdaki JSON formatında yanıt ver:

{
    "title": "SEO uyumlu ürün başlığı (max 60 karakter)",
    "description": "Detaylı ürün açıklaması (150-300 kelime)",
    "search_info": "Web aramasından elde edilen bilgiler"
}

Açıklama yazarken:
- Ürünün görsel özelliklerini detaylandır
- Web aramasından öğrendiğin güncel bilgileri kullan
- Kullanım alanlarını ve hedef kitleyi belirt
- SEO dostu anahtar kelimeler kullan
- Profesyonel ve satışa yönelik bir dil kullan

ÖNEMLİ: Mutlaka web araması yap ve bu bilgileri yanıtında kullan.
"""

@app.get("/")
async def root():
    """Sağlık kontrolü endpoint'i"""
    return {"message": "Product Image Analyzer API çalışıyor", "status": "healthy"}

@app.post("/generate-from-image")
async def generate_from_image(image: UploadFile = File(...)) -> Dict[str, str]:
    """
    Yüklenen görsel dosyasından ürün başlığı ve açıklaması oluştur
    """
    try:
        # Resim dosyasını doğrula
        if not validate_image(image):
            raise HTTPException(
                status_code=400, 
                detail="Geçersiz resim formatı. Desteklenen formatlar: JPEG, JPG, PNG, GIF, BMP, WEBP"
            )
        
        # Resim dosyasını oku
        image_bytes = await image.read()
        
        # Resim boyutunu kontrol et (maksimum 10MB)
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Resim dosyası çok büyük. Maksimum 10MB desteklenir."
            )
        
        # PIL ile resmi doğrula ve işle
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            # Resmi RGB formatına çevir (RGBA veya diğer formatlar için)
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Resim dosyası işlenirken hata: {str(e)}"
            )
        
        # Prompt oluştur
        prompt = create_prompt()
        
        # Resmi base64'e çevir
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Google Gemini API ile içerik üretimi
        client = genai.Client(
            api_key=GOOGLE_API_KEY,
        )
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg"
                    ),
                ],
            ),
        ]
        
        tools = [
            types.Tool(googleSearch=types.GoogleSearch(
            )),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            tools=tools,
        )
        
        response_text = ""
        try:
            for chunk in client.models.generate_content_stream(
                model="gemini-2.0-flash-exp",
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.text:
                    response_text += chunk.text
        except Exception as stream_error:
            # Streaming başarısız olursa normal generate_content dene
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=contents,
                config=generate_content_config,
            )
            response_text = response.text
            
        response_text = response_text.strip()
            
        # Yanıtı işle
        import json
        try:
            result = json.loads(response_text)
            
            # Gerekli alanların varlığını kontrol et
            if "title" not in result or "description" not in result:
                raise ValueError("Yanıt gerekli alanları içermiyor")
            
            # Başlık uzunluğunu kontrol et
            if len(result["title"]) > 100:
                result["title"] = result["title"][:97] + "..."
            
            return {
                "title": result["title"],
                "description": result["description"]
            }
            
        except json.JSONDecodeError:
            # JSON parse edilemezse, metni elle ayrıştırmaya çalış
            lines = response_text.split('\n')
            title = ""
            description = ""
            
            for line in lines:
                if '"title"' in line and ':' in line:
                    title = line.split(':', 1)[1].strip().strip('",')
                elif '"description"' in line and ':' in line:
                    description = line.split(':', 1)[1].strip().strip('",')
            
            if not title or not description:
                raise HTTPException(
                    status_code=500,
                    detail="Gemini yanıtı beklenmedik formatta"
                )
            
            return {
                "title": title,
                "description": description
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini API hatası: {str(e)}"
        )
    
    except Exception as e:
        # Beklenmeyen hatalar
        raise HTTPException(
            status_code=500,
            detail=f"Sunucu hatası: {str(e)}"
        )

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
