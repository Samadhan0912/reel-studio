"""Start FastAPI when installed, otherwise use the dependency-free preview API."""
try:
    import uvicorn
    from app.main import app
except ImportError as exc:
    print(f"FastAPI dependencies are unavailable ({exc}). Starting the in-memory demo preview instead.")
    from demo_server import run
    run()
else:
    uvicorn.run(app, host="127.0.0.1", port=8000)
