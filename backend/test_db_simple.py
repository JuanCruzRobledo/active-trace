"""Quick test: can alembic run in trace_test?"""
import os
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:nikolan@localhost:5432/trace_test"

from alembic.config import Config
from alembic import command

cfg = Config("alembic.ini")
print("URL:", os.environ["DATABASE_URL"])
try:
    command.upgrade(cfg, "head")
    print("OK: upgrade head succeeded")
    command.downgrade(cfg, "base")
    print("OK: downgrade base succeeded")
except Exception as e:
    print(f"ERROR: {e}")
