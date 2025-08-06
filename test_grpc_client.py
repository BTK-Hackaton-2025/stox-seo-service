import grpc
import product_image_analyzer_pb2
import product_image_analyzer_pb2_grpc
import mimetypes
import sys
import argparse

def test_image_file(stub, image_path):
    """Test the GenerateFromImage endpoint with a local image file"""
    print(f"\n=== Testing GenerateFromImage with file: {image_path} ===")
    
    # Dosya adından content_type bul
    content_type, _ = mimetypes.guess_type(image_path)
    if not content_type:
        content_type = "image/jpeg"  # varsayılan
    filename = image_path.split("/")[-1]
    
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        request = product_image_analyzer_pb2.ImageRequest(
            image=image_bytes,
            filename=filename,
            content_type=content_type
        )
        
        response = stub.GenerateFromImage(request)
        print("✅ Success!")
        print("Başlık:", response.title)
        print("Açıklama:", response.description)
        
    except FileNotFoundError:
        print(f"❌ Error: File '{image_path}' not found")
    except grpc.RpcError as e:
        print(f"❌ gRPC Error: {e.code()} - {e.details()}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_image_url(stub, image_url):
    """Test the GenerateFromImageUrl endpoint with an image URL"""
    print(f"\n=== Testing GenerateFromImageUrl with URL: {image_url} ===")
    
    try:
        request = product_image_analyzer_pb2.ImageUrlRequest(
            image_url=image_url
        )
        
        response = stub.GenerateFromImageUrl(request)
        print("✅ Success!")
        print("Başlık:", response.title)
        print("Açıklama:", response.description)
        
    except grpc.RpcError as e:
        print(f"❌ gRPC Error: {e.code()} - {e.details()}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    parser = argparse.ArgumentParser(description='Test ProductImageAnalyzer gRPC service')
    parser.add_argument('--file', '-f', help='Path to local image file')
    parser.add_argument('--url', '-u', help='URL to image')
    parser.add_argument('--host', default='localhost', help='gRPC server host (default: localhost)')
    parser.add_argument('--port', type=int, default=50071, help='gRPC server port (default: 50071)')
    
    args = parser.parse_args()
    
    if not args.file and not args.url:
        print("❌ Error: Please provide either --file or --url (or both)")
        print("\nExamples:")
        print("  python test_grpc_client.py --file image.jpg")
        print("  python test_grpc_client.py --url https://example.com/image.jpg")
        print("  python test_grpc_client.py --file image.jpg --url https://example.com/image.jpg")
        sys.exit(1)
    
    # Connect to gRPC server
    channel = grpc.insecure_channel(f"{args.host}:{args.port}")
    stub = product_image_analyzer_pb2_grpc.ProductImageAnalyzerStub(channel)
    
    print(f"🔗 Connecting to gRPC server at {args.host}:{args.port}")
    
    # Test file endpoint if provided
    if args.file:
        test_image_file(stub, args.file)
    
    # Test URL endpoint if provided
    if args.url:
        test_image_url(stub, args.url)
    
    print("\n✨ Test completed!")

if __name__ == "__main__":
    main()