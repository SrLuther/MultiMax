import os
import sys

base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))
print("base_dir:", base_dir)
print("current dir:", os.getcwd())
print(".env path:", os.path.join(base_dir, ".env"))
print(".env exists:", os.path.exists(os.path.join(base_dir, ".env")))
