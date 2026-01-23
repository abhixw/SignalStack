import requests
import json
import time

API_URL = "http://localhost:8000"

def run_platform_demo():
    print("🚀 Starting 'Platform Engineer' Demo Scenario...")

    # 1. Create Outcome: Platform Modernization
    print("\n1. Creating Outcome: 'platform-lead-v1'...")
    outcome_payload = {
        "id": "platform-lead-v1",
        "title": "Lead Platform Engineer",
        "description": "Modernize our infrastructure with containerization, robust CI/CD, and scalable database practices.",
        "tasks": [
            {"task_id": "t1", "title": "Containerization Strategy", "success_criteria": {"outcome": "Fully dockerized services"}, "importance": "High"},
            {"task_id": "t2", "title": "Database Reliability", "success_criteria": {"outcome": "Zero-downtime migrations"}, "importance": "High"},
            {"task_id": "t3", "title": "CI/CD Automation", "success_criteria": {"outcome": "Fast build pipelines"}, "importance": "Medium"}
        ],
        "rubric": {"containerization": 0.4, "database": 0.4, "automation": 0.2}
    }
    
    try:
        # Check if exists
        res = requests.get(f"{API_URL}/outcomes/platform-lead-v1")
        if res.status_code == 200:
            print("   Outcome already exists. Using existing.")
        else:
            res = requests.post(f"{API_URL}/outcomes", json=outcome_payload)
            res.raise_for_status()
            print("   ✅ Outcome Created.")
    except Exception as e:
        print(f"   ❌ Error creating outcome: {e}")
        return

    # 2. Submit Candidate A (The Docker Expert)
    # Repo: docker/awesome-compose (Pure Docker examples)
    print("\n2. Submitting Candidate A (Docker Expert)...")
    print("   Using Real Repo: https://github.com/docker/awesome-compose")
    proof_a = {
        "job_id": "platform-lead-v1",
        "candidate_id": "alice_docker_guru",
        "type": "github",
        "payload": {
            "repo_url": "https://github.com/docker/awesome-compose",
            "context": "I maintain the official Docker compose examples."
        }
    }
    try:
        requests.post(f"{API_URL}/proofs", json=proof_a)
        print("   ✅ Candidate A Submitted.")
    except Exception as e:
        print(f"   ❌ Error submitting Candidate A: {e}")

    # 3. Submit Candidate B (The Database Expert)
    # Repo: django/django (Famous for its ORM and Migration system)
    print("\n3. Submitting Candidate B (Database Expert)...")
    print("   Using Real Repo: https://github.com/django/django")
    proof_b = {
        "job_id": "platform-lead-v1",
        "candidate_id": "bob_db_architect",
        "type": "github",
        "payload": {
            "repo_url": "https://github.com/django/django",
            "context": "I contribute to the Django ORM and migration framework."
        }
    }
    try:
        requests.post(f"{API_URL}/proofs", json=proof_b)
        print("   ✅ Candidate B Submitted.")
    except Exception as e:
        print(f"   ❌ Error submitting Candidate B: {e}")

    # 4. Trigger Evaluation
    print("\n4. Triggering Evaluation...")
    print("   (Scanning huge repos like Django might take a moment...)")
    eval_payload = {
        "request_id": "demo-platform-1",
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

if __name__ == "__main__":
    run_platform_demo()
