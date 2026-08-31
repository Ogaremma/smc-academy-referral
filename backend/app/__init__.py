import os
import sys

# Ensure backend root directory is in sys.path for runtime import resolution
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

__version__ = "0.1.0"
