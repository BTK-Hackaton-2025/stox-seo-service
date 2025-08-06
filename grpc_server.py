import grpc
from concurrent import futures
import product_image_analyzer_pb2
import product_image_analyzer_pb2_grpc
import os
import base64
from google import genai
from google.genai import types
from PIL import Image
import io
from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SUPPORTED_FORMATS = {"jpeg", "jpg", "png", "gif", "bmp", "webp"}

# Görsel doğrulama fonksiyonu
def validate_image(filename, content_type):
    if not content_type or not content_type.startswith("image/"):
        return False
    if filename:
        extension = filename.lower().split(".")[-1]
        return extension in SUPPORTED_FORMATS
    return False

def create_prompt():
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

class ProductImageAnalyzerServicer(product_image_analyzer_pb2_grpc.ProductImageAnalyzerServicer):
    def GenerateFromImage(self, request, context):
        # Görsel doğrulama
        if not validate_image(request.filename, request.content_type):
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Geçersiz resim formatı.")
        image_bytes = request.image
        if len(image_bytes) > 10 * 1024 * 1024:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Resim dosyası çok büyük. Maksimum 10MB desteklenir.")
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
        except Exception as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Resim dosyası işlenirken hata: {str(e)}")
        prompt = create_prompt()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        client = genai.Client(api_key=GOOGLE_API_KEY)
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=request.content_type
                    ),
                ],
            ),
        ]
        tools = [types.Tool(googleSearch=types.GoogleSearch())]
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=-1),
            tools=tools,
        )
        response_text = ""
        try:
            for chunk in client.models.generate_content_stream(
                model="gemini-2.5-pro",
                contents=contents,
                config=generate_content_config,
            ):
                response_text += chunk.text
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Gemini API hatası: {str(e)}")
        import json
        try:
            result = json.loads(response_text)
            title = result.get("title", "")
            description = result.get("description", "")
        except Exception:
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
            context.abort(grpc.StatusCode.INTERNAL, "Gemini yanıtı beklenmedik formatta")
        return product_image_analyzer_pb2.ImageResponse(title=title, description=description)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    product_image_analyzer_pb2_grpc.add_ProductImageAnalyzerServicer_to_server(
        ProductImageAnalyzerServicer(), server)
    server.add_insecure_port('[::]:50071')
    print("gRPC sunucusu başlatıldı. Port: 50071")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()