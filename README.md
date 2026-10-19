# Expense Tracker — Flask + SQLite

A Flask web application built as an upgrade to the original Python/Pandas/Matplotlib expense tracker.

## Features in this starter
- Dashboard with monthly totals and interactive category chart
- Add, view, and delete expenses
- Monthly category budgets and 80% / exceeded-budget alerts
- Download monthly CSV and PDF reports
- CSV-to-SQLite migration helper

## Important data-safety notes
- `migrate_csv.py` backs up `expenses.csv` to `expenses.csv.backup` and does not modify the original CSV.
- It accepts `YYYY-MM-DD`, `DD-MM-YYYY`, and `MM-DD-YYYY` dates. Ambiguous dates are interpreted day-first where possible; review any ambiguous legacy rows manually.
- Invalid rows are reported and skipped rather than silently changed.
- Re-running the importer avoids many duplicate imports by matching date, category, amount, and description. Identical legitimate expenses may be considered duplicates; inspect the report and database before repeated imports.
- `instance/expenses.db` is local and excluded from Git. Do not commit personal transaction data.

## Setup on Windows

Open a terminal in this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy your existing `expenses.csv` into this folder if it is not already here.

Back up and migrate the CSV:

```powershell
python migrate_csv.py
```

Review the output, especially skipped rows and totals. Then start the app:

```powershell
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Before publishing
- Change `SECRET_KEY` in `app.py` to a private random value.
- Do not deploy Flask's debug server publicly.
- Keep `instance/`, `.env`, and personal CSV backups out of Git.
- This starter is intended for local personal use and has no login system yet.
