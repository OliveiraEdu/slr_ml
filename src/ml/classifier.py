"""SciBERT zero-shot classifier for paper screening."""
import re
from typing import Optional

from src.models.schemas import Paper, ScreeningResult


class SciBERTClassifier:
    """Zero-shot classifier using SciBERT."""

    def __init__(self, model_name: str = "allenai/scibert_scivocab_uncased", device: str = "auto"):
        self.model_name = model_name
        self.device = device
        self.tokenizer = None
        self.model = None
        self._torch = None
        self._transformers = None
        self._device_str = "cpu"

    def _lazy_import(self):
        """Lazy import to handle missing torch."""
        if self._torch is None:
            try:
                import torch
                self._torch = torch
            except OSError as e:
                raise RuntimeError(
                    "PyTorch not available. Install with: pip install torch"
                ) from e
        
        if self._transformers is None:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                self._transformers = (AutoModelForSequenceClassification, AutoTokenizer)
            except ImportError as e:
                raise RuntimeError(
                    "Transformers not available. Install with: pip install transformers"
                ) from e

    def _get_device(self) -> str:
        """Get device for model."""
        self._lazy_import()
        if self.device == "auto":
            return "cuda" if self._torch.cuda.is_available() else "cpu"
        return self.device

    def load(self):
        """Load the SciBERT model and tokenizer."""
        self._lazy_import()
        AutoModelForSequenceClassification, AutoTokenizer = self._transformers
        
        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        if self.model is None:
            self._device_str = self._get_device()
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                num_labels=2,
            )
            self.model.to(self._device_str)
            self.model.eval()

    def classify_relevance(
        self,
        paper: Paper,
        include_prompt: str,
        exclude_prompt: str,
        threshold: float = 0.5,
    ) -> ScreeningResult:
        """Classify paper relevance using zero-shot approach."""
        if not self.model:
            self.load()

        text = self._prepare_text(paper)
        if not text:
            return self._empty_result(paper, "text_too_short")

        inputs = self.tokenizer(
            [include_prompt, exclude_prompt],
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        inputs = {k: v.to(self._device_str) for k, v in inputs.items()}

        with self._torch.no_grad():
            outputs = self.model(**inputs)
            probs = self._torch.softmax(outputs.logits, dim=1)
            include_prob = probs[0][1].item()

        score = include_prob
        if score >= threshold:
            decision = "include"
        else:
            decision = "exclude"

        return ScreeningResult(
            paper_id=paper.id,
            stage="title_abstract",
            relevance_score=score,
            relevance_label=decision,
            decision=decision,
            confidence=abs(score - 0.5) * 2,
        )

    def classify_picoc(
        self,
        paper: Paper,
        picoc_labels: dict,
    ) -> dict[str, float]:
        """Classify paper against PICOC criteria."""
        if not self.model:
            self.load()

        text = self._prepare_text(paper)
        if not text:
            return {}

        scores = {}
        for label, config in picoc_labels.items():
            if not config.get("enabled", True):
                continue

            prompt = config.get("prompt", "").replace("{text}", text)

            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            inputs = {k: v.to(self._device_str) for k, v in inputs.items()}

            with self._torch.no_grad():
                outputs = self.model(**inputs)
                probs = self._torch.softmax(outputs.logits, dim=1)
                scores[label] = probs[0][1].item()

        return scores

    def _prepare_text(self, paper: Paper) -> str:
        """Prepare text from paper for classification."""
        parts = []
        if paper.title:
            parts.append(paper.title)
        if paper.abstract:
            parts.append(paper.abstract)

        text = " ".join(parts)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _empty_result(self, paper: Paper, reason: str) -> ScreeningResult:
        """Create empty result for papers that can't be classified."""
        return ScreeningResult(
            paper_id=paper.id,
            stage="title_abstract",
            relevance_score=0.0,
            relevance_label="unclassifiable",
            decision="uncertain",
            reason=reason,
            confidence=0.0,
        )

    def unload(self):
        """Unload model from memory."""
        if self.model:
            del self.model
            self.model = None
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        if self._torch and self._torch.cuda.is_available():
            self._torch.cuda.empty_cache()


def create_classifier(
    model_name: str = "allenai/scibert_scivocab_uncased",
    device: str = "auto",
) -> SciBERTClassifier:
    """Factory function to create classifier."""
    return SciBERTClassifier(model_name, device)
