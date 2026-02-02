#!/usr/bin/env python3

import warnings
import uvicorn
import os
warnings.filterwarnings("ignore", message=".*config_type.*shadows.*", category=UserWarning)

from config import setup_logging

setup_logging()

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=[
            "*.log", "*.log.*", "__pycache__", "*.pyc", "*.pyo", "*.pyd",
            "../mt-finance-agents-web/node_modules", "../mt-finance-agents-web/dist", "../mt-finance-agents-web/.git",
            "*.pkl", "data/*", "uploads/*", ".git/*", ".env*",
            "*.DS_Store", "*.md", "*.txt", "*.json", "package-lock.json"
        ],
        reload_dirs=["agents", "tools", "services", "utils", "routes", "cosmosservice"],
        log_level="info"
    )