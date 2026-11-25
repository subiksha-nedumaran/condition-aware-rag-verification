"""Explicit first-run model provisioning; normal application runs remain offline."""

import argparse
from pathlib import Path

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_FILES = ("config.json", "model.safetensors", "tokenizer.json")


def ensure_model(*, download: bool = False, model_id: str = MODEL_ID) -> Path:
    from huggingface_hub import snapshot_download

    try:
        directory = Path(snapshot_download(
            repo_id=model_id,
            revision=MODEL_REVISION if model_id == MODEL_ID else None,
            local_files_only=not download,
            allow_patterns=list(MODEL_FILES),
        ))
        missing = [name for name in MODEL_FILES if not (directory / name).is_file()]
        if missing:
            raise FileNotFoundError(", ".join(missing))
        return directory
    except Exception as exc:
        raise RuntimeError(
            "Embedding model is missing or incomplete. With network access, run "
            "'python -m fieldguard.model_setup --download', then retry. "
            f"Model: {model_id}. Details: {exc}"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Download the pinned model revision (requires network).")
    args = parser.parse_args()
    try:
        print(f"Model ready: {ensure_model(download=args.download)}")
    except RuntimeError as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
