# Product Image Analyzer

Google Gemini 2.0 Flash modelini kullanarak ürün görsellerinden otomatik olarak başlık ve açıklama oluşturan Python mikroservis.

## Özellikler

- **Google Gemini 2.0 Flash** ile görsel analizi
- **FastAPI** ile RESTful API
- **Multipart/form-data** ile resim yükleme
- **SEO uyumlu** başlık ve açıklama üretimi
- **Docker** desteği
- **Kapsamlı hata yönetimi**

## Kurulum

### 1. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

### 2. Çevre Değişkenlerini Ayarla

`.env` dosyasını düzenleyin ve Google API anahtarınızı ekleyin:

```env
GOOGLE_API_KEY=your_actual_google_api_key_here
```

**Google API Anahtarı Alma:**
1. [Google AI Studio](https://aistudio.google.com/) adresine gidin
2. "Get API Key" butonuna tıklayın
3. Yeni bir API anahtarı oluşturun
4. Anahtarı `.env` dosyasına ekleyin

### 3. Uygulamayı Başlat

```bash
python main.py
```

Alternatif olarak:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Kullanımı

### Sağlık Kontrolü
```bash
GET http://localhost:8000/
```

### Görsel Analizi
```bash
POST http://localhost:8000/generate-from-image
Content-Type: multipart/form-data

# Form alanı: image (dosya)
```

**cURL Örneği:**
```bash
curl -X POST "http://localhost:8000/generate-from-image" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "image=@product_image.jpg"
```

**Yanıt Formatı:**
```json
{
  "title": "Şık Kahverengi Deri Çanta - Premium Kalite",
  "description": "Yüksek kaliteli hakiki deriden üretilen bu şık kahverengi çanta, hem günlük hem de iş hayatında kullanım için idealdir. Geniş iç hacmi sayesinde tüm ihtiyaçlarınızı rahatça taşıyabilirsiniz. Dayanıklı fermuarı ve ergonomik sapları ile uzun yıllar kullanabileceğiniz bu çanta, stilinizi tamamlayan mükemmel bir aksesuar..."
}
```

## Test

Test scriptini çalıştırın:
```bash
python test_api.py
```

## Docker ile Çalıştırma

### Docker Build
```bash
docker build -t product-analyzer .
```

### Docker Run
```bash
docker run -p 8000:8000 --env-file .env product-analyzer
```

### Docker Compose
```bash
docker-compose up -d
```

## Desteklenen Formatlar

- **Resim Formatları:** JPEG, JPG, PNG, GIF, BMP, WEBP
- **Maksimum Dosya Boyutu:** 10MB
- **Çıktı:** JSON formatında başlık ve açıklama

## API Dokümantasyonu

Uygulama çalışırken otomatik dokümantasyon:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Hata Kodları

- **400:** Geçersiz resim formatı veya boyutu
- **500:** Gemini API hatası veya sunucu hatası

## Proje Yapısı

```
service/
├── main.py              # Ana uygulama
├── requirements.txt     # Python bağımlılıkları
├── .env                # Çevre değişkenleri
├── test_api.py         # Test scripti
├── Dockerfile          # Docker konfigürasyonu
├── docker-compose.yml  # Docker Compose konfigürasyonu
└── README.md           # Bu dosya
```

## Node.js Entegrasyonu

Node.js backend'inizden bu mikroservisi çağırmak için:

```javascript
const FormData = require('form-data');
const fs = require('fs');

async function analyzeProductImage(imagePath) {
  const form = new FormData();
  form.append('image', fs.createReadStream(imagePath));

  const response = await fetch('http://localhost:8000/generate-from-image', {
    method: 'POST',
    body: form
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Kullanım
analyzeProductImage('./product.jpg')
  .then(result => {
    console.log('Başlık:', result.title);
    console.log('Açıklama:', result.description);
  })
  .catch(error => {
    console.error('Hata:', error);
  });
```

## Güvenlik

- **CORS:** Tüm originlere açık (üretimde spesifik domainleri belirtin)
- **Dosya Validasyonu:** Sadece resim dosyaları kabul edilir
- **Boyut Sınırı:** Maksimum 10MB dosya boyutu
- **API Anahtarı:** Çevre değişkeni olarak saklanır

## Performans

- **Gemini 2.0 Flash:** Hızlı ve kaliteli görsel analizi
- **Async/Await:** Non-blocking I/O işlemleri
- **Memory Efficient:** PIL ile optimize edilmiş resim işleme

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır.
