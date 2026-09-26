import sys
import os
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import engine

def apply_sql_file(file_path: str):
    print(f"[*] Executing SQL migration: {file_path}")
    if not os.path.exists(file_path):
        print(f"[!] Migration file not found: {file_path}")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split statements
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

    print(f"[OK] Successfully applied {file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate.py <path_to_sql_file>")
        sys.exit(1)
    apply_sql_file(sys.argv[1])
