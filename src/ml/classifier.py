"""SciBERT zero-shot classifier for paper screening with multiple backend support."""
import os
import re
from enum import Enum
from typing import Optional

from src.models.schemas import Paper, ScreeningResult


class BackendType(str, Enum):
    AUTO = "auto"
    PYTORCH = "pytorch"
    CTRANSFORMERS = "ctransformers"
    CTRANSFORMATE2 = "ctranslate2"


class SciBERTClassifier:
    """Zero-shot classifier using SciBERT with multiple backend support."""

    def __init__(
        self,
        model_name: str = "allenai/scibert_scivocab_uncased",
        device: str = "auto",
        backend: BackendType = BackendType.AUTO,
        model_path: Optional[str] = None,
    ):
        self.model_name = model_name
        self.device = device
        self.backend = self._resolve_backend(backend)
        self.model_path = model_path
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

        # Check if ctransformers/ctranslate2 is available
        try:
            import ctranslate2
            return BackendType.CTRANSFORMATE2
        except ImportError:
            pass

        return BackendType.PYTORCH

    def _lazy_import_pytorch(self):
        """Lazy import PyTorch."""
        if self._torch is None:
            try:
                import torch
                self._torch = torch
            except OSError:
                pass

    def _lazy_import_transformers(self):
        """Lazy import transformers."""
        if self._transformers is None:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                self._transformers = (AutoModelForSequenceClassification, AutoTokenizer)
            except ImportError:
                pass

    def _lazy_import_ctranslate2(self):
        """Lazy import ctranslate2."""
        if self._ctranslate2 is None:
            try:
                import ctranslate2
                self._ctranslate2 = ctranslate2
            except ImportError:
                pass

    def _get_device(self) -> str:
        """Get device for model."""
        if self.device == "auto":
            self._lazy_import_pytorch()
            if self._torch:
                return "cuda" if self._torch.cuda.is_available() else "cpu"
            return "cpu"
        return self.device

    def load(self):
        """Load the SciBERT model and tokenizer."""
        if self.backend == BackendType.CTRANSFORMATE2:
            self._load_ctranslate2()
        else:
            self._load_pytorch()

    def _load_ctranslate2(self):
        """Load model using ctranslate2 (fastest)."""
        self._lazy_import_ctranslate2()

        if self.model is None:
            model_path = self.model_path or f"./models/{self.model_name.split('/')[-1]}-ct2"
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(
                    f"Converted model not found at {model_path}. "
                    "Run: python scripts/convert_model.py"
                )

            self.model = self._ctranslate2.Transformer(model_path)
            
            from transformers import AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

    def _load_pytorch(self):
        """Load model using PyTorch/transformers."""
        self._lazy_import_pytorch()
        self._lazy_import_transformers()

        if not self._torch or not self._transformers:
            raise RuntimeError(
                "PyTorch or transformers not available. "
                "Install: pip install torch transformers"
            )

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

        if self.backend == BackendType.CTRANSFORMATE2:
            score = self._classify_ctranslate2(include_prompt, text)
        else:
            score = self._classify_pytorch(include_prompt, text)

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

    def _classify_ctranslate2(self, prompt: str, text: str) -> float:
        """Classify using ctranslate2 (fast)."""
        # ctranslate2 requires different approach - use as feature extractor
        input_text = f"{prompt} [SEP] {text[:512]}"
        
        tokens = self.tokenizer.convert_ids_to_tokens(
            self.tokenizer.encode(input_text, truncation=True, max_length=512)
        )
        
        results = self.model.forward(tokens)
        
        # Get logits from last layer
        logits = results[0].scores
        probs = self._softmax(logits)
        return probs[1] if len(probs) > 1 else 0.5

    def _classify_pytorch(self, prompt: str, text: str) -> float:
        """Classify using PyTorch."""
        inputs = self.tokenizer(
            [prompt],
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
            return probs[0][1].item()

    def _softmax(self, scores) -> list:
        """Compute softmax."""
        if hasattr(scores, '__iter__'):
            scores = [s for s in scores]
            max_score = max(scores)
            exp_scores = [pow(2.71828, s - max_score) for s in scores]
            sum_exp = sum(exp_scores)
            return [e / sum_exp for e in exp_scores]
        return [1.0]

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

            if self.backend == BackendType.CTRANSFORMATE2:
                scores[label] = self._classify_ctranslate2(prompt, text)
            else:
                scores[label] = self._classify_pytorch(prompt, text)

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
        if self._torch and hasattr(self._torch.cuda, 'is_available'):
            if self._torch.cuda.is_available():
                self._torch.cuda.empty_cache()


def create_classifier(
    model_name: str = "allenai/scibert_scivocab_uncased",
    device: str = "auto",
    backend: str = "auto",
    model_path: Optional[str] = None,
) -> SciBERTClassifier:
    """Factory function to create classifier."""
    return SciBERTClassifier(
        model_name=model_name,
        device=device,
        backend=BackendType(backend),
        model_path=model_path,
    )
