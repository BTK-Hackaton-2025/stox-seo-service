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
import requests
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
        # Parse the response using the improved parsing logic
        title, description = self._parse_gemini_response(response_text, context)
        return product_image_analyzer_pb2.ImageResponse(title=title, description=description)

    def GenerateFromImageUrl(self, request, context):
        """Generate product information from image URL"""
        image_url = request.image_url
        
        if not image_url:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Image URL is required")
        
        try:
            # Download image from URL
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Check if response is actually an image
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"URL does not point to an image. Content-Type: {content_type}")
            
            image_bytes = response.content
            
            # Check file size
            if len(image_bytes) > 10 * 1024 * 1024:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Image file is too large. Maximum 10MB supported.")
            
            # Validate image can be processed
            try:
                pil_image = Image.open(io.BytesIO(image_bytes))
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
            except Exception as e:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Error processing image: {str(e)}")
            
        except requests.RequestException as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Error downloading image from URL: {str(e)}")
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Unexpected error: {str(e)}")
        
        # Use the same AI processing logic as the file upload method
        prompt = create_prompt()
        client = genai.Client(api_key=GOOGLE_API_KEY)
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=content_type
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
            context.abort(grpc.StatusCode.INTERNAL, f"Gemini API error: {str(e)}")
        
        # Parse the response with improved error handling
        title, description = self._parse_gemini_response(response_text, context)
        return product_image_analyzer_pb2.ImageResponse(title=title, description=description)
    
    def _parse_gemini_response(self, response_text, context):
        """Parse Gemini API response and extract title and description"""
        import json
        import re
        
        # First, try to find JSON in the response
        json_pattern = r'\{.*?"title".*?"description".*?\}'
        json_matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        for json_match in json_matches:
            try:
                result = json.loads(json_match)
                title = result.get("title", "").strip()
                description = result.get("description", "").strip()
                if title and description:
                    return title, description
            except json.JSONDecodeError:
                continue
        
        # If JSON parsing fails, try manual extraction with improved regex
        title_patterns = [
            r'"title"\s*:\s*"([^"]+)"',
            r'"title"\s*:\s*\'([^\']+)\'',
            r'title:\s*"([^"]+)"',
            r'title:\s*\'([^\']+)\'',
        ]
        
        description_patterns = [
            r'"description"\s*:\s*"([^"]+)"',
            r'"description"\s*:\s*\'([^\']+)\'', 
            r'description:\s*"([^"]+)"',
            r'description:\s*\'([^\']+)\'',
        ]
        
        title = ""
        description = ""
        
        for pattern in title_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                break
                
        for pattern in description_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if match:
                description = match.group(1).strip()
                break
        
        # If still no results, try even simpler line-by-line parsing
        if not title or not description:
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if not title and any(keyword in line.lower() for keyword in ['title', 'başlık']):
                    # Extract anything that looks like a title
                    colon_split = line.split(':', 1)
                    if len(colon_split) > 1:
                        title = colon_split[1].strip().strip('",\'')
                elif not description and any(keyword in line.lower() for keyword in ['description', 'açıklama']):
                    # Extract anything that looks like a description  
                    colon_split = line.split(':', 1)
                    if len(colon_split) > 1:
                        description = colon_split[1].strip().strip('",\'')
        
        # Final fallback - if we still don't have both, provide debug info
        if not title or not description:
            # Log the actual response for debugging (truncated)
            debug_response = response_text[:500] + "..." if len(response_text) > 500 else response_text
            context.abort(grpc.StatusCode.INTERNAL, 
                         f"Could not parse Gemini response. Found title: {'Yes' if title else 'No'}, "
                         f"Found description: {'Yes' if description else 'No'}. "
                         f"Response preview: {debug_response}")
        
        return title, description

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