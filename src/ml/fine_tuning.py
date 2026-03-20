"""Fine-tuning pipeline for SciBERT on SLR screening tasks.

This module provides fine-tuning capabilities for SciBERT using labeled
paper data from active learning or manual screening.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
)
from datasets import Dataset


@dataclass
class FineTuningConfig:
    model_name: str = "allenai/scibert_scivocab_uncased"
    output_dir: str = "models/fine_tuned"
    num_epochs: int = 3
    per_device_batch_size: int = 8
    learning_rate: float = 2e-5
    warmup_steps: int = 100
    weight_decay: float = 0.01
    max_seq_length: int = 512
    fp16: bool = True
    eval_steps: int = 50
    save_steps: int = 100
    logging_steps: int = 10


class SciBERTFineTuner:
    """Fine-tune SciBERT for SLR paper classification.
    
    Uses a small set of labeled papers to fine-tune SciBERT for
    improved classification accuracy.
    """
    
    def __init__(
        self,
        config: Optional[FineTuningConfig] = None,
        device: str = "auto",
    ):
        self.config = config or FineTuningConfig()
        self.device = self._resolve_device(device)
        self.tokenizer = None
        self.model = None
        self.trainer = None
    
    def _resolve_device(self, device: str) -> str:
        """Resolve compute device."""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            return "cpu"
        return device
    
    def prepare_dataset(
        self,
        texts: list[str],
        labels: list[int],
    ) -> Dataset:
        """Prepare dataset for training.
        
        Args:
            texts: List of paper texts (title + abstract)
            labels: List of labels (1=include, 0=exclude)
            
        Returns:
            HuggingFace Dataset ready for training
        """
        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        
        dataset_dict = {
            "text": texts,
            "label": labels,
        }
        
        dataset = Dataset.from_dict(dataset_dict)
        
        def tokenize_function(examples):
            return self.tokenizer(
                examples["text"],
                truncation=True,
                max_length=self.config.max_seq_length,
                padding=False,
            )
        
        dataset = dataset.map(tokenize_function, batched=True)
        dataset = dataset.remove_columns(["text"])
        dataset = dataset.map(
            lambda x: {"labels": x["label"]},
            batched=False,
        )
        
        return dataset
    
    def train(
        self,
        train_texts: list[str],
        train_labels: list[int],
        eval_texts: Optional[list[str]] = None,
        eval_labels: Optional[list[int]] = None,
    ) -> dict:
        """Fine-tune the model on labeled data.
        
        Args:
            train_texts: Training texts
            train_labels: Training labels
            eval_texts: Optional evaluation texts
            eval_labels: Optional evaluation labels
            
        Returns:
            Training metrics
        """
        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        
        train_dataset = self.prepare_dataset(train_texts, train_labels)
        eval_dataset = None
        
        if eval_texts and eval_labels:
            eval_dataset = self.prepare_dataset(eval_texts, eval_labels)
        
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        training_args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=self.config.num_epochs,
            per_device_train_batch_size=self.config.per_device_batch_size,
            per_device_eval_batch_size=self.config.per_device_batch_size,
            learning_rate=self.config.learning_rate,
            warmup_steps=self.config.warmup_steps,
            weight_decay=self.config.weight_decay,
            fp16=self.config.fp16 and self.device == "cuda",
            eval_strategy="steps" if eval_dataset else "no",
            eval_steps=self.config.eval_steps if eval_dataset else None,
            save_steps=self.config.save_steps,
            logging_steps=self.config.logging_steps,
            load_best_model_at_end=True if eval_dataset else False,
            report_to=["none"],
        )
        
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.config.model_name,
            num_labels=2,
        )
        self.model.to(self.device)
        
        data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)
        
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
            tokenizer=self.tokenizer,
        )
        
        train_result = self.trainer.train()
        
        metrics = {
            "train_loss": train_result.training_loss,
            "train_steps": train_result.global_step,
        }
        
        if eval_dataset:
            eval_metrics = self.trainer.evaluate()
            metrics.update(eval_metrics)
        
        self.save_model()
        
        return metrics
    
    def predict(
        self,
        texts: list[str],
        batch_size: int = 16,
    ) -> list[dict]:
        """Predict relevance for texts.
        
        Args:
            texts: List of texts to classify
            batch_size: Batch size for inference
            
        Returns:
            List of predictions with scores
        """
        if self.model is None or self.tokenizer is None:
            raise ValueError("Model not trained. Call train() first.")
        
        self.model.eval()
        
        predictions = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            inputs = self.tokenizer(
                batch_texts,
                truncation=True,
                max_length=self.config.max_seq_length,
                padding=True,
                return_tensors="pt",
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=1)
                
                for j, text in enumerate(batch_texts):
                    include_prob = probs[j][1].item()
                    predictions.append({
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "include_probability": include_prob,
                        "exclude_probability": probs[j][0].item(),
                        "prediction": "include" if include_prob > 0.5 else "exclude",
                    })
        
        return predictions
    
    def save_model(self, path: Optional[str] = None):
        """Save fine-tuned model and tokenizer."""
        save_path = Path(path or self.config.output_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        if self.model:
            self.model.save_pretrained(str(save_path))
        if self.tokenizer:
            self.tokenizer.save_pretrained(str(save_path))
        
        config_file = save_path / "fine_tune_config.json"
        import json
        with open(config_file, "w") as f:
            json.dump({
                "base_model": self.config.model_name,
                "task": "slr_screening",
                "num_labels": 2,
            }, f, indent=2)
    
    def load_model(self, path: str):
        """Load a fine-tuned model."""
        self.model = AutoModelForSequenceClassification.from_pretrained(path)
        self.tokenizer = AutoTokenizer.from_pretrained(path)
        self.model.to(self.device)
    
    def get_model_path(self) -> Optional[str]:
        """Get path to saved model."""
        output_dir = Path(self.config.output_dir)
        if output_dir.exists():
            config_file = output_dir / "fine_tune_config.json"
            if config_file.exists():
                return str(output_dir)
        return None


def create_fine_tuner(config: dict) -> SciBERTFineTuner:
    """Create fine-tuner from configuration dictionary."""
    ft_config = FineTuningConfig(
        model_name=config.get("model_name", "allenai/scibert_scivocab_uncased"),
        output_dir=config.get("output_dir", "models/fine_tuned"),
        num_epochs=config.get("num_epochs", 3),
        per_device_batch_size=config.get("per_device_batch_size", 8),
        learning_rate=config.get("learning_rate", 2e-5),
        fp16=config.get("fp16", True),
    )
    return SciBERTFineTuner(config=ft_config)
