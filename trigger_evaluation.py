import requests
import json

API_URL = "http://localhost:8000"
OUTCOME_ID = "payments-api-v1"

def trigger_manual_evaluation():
    print(f"🚀 Triggering Manual Evaluation for '{OUTCOME_ID}'...")

    try:
        # 1. Fetch Outcome
        print("   Fetching Outcome data...")
        outcome_res = requests.get(f"{API_URL}/outcomes/{OUTCOME_ID}")
        if outcome_res.status_code != 200:
            print(f"   ❌ Outcome '{OUTCOME_ID}' not found. Please create it in the UI first.")
            return
        outcome = outcome_res.json()

        # 2. Fetch Proofs
        print("   Fetching Submitted Proofs...")
        proofs_res = requests.get(f"{API_URL}/proofs/{OUTCOME_ID}")
        proofs = proofs_res.json()
        
        if not proofs:
            print("   ⚠️ No proofs found. Please submit candidates in the UI first.")
            return
        
        print(f"   Found {len(proofs)} proofs.")

        # 3. Trigger Evaluation
        print("   Requesting AI Evaluation (this may take 10-20 seconds)...")
        payload = {
            "request_id": f"manual-{int(requests.get(f'{API_URL}/health').elapsed.total_seconds())}", # Random-ish ID
            "outcome": outcome,
            "proofs": proofs
        }
        
        eval_res = requests.post(f"{API_URL}/plugin/evaluate", json=payload)
        eval_res.raise_for_status()
        result = eval_res.json()
        
        print("   ✅ Evaluation Completed Successfully!")
        print(f"   Job ID: {result['job_id']}")
        print("   👉 Go to 'Review Queue' in the UI to see the results.")

    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    trigger_manual_evaluation()
