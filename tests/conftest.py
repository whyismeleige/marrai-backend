import sys
import pathlib

# Ensure the repo root is importable regardless of the working directory.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))