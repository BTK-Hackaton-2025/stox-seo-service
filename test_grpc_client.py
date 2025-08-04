import grpc
import product_image_analyzer_pb2
import product_image_analyzer_pb2_grpc
import mimetypes
import sys

# Kullanım: python test_grpc_client.py <image_path>
def main(image_path):
    # Dosya adından content_type bul
    content_type, _ = mimetypes.guess_type(image_path)
    if not content_type:
        content_type = "image/jpeg"  # varsayılan
    filename = image_path.split("/")[-1]
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    channel = grpc.insecure_channel("localhost:50051")
    stub = product_image_analyzer_pb2_grpc.ProductImageAnalyzerStub(channel)
    request = product_image_analyzer_pb2.ImageRequest(
        image=image_bytes,
        filename=filename,
        content_type=content_type
    )
    try:
        response = stub.GenerateFromImage(request)
        print("Başlık:", response.title)
        print("Açıklama:", response.description)
    except grpc.RpcError as e:
        print(f"Hata: {e.code()} - {e.details()}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Kullanım: python test_grpc_client.py <gorsel_dosyasi>")
        sys.exit(1)
    main(sys.argv[1])