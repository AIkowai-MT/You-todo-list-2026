import requests
import json
import traceback

BASE_URL = "http://localhost:8000"

def test_google_tasks_endpoints():
    print("Testing Google Tasks endpoints...")
    try:
        # 1. 接続ステータス確認
        response = requests.get(f"{BASE_URL}/api/google/status")
        print(f"Status Check: {response.status_code}, Res: {response.text}")
        
        # 2. 認証なしでのアクセス（401期待）
        # ただしセッションに残っている可能性もあるので、挙動を確認
        response = requests.get(f"{BASE_URL}/api/google/tasklists")
        print(f"Tasklist Check: {response.status_code}")
        if response.status_code in [200, 401]:
             print("PASSED: Tasklist endpoint matches expected behavior (200 or 401)")
        else:
             print(f"FAILED: Unexpected status code {response.status_code}")

    except Exception as e:
        print(f"Google Tasks Test Failed: {e}")

def test_error_handling():
    print("\nTesting Error Handling (Invalid URL)...")
    try:
        payload = {"urls": ["https://invalid-url.com/aaa"]}
        response = requests.post(f"{BASE_URL}/api/analyze", json=payload)
        print(f"Invalid URL Status: {response.status_code}")
        # bodyがJSONであることを確認
        try:
            data = response.json()
            if "error" in data:
                print(f"PASSED: Error response is valid JSON. Msg: {data['error']}")
            else:
                print("FAILED: Response JSON does not contain 'error' field.")
        except:
             print("FAILED: Response is not valid JSON")
             print(response.text)
    except Exception as e:
        print(f"Error Handling Test Failed: {e}")

if __name__ == "__main__":
    test_google_tasks_endpoints()
    test_error_handling()
