# D:\FYP\FORGE-1\components\recalculate_embeddings.py
import os
import json
import time
from pathlib import Path
from sentence_transformers import SentenceTransformer

COMPONENTS_DIR = Path(__file__).resolve().parent
CATALOG_PATH = COMPONENTS_DIR / "components_catalog.json"
OUTPUT_PATH = COMPONENTS_DIR / "component_embeddings.json"


def recalculate_embeddings():
    print(f"Reading components catalog from: {CATALOG_PATH}")
    if not CATALOG_PATH.is_file():
        raise FileNotFoundError(f"Catalog file not found at {CATALOG_PATH}")

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    print(f"Loaded {len(catalog)} components from catalog.")

    # Load model
    print("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
    start_time = time.time()
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"Model loaded in {time.time() - start_time:.2f}s")

    # Extract component IDs and descriptions
    cids = []
    descriptions = []
    for item in catalog:
        cid = item.get("component_id")
        desc = item.get("description", "")
        if not cid:
            continue
        cids.append(cid)
        descriptions.append(desc)

    print(f"Encoding {len(descriptions)} component descriptions...")
    encode_start = time.time()
    # Batch encode all descriptions with normalization
    embeddings_matrix = model.encode(descriptions, batch_size=32, show_progress_bar=True)
    print(f"Encoded in {time.time() - encode_start:.2f}s")

    # Map each component_id to its 384-dim vector as list of floats
    embeddings_dict = {}
    for cid, vec in zip(cids, embeddings_matrix):
        embeddings_dict[cid] = [float(x) for x in vec]

    print(f"Writing embeddings to: {OUTPUT_PATH}")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(embeddings_dict, f, indent=2)

    file_size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Done! Successfully generated embeddings for {len(embeddings_dict)} components.")
    print(f"Output file size: {file_size_kb:.1f} KB. Embedding dimension: {len(next(iter(embeddings_dict.values())))}.")


if __name__ == "__main__":
    recalculate_embeddings()
