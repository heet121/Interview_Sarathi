#!/usr/bin/env python3
"""
Fine-tune DeBERTa-v3 for multi-dimensional answer scoring (judge model).
"""
from __future__ import annotations

import json
import os
import sys
# Avoid TensorFlow/Keras import conflicts — we only use PyTorch.
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.prepare_judge_data import DIMS

DEFAULT_DATA = os.path.join("data", "research", "v1", "judge")
DEFAULT_OUT = os.path.join("models", "judge", "deberta-v3-base-v1")
DEFAULT_MODEL = "microsoft/deberta-v3-base"


class JudgeDataset(Dataset):
    def __init__(self, path: str, tokenizer, max_len: int = 256):
        self.rows = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.rows.append(json.loads(line))
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        r = self.rows[idx]
        text = f"Question: {r['question']} Answer: {r['answer']}"
        enc = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_len,
            return_tensors="pt",
        )
        labels = torch.tensor([r["labels"][d] for d in DIMS], dtype=torch.float32)
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": labels,
        }


class MultiRegTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        loss = torch.nn.functional.mse_loss(logits, labels)
        return (loss, outputs) if return_outputs else loss


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default=DEFAULT_DATA)
    p.add_argument("--out-dir", default=DEFAULT_OUT)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--max-len", type=int, default=256)
    args = p.parse_args()

    train_path = os.path.join(args.data_dir, "judge_train.jsonl")
    val_path = os.path.join(args.data_dir, "judge_val.jsonl")
    if not os.path.exists(train_path):
        raise SystemExit(f"Missing {train_path}. Run prepare_judge_data first.")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device} | Model: {args.model}")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=len(DIMS),
        problem_type="regression",
    )

    train_ds = JudgeDataset(train_path, tokenizer, args.max_len)
    val_ds = JudgeDataset(val_path, tokenizer, args.max_len)

    os.makedirs(args.out_dir, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=args.out_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=50,
        learning_rate=2e-5,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        report_to="none",
        fp16=torch.cuda.is_available(),
    )

    trainer = MultiRegTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
    )

    print(f"Training on {len(train_ds)} samples…")
    trainer.train()
    trainer.save_model(args.out_dir)
    tokenizer.save_pretrained(args.out_dir)

    meta = {"model": args.model, "dims": DIMS, "max_len": args.max_len}
    with open(os.path.join(args.out_dir, "judge_config.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Judge model saved to {args.out_dir}")


if __name__ == "__main__":
    main()
