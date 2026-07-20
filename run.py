import subprocess
import sys
import time
import os

def main():
    print("=" * 60)
    print(" Launching DocuMind AI (Full-Stack RAG System)")
    print("=" * 60)
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")

    # Start FastAPI Backend
    print("[DocuMind] Starting Backend server on http://127.0.0.1:8000 ...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
        cwd=root_dir
    )

    # Wait for FastAPI Backend to be ready
    print("[DocuMind] Waiting for Backend server to initialize...")
    import socket
    backend_ready = False
    for _ in range(30):
        try:
            with socket.create_connection(("127.0.0.1", 8000), timeout=1):
                backend_ready = True
                break
        except (OSError, ConnectionRefusedError):
            time.sleep(0.5)

    if backend_ready:
        print("[DocuMind] Backend is ready and listening on http://127.0.0.1:8000!")

    # Start Vite Frontend
    print("[DocuMind] Starting Frontend dev server on http://localhost:5173 ...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_process = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=frontend_dir
    )

    print("\n" + "=" * 60)
    print(" DocuMind AI Full-Stack App is LIVE!")
    print(" -> Frontend UI:  http://localhost:5173")
    print(" -> Backend API:  http://127.0.0.1:8000")
    print("=" * 60)
    print("Press Ctrl+C to stop both servers.\n")

    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\nStopping DocuMind AI servers...")
        backend_process.terminate()
        frontend_process.terminate()

if __name__ == "__main__":
    main()
