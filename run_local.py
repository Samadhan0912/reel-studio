"""Start the real Reel Studio API and bundled UI."""
import os
from pathlib import Path

import uvicorn


if __name__ == "__main__":
    # Resolve .env, data/, uploads/, and outputs/ relative to this project even
    # when the script is launched as `python backend/run_local.py` from the root.
    os.chdir(Path(__file__).resolve().parent)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
