import requests
import json
import os
import sys

BASE_URL = "http://localhost:8000"

def test_analyze_endpoint():
    print("Testing /api/analyze endpoint...")
    
    # 1. 無効なURLでのテスト
    try:
        payload = {"urls": ["https://invalid-url.com/aaa"]}
        response = requests.post(f"{BASE_URL}/api/analyze", json=payload)
        print(f"Invalid URL Test: Status Code {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code != 500 and response.status_code != 400: # 500 or 400 expected for execution error
             print("Warning: Unexpected status code for invalid URL")
    except Exception as e:
        print(f"Invalid URL Test Failed: {e}")

    # 2. 正常系テスト（短めの動画推奨だが、実際の解析は時間がかかるのでタイムアウト注意）
    # APIキーが設定されていないと失敗するので、環境変数チェック
    if not os.environ.get("GEMINI_API_KEY"):
        print("Skipping valid URL test because GEMINI_API_KEY is not set locally for the client script (server might have it).")
        return

    # ここではサーバーが起動している前提。
    print("Testing with a sample video...")
    try:
        # 短いテスト動画: "YouTube Developers" チャンネルのイントロなど
        payload = {"urls": ["https://www.youtube.com/watch?v=S30R3i26Xh4"]} 
        response = requests.post(f"{BASE_URL}/api/analyze", json=payload, timeout=60)
        print(f"Valid URL Test: Status Code {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if "tasks" in data and "summary" in data:
                print("Valid URL Test PASSED: Tasks and Summary found.")
            else:
                print("Valid URL Test FAILED: 'tasks' or 'summary' missing in response.")
        else:
            print(f"Valid URL Test FAILED: {response.text}")
    except Exception as e:
        print(f"Valid URL Test Failed (Server might be down): {e}")

def test_google_tasks_endpoints():
    print("\nTesting Google Tasks endpoints...")
    # 認証していない状態でのテスト
    try:
        response = requests.get(f"{BASE_URL}/api/google/status")
        print(f"Status Check: {response.status_code}, {response.json()}")
        
        response = requests.get(f"{BASE_URL}/api/google/tasklists")
        print(f"Tasklist Check (Unauth): {response.status_code}") # Should be 401
        
    except Exception as e:
        print(f"Google Tasks Test Failed: {e}")

if __name__ == "__main__":
    test_analyze_endpoint()
    test_google_tasks_endpoints()
