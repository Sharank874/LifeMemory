"""
MLOps tracking with MLflow for prompt and retrieval versioning.
"""

import os
from typing import Dict, Optional, List
import mlflow
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv

load_dotenv()


class MLflowTracker:
    """MLflow integration for tracking prompts, retrievals, and evaluations."""
    
    def __init__(self):
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "life-memory-ai")
        
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        
        self.client = MlflowClient()
    
    def log_retrieval(
        self,
        user_id: str,
        query: str,
        retrieved_count: int,
        retrieval_params: Dict,
        run_id: Optional[str] = None
    ):
        """
        Log retrieval operation.
        
        Args:
            user_id: User ID (hashed for privacy)
            query: User query
            retrieved_count: Number of entries retrieved
            retrieval_params: Retrieval parameters (limit, filters, etc.)
            run_id: Optional run ID to associate with
        """
        import hashlib
        hashed_user_id = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        
        with mlflow.start_run(run_id=run_id, nested=True) if run_id else mlflow.start_run(nested=True):
            mlflow.log_param("user_id_hash", hashed_user_id)
            mlflow.log_param("query_length", len(query))
            mlflow.log_param("retrieved_count", retrieved_count)
            mlflow.log_params(retrieval_params)
            mlflow.log_metric("retrieval_success", 1 if retrieved_count > 0 else 0)
    
    def log_prompt_version(
        self,
        prompt_type: str,
        prompt_text: str,
        model: str,
        temperature: float
    ) -> str:
        """
        Log prompt version for tracking.
        
        Args:
            prompt_type: Type of prompt (e.g., "intent_classifier", "reflection_synthesizer")
            prompt_text: Prompt content
            model: LLM model used
            temperature: Temperature setting
            
        Returns:
            str: Run ID
        """
        with mlflow.start_run() as run:
            mlflow.log_param("prompt_type", prompt_type)
            mlflow.log_param("model", model)
            mlflow.log_param("temperature", temperature)
            mlflow.log_text(prompt_text, "prompt.txt")
            return run.info.run_id
    
    def log_query_result(
        self,
        user_id: str,
        query: str,
        intent: str,
        answer_length: int,
        evidence_count: int,
        retrieval_run_id: Optional[str] = None
    ):
        """
        Log query processing result.
        
        Args:
            user_id: User ID (hashed)
            query: User query
            intent: Detected intent
            answer_length: Length of generated answer
            evidence_count: Number of evidence entries
            retrieval_run_id: Associated retrieval run ID
        """
        import hashlib
        hashed_user_id = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        
        with mlflow.start_run(nested=True):
            mlflow.log_param("user_id_hash", hashed_user_id)
            mlflow.log_param("intent", intent)
            mlflow.log_param("query_length", len(query))
            mlflow.log_metric("answer_length", answer_length)
            mlflow.log_metric("evidence_count", evidence_count)
            if retrieval_run_id:
                mlflow.log_param("retrieval_run_id", retrieval_run_id)


def get_tracker() -> MLflowTracker:
    """Get or create MLflow tracker instance."""
    return MLflowTracker()

