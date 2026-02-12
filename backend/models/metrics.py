"""
Usage and Cost Metrics Model
Tracks API usage counts and computes rough cost estimates.
"""

import os
import logging
from datetime import datetime
from typing import Dict
from models.mongodb_connection import mongodb_client

logger = logging.getLogger(__name__)

COLLECTION = "usage_metrics"
DOC_ID = "global"

DEFAULT_COSTS = {
    "perplexity_search_per_call": float(os.getenv("PERPLEXITY_COST_PER_CALL", "0.05")),
    "groq_summary_per_call": float(os.getenv("GROQ_SUMMARY_COST_PER_CALL", "0.002")),
    "groq_title_per_call": float(os.getenv("GROQ_TITLE_COST_PER_CALL", "0.001")),
}


class MetricsModel:
    def __init__(self):
        self.db = mongodb_client.db if mongodb_client else None
        self.col = self.db[COLLECTION] if (self.db is not None) else None
        if self.col is None:
            logger.warning("Metrics collection unavailable")
        else:
            self.col.update_one(
                {"_id": DOC_ID},
                {"$setOnInsert": {
                    "_id": DOC_ID,
                    "perplexity_calls": 0,
                    "groq_summaries": 0,
                    "groq_titles": 0,
                    "news_refreshes": 0,
                    "last_updated": datetime.utcnow(),
                }},
                upsert=True,
            )

    def _inc(self, field: str, amount: int = 1):
        if self.col is None:
            return
        self.col.update_one(
            {"_id": DOC_ID},
            {"$inc": {field: amount}, "$set": {"last_updated": datetime.utcnow()}},
            upsert=True,
        )

    def inc_perplexity(self):
        self._inc("perplexity_calls")

    def inc_groq_summary(self):
        self._inc("groq_summaries")

    def inc_groq_title(self):
        self._inc("groq_titles")

    def inc_news_refresh(self):
        self._inc("news_refreshes")

    def get(self) -> Dict:
        if self.col is None:
            return {"available": False}
        doc = self.col.find_one({"_id": DOC_ID}) or {}
        # Cost estimates
        costs = DEFAULT_COSTS
        est = {
            "perplexity": doc.get("perplexity_calls", 0) * costs["perplexity_search_per_call"],
            "groq": doc.get("groq_summaries", 0) * costs["groq_summary_per_call"] + doc.get("groq_titles", 0) * costs["groq_title_per_call"],
        }
        return {
            "available": True,
            **doc,
            "estimated_costs": {
                **est,
                "total": round(est.get("perplexity", 0) + est.get("groq", 0), 4),
            },
            "unit_costs": costs,
        }


metrics_model = MetricsModel()