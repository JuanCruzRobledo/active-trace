"""Generate SQL for a specific migration range."""

import subprocess
import sys
from pathlib import Path

# Use range syntax to get just 001 -> 002
result = subprocess.run(
    [
        sys.executable,
        "-m",
        "alembic",
        "upgrade",
        "head",
        "--sql",
    ],
    cwd=Path(__file__).resolve().parents[1],
    capture_output=True,
    text=True,
    encoding="utf-8",
)

if result.returncode != 0:
    print("STDOUT:", result.stdout, file=sys.stderr)
    print("STDERR:", result.stderr, file=sys.stderr)
    sys.exit(result.returncode)

sql = result.stdout
out_path = Path("C:/Users/lucas/AppData/Local/Temp/opencode/migration_002.sql")
out_path.write_text(sql, encoding="utf-8")
print(f"Wrote {out_path} ({len(sql)} chars)")
