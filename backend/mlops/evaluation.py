"""
RAG evaluation using Ragas for assessing retrieval and generation quality.
"""

import os
from typing import List, Dict, Optional
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from datasets import Dataset
from dotenv import load_dotenv

load_dotenv()


class RAGEvaluator:
    """Ragas integration for RAG evaluation."""
    
    def __init__(self):
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ]
    
    def evaluate_query(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> Dict:
        """
        Evaluate a single query-answer pair.
        
        Args:
            question: User question
            answer: Generated answer
            contexts: Retrieved context passages
            ground_truth: Optional ground truth answer (for manual evaluation)
            
        Returns:
            Dict: Evaluation scores
        """
        # Prepare dataset
        data = {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts],
        }
        
        if ground_truth:
            data["ground_truth"] = [ground_truth]
        
        dataset = Dataset.from_dict(data)
        
        # Run evaluation
        result = evaluate(
            dataset=dataset,
            metrics=self.metrics
        )
        
        # Extract scores
        scores = result.to_dict()
        
        return {
            "faithfulness": scores.get("faithfulness", 0.0),
            "answer_relevancy": scores.get("answer_relevancy", 0.0),
            "context_precision": scores.get("context_precision", 0.0),
            "context_recall": scores.get("context_recall", 0.0),
            "overall_score": sum(scores.values()) / len(scores) if scores else 0.0
        }
    
    def evaluate_batch(
        self,
        queries: List[Dict]
    ) -> Dict:
        """
        Evaluate a batch of queries.
        
        Args:
            queries: List of dicts with 'question', 'answer', 'contexts', optional 'ground_truth'
            
        Returns:
            Dict: Aggregate evaluation scores
        """
        if not queries:
            return {}
        
        # Prepare dataset
        data = {
            "question": [q["question"] for q in queries],
            "answer": [q["answer"] for q in queries],
            "contexts": [q["contexts"] for q in queries],
        }
        
        if all("ground_truth" in q for q in queries):
            data["ground_truth"] = [q.get("ground_truth", "") for q in queries]
        
        dataset = Dataset.from_dict(data)
        
        # Run evaluation
        result = evaluate(
            dataset=dataset,
            metrics=self.metrics
        )
        
        # Extract aggregate scores
        scores = result.to_dict()
        
        return {
            "average_faithfulness": scores.get("faithfulness", 0.0),
            "average_answer_relevancy": scores.get("answer_relevancy", 0.0),
            "average_context_precision": scores.get("context_precision", 0.0),
            "average_context_recall": scores.get("context_recall", 0.0),
            "overall_score": sum(scores.values()) / len(scores) if scores else 0.0,
            "sample_size": len(queries)
        }


def get_evaluator() -> RAGEvaluator:
    """Get or create RAG evaluator instance."""
    return RAGEvaluator()

