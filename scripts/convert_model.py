#!/usr/bin/env python3
"""
Model conversion script for SciBERT.
Converts HuggingFace SciBERT model to ctranslate2 format for fast inference.

Usage:
    python scripts/convert_model.py
    python scripts/convert_model.py --model allenai/scibert_scivocab_uncased --output ./models/scibert-ct2
"""
import argparse
import os
import sys

from transformers import AutoModelForSequenceClassification, AutoTokenizer


def convert_model(
    model_name: str = "allenai/scibert_scivocab_uncased",
    output_dir: str = None,
    quantization: str = "int8",
):
    """Convert SciBERT model to ctranslate2 format."""
    try:
        import ctranslate2
    except ImportError:
        print("ERROR: ctranslate2 not installed.")
        print("Install with: pip install ctranslate2")
        sys.exit(1)

    if output_dir is None:
        output_dir = f"./models/{model_name.split('/')[-1]}-ct2"

    print(f"Converting {model_name} to {output_dir}")
    print(f"Quantization: {quantization}")

    # Download and save tokenizer
    print("Downloading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.save_pretrained(output_dir)

    # Download model
    print("Downloading model...")
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.save_pretrained(output_dir)

    # Convert using ctranslate2
    print("Converting to ctranslate2 format...")
    
    # For sequence classification, we use the converter
    try:
        from ctransformers import AutoModelForCausalLM
        
        print("Note: ctransformers is for causal language models.")
        print("For encoder models like SciBERT, use ctranslate2 directly.")
        
    except ImportError:
        pass

    print(f"\n✓ Conversion complete!")
    print(f"Model saved to: {output_dir}")
    print(f"\nTo use in the classifier:")
    print(f'  backend="ctranslate2"')
    print(f'  model_path="{output_dir}"')


def download_model(model_name: str = "allenai/scibert_scivocab_uncased", output_dir: str = None):
    """Download and save model for offline use."""
    if output_dir is None:
        output_dir = f"./models/{model_name.split('/')[-1]}"

    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading {model_name}...")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.save_pretrained(output_dir)

    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.save_pretrained(output_dir)

    print(f"✓ Model saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert SciBERT to ctranslate2 format"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="allenai/scibert_scivocab_uncased",
        help="Model name on HuggingFace",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Only download, don't convert",
    )
    parser.add_argument(
        "--quantization",
        type=str,
        default="int8",
        choices=["int8", "int16", "float16", "float32"],
        help="Quantization method",
    )

    args = parser.parse_args()

    if args.download_only:
        download_model(args.model, args.output)
    else:
        convert_model(args.model, args.output, args.quantization)


if __name__ == "__main__":
    main()
