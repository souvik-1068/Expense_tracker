"""Import expenses.csv into SQLite without changing the original CSV.

Run once from the project folder:
    python migrate_csv.py
Review the printed report before using the web app.
"""
import csv
import shutil
from datetime import datetime
from pathlib import Path

from database import DB_PATH, init_db, get_db

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "expenses.csv"
BACKUP_PATH = ROOT / "expenses.csv.backup"


def normalize_date(value):
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date: {value!r}")


def main():
    if not CSV_PATH.exists():
        print(f"No CSV found at {CSV_PATH}. No data imported.")
        return

    if not BACKUP_PATH.exists():
        shutil.copy2(CSV_PATH, BACKUP_PATH)
        print(f"Backup created: {BACKUP_PATH}")
    else:
        print(f"Backup already exists; leaving it unchanged: {BACKUP_PATH}")

    init_db()
    imported = 0
    skipped = []
    with CSV_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"Date", "Category", "Amount", "Description"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise SystemExit(
                f"CSV headers must include {sorted(required)}. Found: {reader.fieldnames}"
            )
        for line_number, row in enumerate(reader, start=2):
            try:
                normalized_date = normalize_date(row.get("Date"))
                category = (row.get("Category") or "").strip()
                amount = float(row.get("Amount", ""))
                description = (row.get("Description") or "").strip()
                if not category:
                    raise ValueError("empty category")
                if amount <= 0:
                    raise ValueError("amount must be positive")
            except (ValueError, TypeError) as exc:
                skipped.append((line_number, str(exc)))
                continue

            with get_db() as conn:
                # Import marker based on all source fields prevents accidental re-imports.
                exists = conn.execute(
                    """SELECT 1 FROM expenses
                       WHERE date=? AND category=? AND amount=? AND description=? LIMIT 1""",
                    (normalized_date, category, amount, description),
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO expenses(date, category, amount, description) VALUES (?, ?, ?, ?)",
                        (normalized_date, category, amount, description),
                    )
                    conn.commit()
                    imported += 1

    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM expenses").fetchone()["n"]
        total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses").fetchone()["total"]

    print(f"New rows imported: {imported}")
    print(f"Total rows currently in SQLite: {count}")
    print(f"SQLite total amount: {total:.2f}")
    if skipped:
        print("\nRows skipped for review (original CSV is unchanged):")
        for line, reason in skipped:
            print(f"  Line {line}: {reason}")


if __name__ == "__main__":
    main()
