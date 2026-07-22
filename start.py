import os
import sys

# ── Memory optimizations MUST be set before importing ML libs ──
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
# Tell torch to use minimal memory
os.environ["PYTORCH_NO_CUDA_MEMORY_CACHING"] = "1"

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"[DocuMind AI] Starting on host=0.0.0.0 port={port}", flush=True)
    sys.stdout.flush()
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        workers=1,           # single worker = lowest memory footprint
        log_level="info",
        access_log=True,
    )
