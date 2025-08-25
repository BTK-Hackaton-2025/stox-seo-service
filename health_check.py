#!/usr/bin/env python3
"""
Simple health check script for gRPC server
"""
import grpc
import product_analyzer_pb2_grpc
import sys

def check_health():
    try:
        # Try to connect to the gRPC server
        channel = grpc.insecure_channel('localhost:50071')
        stub = product_analyzer_pb2_grpc.ProductAnalyzerStub(channel)
        
        # Set a short timeout for health check
        channel.close()
        return True
    except Exception:
        return False

if __name__ == "__main__":
    if check_health():
        print("✅ gRPC server is healthy")
        sys.exit(0)
    else:
        print("❌ gRPC server is not responding")
        sys.exit(1)