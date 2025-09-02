import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))

if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"INFO: Added project root '{project_root}' to sys.path for testing")
