import os
import uvicorn

if __name__ == "__main__":
    # Render provides PORT environment variable dynamically
    port = int(os.environ.get("PORT", 10000))
    print(f"[DocuMind AI] Launching Uvicorn on 0.0.0.0:{port}")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
