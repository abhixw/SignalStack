import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(name, url, method="GET", data=None):
    print(f"\n{'='*50}")
    print(f"=== {name} ===")
    print(f"URL: {url}")
    try:
        if method == "GET":
            r = requests.get(url, timeout=10)
        else:
            r = requests.post(url, json=data, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"Response: {json.dumps(data, indent=2)[:1500]}")
            except:
                print(f"Response: {r.text[:500]}")
        else:
            print(f"Error: {r.text[:500]}")
    except Exception as e:
        print(f"ERROR: {e}")

# 1. Reviewer Queue (List all evaluations)
test_endpoint("REVIEWER QUEUE", f"{BASE_URL}/evaluations")

# 2. Get outcomes to find job_id
print("\n" + "="*50)
print("=== OUTCOMES LIST ===")
try:
    r = requests.get(f"{BASE_URL}/outcomes", timeout=10)
    outcomes = r.json()
    print(f"Found {len(outcomes)} outcomes")
    if outcomes:
        job_id = outcomes[0].get('id')
        print(f"First outcome ID: {job_id}")
        
        # 3. Get specific evaluation
        test_endpoint("EVALUATION DETAILS", f"{BASE_URL}/evaluations/{job_id}")
except Exception as e:
    print(f"ERROR: {e}")

# 4. System Learning / Feedback
test_endpoint("SYSTEM LEARNING (Feedback)", f"{BASE_URL}/feedback")

# 5. Audit Logs
test_endpoint("AUDIT LOGS", f"{BASE_URL}/audit-logs")

print("\n" + "="*50)
print("=== VERIFICATION COMPLETE ===")
