# =================== AIPass ====================
# Name: embed_subprocess.py
# Description: Embedding Subprocess Handler
# Version: 2.0.0
# Created: 2026-03-12
# Modified: 2026-05-07
# =============================================

"""
Embedding Subprocess Handler

Called via subprocess from rollover orchestrator to generate embeddings
using fastembed (ONNX runtime, no torch dependency).

Input: JSON on stdin with texts to encode
Output: JSON on stdout with embeddings
"""

import sys
import json


def main():
    """Process embedding request from stdin JSON."""
    try:
        input_data = json.load(sys.stdin)
        texts = input_data.get("texts", [])

        if not texts:
            print(json.dumps({"success": True, "embeddings": [], "count": 0, "dimension": 384}))
            return

        from fastembed import TextEmbedding

        model = TextEmbedding("all-MiniLM-L6-v2")

        sorted_pairs = sorted(enumerate(texts), key=lambda x: len(x[1]))
        sorted_indices, sorted_texts = zip(*sorted_pairs)

        embeddings = list(model.embed(list(sorted_texts)))

        ordered = [None] * len(texts)
        for orig_idx, sorted_idx in enumerate(sorted_indices):
            ordered[sorted_idx] = embeddings[orig_idx].tolist()

        print(json.dumps({"success": True, "embeddings": ordered, "count": len(ordered), "dimension": 384}))

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
