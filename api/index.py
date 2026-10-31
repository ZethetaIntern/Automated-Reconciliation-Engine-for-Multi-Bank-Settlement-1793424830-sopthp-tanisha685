"""
Vercel Serverless Function Entry Point for PayBridge Automated Reconciliation Engine.
Imports FastAPI ASGI app and exposes it to the Vercel Python runtime.
"""

import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.main import app
