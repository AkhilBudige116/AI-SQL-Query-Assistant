"""
Streamlit Community Cloud default entry point alias.
Executes app.py directly.
"""

import runpy
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

runpy.run_path(os.path.join(BASE_DIR, "app.py"), run_name="__main__")
