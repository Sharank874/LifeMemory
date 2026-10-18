"""
Drift detection using Evidently AI for embedding and topic drift.
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metrics import (
    DataDriftTable,
    EmbeddingsDriftMetric,
    TextDescriptorsDriftMetric
)
from dotenv import load_dotenv

load_dotenv()


class DriftDetector:
    """Evidently AI integration for detecting embedding and topic drift."""
    
    def __init__(self):
        self.reference_data: Optional[pd.DataFrame] = None
        self.column_mapping = ColumnMapping(
            embeddings="embedding",
            text_features=["content"],
            categorical_features=["mood"]
        )
    
    def set_reference_data(self, journals: List[Dict]):
        """
        Set reference dataset for drift detection.
        
        Args:
            journals: List of journal entries with embeddings
        """
        df_data = []
        for journal in journals:
            if journal.get("embedding"):
                df_data.append({
                    "content": journal.get("content", "")[:500],  # Truncate for efficiency
                    "mood": journal.get("mood", ""),
                    "embedding": journal.get("embedding", [])
                })
        
        if df_data:
            self.reference_data = pd.DataFrame(df_data)
    
    def detect_drift(self, current_journals: List[Dict]) -> Dict:
        """
        Detect drift in current data compared to reference.
        
        Args:
            current_journals: Current journal entries to compare
            
        Returns:
            Dict: Drift detection results
        """
        if self.reference_data is None or len(self.reference_data) == 0:
            return {
                "drift_detected": False,
                "message": "No reference data set"
            }
        
        # Prepare current data
        current_data = []
        for journal in current_journals:
            if journal.get("embedding"):
                current_data.append({
                    "content": journal.get("content", "")[:500],
                    "mood": journal.get("mood", ""),
                    "embedding": journal.get("embedding", [])
                })
        
        if not current_data:
            return {
                "drift_detected": False,
                "message": "No current data to compare"
            }
        
        current_df = pd.DataFrame(current_data)
        
        # Create drift report
        report = Report(metrics=[
            DataDriftTable(),
            EmbeddingsDriftMetric(column_name="embedding"),
            TextDescriptorsDriftMetric(column_name="content")
        ])
        
        report.run(
            reference_data=self.reference_data,
            current_data=current_df,
            column_mapping=self.column_mapping
        )
        
        # Extract results
        result = report.as_dict()
        
        # Check if drift is detected
        drift_detected = False
        drift_score = 0.0
        
        if "metrics" in result:
            for metric in result["metrics"]:
                if "drift_score" in metric:
                    drift_score = max(drift_score, metric["drift_score"])
                if metric.get("drift_detected", False):
                    drift_detected = True
        
        return {
            "drift_detected": drift_detected,
            "drift_score": drift_score,
            "timestamp": datetime.utcnow().isoformat(),
            "reference_size": len(self.reference_data),
            "current_size": len(current_df)
        }


def get_drift_detector() -> DriftDetector:
    """Get or create drift detector instance."""
    return DriftDetector()

