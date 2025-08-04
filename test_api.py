import requests
import json
import os

def test_health_check():
    """API sağlık kontrolü testi"""
    try:
        response = requests.get("http://localhost:8000/")
        print("Sağlık Kontrolü:")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        print("-" * 50)
        return response.status_code == 200
    except Exception as e:
        print(f"Sağlık kontrolü hatası: {e}")
        return False

def test_image_analysis(image_path):
    """Görsel analizi testi"""
    if not os.path.exists(image_path):
        print(f"Test resmi bulunamadı: {image_path}")
        return False
    
    try:
        url = "http://localhost:8000/generate-from-image"
        
        with open(image_path, 'rb') as image_file:
            files = {'image': ('test_image.jpg', image_file, 'image/jpeg')}
            
            print(f"Test resmi gönderiliyor: {image_path}")
            response = requests.post(url, files=files)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("Başarılı Analiz:")
                print(f"Başlık: {result.get('title', 'N/A')}")
                print(f"Açıklama: {result.get('description', 'N/A')}")
                print("-" * 50)
                return True
            else:
                print(f"Hata: {response.text}")
                return False
                
    except Exception as e:
        print(f"Test hatası: {e}")
        return False

def main():
    """Ana test fonksiyonu"""
    print("=== Product Image Analyzer API Test ===\n")
    
    # Sağlık kontrolü
    if not test_health_check():
        print("API çalışmıyor. Önce servisi başlatın: python main.py")
        return
    
    # Resim analizi testi
    print("Görsel analizi için test resmi yolu girin (boş bırakırsanız test atlanır):")
    image_path = input("Resim yolu: ").strip()
    
    if image_path and os.path.exists(image_path):
        test_image_analysis(image_path)
    else:
        print("Test resmi belirtilmedi veya bulunamadı.")
        print("\nManuel test için:")
        print("curl -X POST \"http://localhost:8000/generate-from-image\" \\")
        print("     -H \"accept: application/json\" \\")
        print("     -H \"Content-Type: multipart/form-data\" \\")
        print("     -F \"image=@your_image.jpg\"")

if __name__ == "__main__":
    main()
