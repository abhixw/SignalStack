import requests
import json
import time

API_URL = "http://localhost:8000"

def run_demo():
    print("🚀 Starting 'Payments API v1' Demo Scenario...")

    # 1. Create Outcome (Exact match to demo.txt)
    print("\n1. Creating Outcome: 'payments-api-v1'...")
    outcome_payload = {
        "id": "payments-api-v1",
        "title": "Build payments API - v1",
        "description": "Deliver a production payments API supporting 50k RPM, idempotent charge creation, and end-to-end tests within 90 days",
        "tasks": [
            {"task_id": "t1", "title": "Schema design", "success_criteria": {"outcome": "Robust schema"}, "importance": "High"},
            {"task_id": "t2", "title": "Rate limiting & middleware", "success_criteria": {"outcome": "Scalable API"}, "importance": "High"},
            {"task_id": "t3", "title": "Deployment & Observability", "success_criteria": {"outcome": "Production ready"}, "importance": "Medium"}
        ],
        "rubric": {"schema_design": 0.4, "rate_limiting": 0.4, "deployment": 0.2}
    }
    
    try:
        # Check if exists first to avoid 400
        res = requests.get(f"{API_URL}/outcomes/payments-api-v1")
        if res.status_code == 200:
            print("   Outcome already exists. Using existing.")
        else:
            res = requests.post(f"{API_URL}/outcomes", json=outcome_payload)
            res.raise_for_status()
            print("   ✅ Outcome Created.")
    except Exception as e:
        print(f"   ❌ Error creating outcome: {e}")
        return

    # 2. Submit Candidate A (Schema Focus)
    # Demo: demo-user/payments-sample (Fake)
    # Real: tiangolo/full-stack-fastapi-template (Has Alembic migrations, Docker, complex schema)
    print("\n2. Submitting Candidate A (Schema Expert)...")
    print("   Using Real Repo: https://github.com/tiangolo/full-stack-fastapi-template")
    proof_a = {
        "job_id": "payments-api-v1",
        "candidate_id": "candidate_a_schema_expert",
        "type": "github",
        "payload": {
            "repo_url": "https://github.com/tiangolo/full-stack-fastapi-template",
            "context": "I built this full-stack template with robust DB migrations."
        }
    }
    try:
        requests.post(f"{API_URL}/proofs", json=proof_a)
        print("   ✅ Candidate A Submitted.")
    except Exception as e:
        print(f"   ❌ Error submitting Candidate A: {e}")

    # 3. Submit Candidate B (Rate Limiting Focus)
    # Demo: another-user/rate-throttle (Fake)
    # Real: long2ice/fastapi-limiter (Real rate limiting library)
    print("\n3. Submitting Candidate B (Middleware Expert)...")
    print("   Using Real Repo: https://github.com/long2ice/fastapi-limiter")
    proof_b = {
        "job_id": "payments-api-v1",
        "candidate_id": "candidate_b_middleware_expert",
        "type": "github",
        "payload": {
            "repo_url": "https://github.com/long2ice/fastapi-limiter",
            "context": "I wrote a high-performance rate limiting library for FastAPI."
        }
    }
    try:
        requests.post(f"{API_URL}/proofs", json=proof_b)
        print("   ✅ Candidate B Submitted.")
    except Exception as e:
        print(f"   ❌ Error submitting Candidate B: {e}")

    # 4. Trigger Evaluation
    print("\n4. Triggering Evaluation (Gemini + GitHub)...")
    print("   (This may take 10-20 seconds to fetch files and generate AI explanations)")
    eval_payload = {
        "request_id": "demo-run-1",
        "outcome": outcome_payload,
        "proofs": [proof_a, proof_b]
    }
    
    try:
        res = requests.post(f"{API_URL}/plugin/evaluate", json=eval_payload)
        res.raise_for_status()
        evaluation = res.json()
        print("   ✅ Evaluation Completed!")
        
        print("\n--- 📊 RESULTS ---")
        print(f"Fit Score: {evaluation['fit_score']}")
        
        for alloc in evaluation['work_allocation']:
            print(f"\nTask: {alloc['task_title']}")
            print(f"  🏆 Winner: {alloc['recommended_candidate']}")
            print(f"  🧠 Reason: {alloc['reasons'][0]}")
            if alloc['evidence']:
                 print(f"  📄 Evidence: {alloc['evidence'][0]['source_url']}")

    except Exception as e:
        print(f"   ❌ Evaluation Failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(e.response.text)
        return

    # 5. Post-Hire Feedback (The Learning Loop)
    print("\n5. Simulating Post-Hire Feedback (Learning Loop)...")
    print("   Scenario: We hired Candidate A, but they struggled with migrations (False Positive).")
    print("   Action: Sending 'failure' feedback to system.")
    
    feedback_payload = {
        "job_id": "payments-api-v1",
        "evaluation_id": "eval-1", # Mock ID, in real app comes from eval response
        "result": "failure",
        "metrics": {"incidents": 2, "migration_issues": 1}
    }
    
    try:
        res = requests.post(f"{API_URL}/plugin/feedback", json=feedback_payload)
        print(f"   ✅ Feedback Recorded: {res.json()}")
    except Exception as e:
        print(f"   ❌ Feedback Failed: {e}")

    # 6. Verify Weight Updates
    print("\n6. Verifying System Learning...")
    try:
        res = requests.get(f"{API_URL}/admin/signal-weights")
        weights = res.json()
        print("   Updated Signal Weights:")
        for w in weights:
            print(f"   - {w['signal_name']}: {w['weight']}")
        print("\n✅ DEMO COMPLETE: The system has 'learned' from this outcome.")
    except Exception as e:
        print(f"   ❌ Failed to fetch weights: {e}")

if __name__ == "__main__":
    run_demo()
