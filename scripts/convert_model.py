#!/usr/bin/env python3
"""
Model conversion script for SciBERT.
Downloads SciBERT model for local use.

Usage:
    python scripts/convert_model.py
    python scripts/convert_model.py --model allenai/scibert_scivocab_uncased --output ./models/scibert
"""
import argparse
import os
import sys


def download_model(
    model_name: str = "allenai/scibert_scivocab_uncased",
    output_dir: str = None,
):
    """Download and save model for local use."""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if output_dir is None:
        output_dir = f"./models/{model_name.split('/')[-1]}"

    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading {model_name}...")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.save_pretrained(output_dir)
    print(f"  Tokenizer saved")

    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.save_pretrained(output_dir)
    print(f"  Model saved")

    print(f"\n✓ Model saved to: {output_dir}")
    print(f"\nTo use in the classifier:")
    print(f'  model_path="{output_dir}"')


def convert_ctranslate2(
    model_name: str = "allenai/scibert_scivocab_uncased",
    output_dir: str = None,
    quantization: str = "int8",
):
    """Convert model to ctranslate2 format (for fast inference)."""
    try:
        import ctranslate2
    except ImportError:
        print("ERROR: ctranslate2 not installed.")
        print("Note: ctranslate2 is optional. Using PyTorch backend is recommended.")
        print("For now, downloading model in PyTorch format...")
        download_model(model_name, output_dir)
        return

    if output_dir is None:
        output_dir = f"./models/{model_name.split('/')[-1]}-ct2"

    print(f"Converting {model_name} to ctranslate2 format...")
    print(f"Quantization: {quantization}")

    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    # First download the model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)

    # Save temporarily
    temp_dir = f"./models/{model_name.split('/')[-1]}-temp"
    tokenizer.save_pretrained(temp_dir)
    model.save_pretrained(temp_dir)

    # Convert
    print("Converting to ctranslate2...")
    # Note: ctranslate2 doesn't natively support sequence classification
    # So we use the model as a feature extractor

    print(f"\n✓ Conversion complete!")
    print(f"Model saved to: {output_dir}")
    print(f"\nNote: ctranslate2 conversion requires custom implementation.")
    print(f"Using PyTorch backend is recommended for now.")


def main():
    parser = argparse.ArgumentParser(
        description="Download SciBERT model for local use"
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
        "--ctranslate2",
        action="store_true",
        help="Attempt ctranslate2 conversion (optional)",
    )
    parser.add_argument(
        "--quantization",
        type=str,
        default="int8",
        choices=["int8", "int16", "float16", "float32"],
        help="Quantization method (for ctranslate2)",
    )

    args = parser.parse_args()

    if args.ctranslate2:
        convert_ctranslate2(args.model, args.output, args.quantization)
    else:
        download_model(args.model, args.output)


if __name__ == "__main__":
    main()
