"""ML modules for SLR screening."""

from src.ml.classifier import SciBERTClassifier, create_classifier
from src.ml.keyword_filter import KeywordFilter, create_keyword_filter
from src.ml.active_learning import (
    ActiveLearningPipeline,
    CitationRanker,
    CertaintyBasedScreen,
    create_active_learning_pipeline,
    create_citation_ranker,
)
from src.ml.fine_tuning import SciBERTFineTuner, create_fine_tuner
from src.ml.snowballing import SnowballingSearcher, create_snowballer

__all__ = [
    "SciBERTClassifier",
    "create_classifier",
    "KeywordFilter",
    "create_keyword_filter",
    "ActiveLearningPipeline",
    "CitationRanker",
    "CertaintyBasedScreen",
    "create_active_learning_pipeline",
    "create_citation_ranker",
    "SciBERTFineTuner",
    "create_fine_tuner",
    "SnowballingSearcher",
    "create_snowballer",
]