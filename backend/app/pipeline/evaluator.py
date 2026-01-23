from typing import List, Dict
import app.schemas as schemas
from app.pipeline.matcher import Matcher
from app.pipeline.allocator import Allocator
from app.pipeline.signal_extractor import SignalExtractor

class Evaluator:
    def __init__(self):
        self.matcher = Matcher()
        self.allocator = Allocator()
        self.extractor = SignalExtractor()

    def evaluate(self, outcome: schemas.OutcomeCreate, proofs: List[schemas.ProofCreate], signals_map: Dict[str, Dict]) -> schemas.EvaluationResponse:
        allocations = []
        global_signals_used = set()
        
        for task in outcome.tasks:
            best_candidate = None
            best_score = 0.0
            reasons = []
            evidence = []
            
            # Find best candidate based on signals
            for proof in proofs:
                cand_id = proof.candidate_id
                signals = signals_map.get(cand_id, {})
                
                # Calculate task-specific score
                score = self.matcher.calculate_task_score(task.title, signals)
                
                # Track which signals we used
                for signal_name in self.matcher._get_task_signals(task.title):
                    global_signals_used.add(signal_name)
                
                if score > best_score:
                    best_score = score
                    best_candidate = cand_id
            
            # Generate reasons based on matched signals
            if best_candidate and best_candidate in signals_map:
                candidate_signals = signals_map[best_candidate]
                reasons = self.matcher.get_matched_reason(task.title, candidate_signals)
                
                # Extract evidence (Re-using extractor for evidence specifically)
                # Ideally proof should contain repo_url
                # We need to find the proof object for the best candidate
                best_proof = next((p for p in proofs if p.candidate_id == best_candidate), None)
                if best_proof:
                     repo_url = best_proof.payload.get("repo_url", "")
                     if repo_url:
                        evidence = self.extractor.extract_evidence(repo_url, task.title)

            allocations.append(self.allocator.create_allocation(
                task, best_candidate, best_score, reasons, evidence
            ))

        # Calculate overall fit score
        avg_confidence = 0.0
        if allocations:
            avg_confidence = sum(a.confidence for a in allocations) / len(allocations)

        return schemas.EvaluationResponse(
            job_id=outcome.id,
            fit_score=round(avg_confidence, 2),
            work_allocation=allocations,
            global_signals_used=list(global_signals_used),
            risk_flags=[],
            human_action_required=True
        )
