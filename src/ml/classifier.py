"""SciBERT zero-shot classifier for paper screening with multiple backend support."""
import os
import re
from enum import Enum
from typing import Optional

from src.models.schemas import Paper, ScreeningResult


class BackendType(str, Enum):
    AUTO = "auto"
    PYTORCH = "pytorch"
    KEYWORD = "keyword"
    CTRANSFORMATE2 = "ctranslate2"


class SciBERTClassifier:
    """Zero-shot classifier using SciBERT with multiple backend support."""

    def __init__(
        self,
        model_name: str = "allenai/scibert_scivocab_uncased",
        device: str = "auto",
        backend: BackendType = BackendType.AUTO,
        model_path: Optional[str] = None,
        keywords: Optional[dict] = None,
    ):
        self.model_name = model_name
        self.device = device
        self.backend = self._resolve_backend(backend)
        self.model_path = model_path
        self.keywords = keywords or {}
        self.tokenizer = None
        self.model = None
        self._torch = None
        self._transformers = None
        self._ctranslate2 = None
        self._device_str = "cpu"

    def _resolve_backend(self, backend: BackendType) -> BackendType:
        """Resolve which backend to use."""
        if backend != BackendType.AUTO:
            return backend

        # Check if ctranslate2 is available
        try:
            import ctranslate2
            return BackendType.CTRANSFORMATE2
        except ImportError:
            pass

        # Check if PyTorch is available
        try:
            import torch
            import transformers
            return BackendType.PYTORCH
        except ImportError:
            pass

        # Fallback to keyword-based
        return BackendType.KEYWORD

    def load(self):
        """Load the SciBERT model and tokenizer."""
        if self.backend == BackendType.CTRANSFORMATE2:
            self._load_ctranslate2()
        elif self.backend == BackendType.PYTORCH:
            self._load_pytorch()
        else:
            # Keyword-based doesn't need loading
            pass

    def _load_ctranslate2(self):
        """Load model using ctranslate2 (fastest)."""
        try:
            import ctranslate2
            self._ctranslate2 = ctranslate2
        except ImportError:
            raise RuntimeError(
                "ctranslate2 not available. Install: pip install ctranslate2"
            )

        if self.model is None:
            model_path = self.model_path or f"./models/{self.model_name.split('/')[-1]}-ct2"
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(
                    f"Converted model not found at {model_path}. "
                    "Using keyword-based classification instead."
                )

            self.model = self._ctranslate2.Transformer(model_path)
            
            from transformers import AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

    def _load_pytorch(self):
        """Load model using PyTorch/transformers."""
        try:
            import torch
            import transformers
            self._torch = torch
            self._transformers = transformers
        except ImportError as e:
            raise RuntimeError(
                f"PyTorch/transformers not available: {e}. "
                "Using keyword-based classification instead."
            )

        if self.tokenizer is None:
            from transformers import AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        if self.model is None:
            from transformers import AutoModelForSequenceClassification
            
            self._device_str = self._get_device()
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                num_labels=2,
            )
            self.model.to(self._device_str)
            self.model.eval()

    def _get_device(self) -> str:
        """Get device for model."""
        if self.device == "auto":
            if self._torch:
                return "cuda" if self._torch.cuda.is_available() else "cpu"
            return "cpu"
        return self.device

    def classify_relevance(
        self,
        paper: Paper,
        include_prompt: str,
        exclude_prompt: str,
        threshold: float = 0.5,
    ) -> ScreeningResult:
        """Classify paper relevance using zero-shot approach."""
        
        # Use keyword-based if PyTorch not available
        if self.backend == BackendType.KEYWORD:
            return self._classify_keyword(paper, threshold)
        
        if not self.model:
            self.load()
            
        # If still no model, use keyword
        if not self.model:
            return self._classify_keyword(paper, threshold)

        if self.backend == BackendType.CTRANSFORMATE2:
            return self._classify_ctranslate2(paper, include_prompt, threshold)
        else:
            return self._classify_pytorch(paper, include_prompt, threshold)

    def _classify_keyword(self, paper: Paper, threshold: float = 0.5) -> ScreeningResult:
        """Classify using keyword matching (fallback when ML not available)."""
        text = self._prepare_text(paper).lower()
        
        required_keywords = self.keywords.get("required", [])
        optional_keywords = self.keywords.get("optional", [])
        
        required_matches = sum(1 for kw in required_keywords if kw.lower() in text)
        optional_matches = sum(1 for kw in optional_keywords if kw.lower() in text)
        
        # Calculate score
        max_required = len(required_keywords) if required_keywords else 1
        max_optional = len(optional_keywords) if optional_keywords else 1
        
        required_score = required_matches / max_required
        optional_score = optional_matches / max_optional
        
        # Weight: required keywords more important
        score = (required_score * 0.7) + (optional_score * 0.3)
        
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

    def _classify_pytorch(self, paper: Paper, prompt: str, threshold: float) -> ScreeningResult:
        """Classify using PyTorch."""
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        
        text = self._prepare_text(paper)
        
        inputs = self.tokenizer(
            [prompt],
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        inputs = {k: v.to(self._device_str) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            score = probs[0][1].item()

        decision = "include" if score >= threshold else "exclude"

        return ScreeningResult(
            paper_id=paper.id,
            stage="title_abstract",
            relevance_score=score,
            relevance_label=decision,
            decision=decision,
            confidence=abs(score - 0.5) * 2,
        )

    def _classify_ctranslate2(self, paper: Paper, prompt: str, threshold: float) -> ScreeningResult:
        """Classify using ctranslate2."""
        text = self._prepare_text(paper)
        
        input_text = f"{prompt} [SEP] {text[:512]}"
        
        tokens = self.tokenizer.convert_ids_to_tokens(
            self.tokenizer.encode(input_text, truncation=True, max_length=512)
        )
        
        results = self.model.forward(tokens)
        logits = results[0].scores
        
        # Simple softmax
        max_logit = max(logits)
        exp_logits = [pow(2.71828, l - max_logit) for l in logits]
        sum_exp = sum(exp_logits)
        probs = [e / sum_exp for e in exp_logits]
        
        score = probs[1] if len(probs) > 1 else 0.5
        decision = "include" if score >= threshold else "exclude"

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
        if self.backend == BackendType.KEYWORD:
            return {}
        
        if not self.model:
            self.load()
        
        if not self.model:
            return {}

        text = self._prepare_text(paper)
        if not text:
            return {}

        scores = {}
        import torch
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

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=1)
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

    def unload(self):
        """Unload model from memory."""
        if self.model:
            del self.model
            self.model = None
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None


def create_classifier(
    model_name: str = "allenai/scibert_scivocab_uncased",
    device: str = "auto",
    backend: str = "auto",
    model_path: Optional[str] = None,
    keywords: Optional[dict] = None,
) -> SciBERTClassifier:
    """Factory function to create classifier."""
    return SciBERTClassifier(
        model_name=model_name,
        device=device,
        backend=BackendType(backend),
        model_path=model_path,
        keywords=keywords,
    )
