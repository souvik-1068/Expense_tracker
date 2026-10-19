from datetime import datetime, date
from io import BytesIO, StringIO
import csv

from flask import Flask, render_template, request, redirect, url_for, flash, Response, send_file
import pandas as pd
import plotly.express as px
import plotly.io as pio

from database import get_db, init_db, DB_PATH

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-to-a-random-secret-before-deployment"


def month_bounds(month_text):
    try:
        month = datetime.strptime(month_text, "%Y-%m")
        return month.strftime("%Y-%m-01"), (month.replace(day=28) + pd.Timedelta(days=4)).replace(day=1).strftime("%Y-%m-%d")
    except ValueError:
        return None, None


@app.before_request
def ensure_database():
    init_db()


@app.get("/")
def dashboard():
    today = date.today()
    selected_month = request.args.get("month", today.strftime("%Y-%m"))
    start, next_month = month_bounds(selected_month)
    if not start:
        selected_month = today.strftime("%Y-%m")
        start, next_month = month_bounds(selected_month)

    with get_db() as conn:
        total_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE date >= ? AND date < ?",
            (start, next_month),
        ).fetchone()
        category_rows = conn.execute(
            """SELECT category, SUM(amount) AS total
               FROM expenses WHERE date >= ? AND date < ?
               GROUP BY category ORDER BY total DESC""",
            (start, next_month),
        ).fetchall()
        recent = conn.execute(
            "SELECT id, date, category, amount, description FROM expenses ORDER BY date DESC, id DESC LIMIT 10"
        ).fetchall()
        all_rows = conn.execute(
            "SELECT date, category, amount, description FROM expenses WHERE date >= ? AND date < ? ORDER BY date",
            (start, next_month),
        ).fetchall()
        budget_rows = conn.execute(
            "SELECT category, monthly_limit FROM budgets WHERE month = ?", (selected_month,)
        ).fetchall()

    category_data = [{"category": r["category"], "total": r["total"]} for r in category_rows]
    chart_html = ""
    if category_data:
        fig = px.pie(category_data, names="category", values="total", hole=0.45, title=None)
        fig.update_traces(textposition="inside", textinfo="percent", insidetextorientation="auto",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Amount: ₹%{value:.2f}<br>"
                "Share: %{percent}"
                "<extra></extra>"
            )
        )

        fig.update_layout(
            height=380,
            autosize=True,
            margin=dict(l=20, r=20, t=20, b=70),
            font=dict(size=13),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.12,
                xanchor="center",
                x=0.5
            ),
            showlegend=True
        )

        chart_html = pio.to_html(
            fig,
            full_html=False,
            include_plotlyjs="cdn",
            config={"responsive": True},
            default_width="100%",
            default_height="380px"
        )

    month_total = float(total_row["total"] or 0)
    budgets = {r["category"]: float(r["monthly_limit"]) for r in budget_rows}
    alerts = []
    for item in category_data:
        limit = budgets.get(item["category"])
        if limit:
            ratio = item["total"] / limit
            if ratio >= 1:
                alerts.append(f'{item["category"]}: over budget by ₹{item["total"] - limit:.2f}.')
            elif ratio >= 0.8:
                alerts.append(f'{item["category"]}: {ratio:.0%} of budget used.')
    return render_template(
        "dashboard.html", month=selected_month, month_total=month_total,
        categories=category_data, recent=recent, chart_html=chart_html, alerts=alerts
    )


@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    if request.method == "POST":
        date_text = request.form.get("date", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        amount_text = request.form.get("amount", "").strip()
        try:
            parsed_date = datetime.strptime(date_text, "%Y-%m-%d").date().isoformat()
            amount = float(amount_text)
            if amount <= 0:
                raise ValueError
            if not category:
                raise ValueError
        except ValueError:
            flash("Enter a valid date (YYYY-MM-DD), category, and positive amount.", "error")
            return redirect(url_for("expenses"))
        with get_db() as conn:
            conn.execute(
                "INSERT INTO expenses(date, category, amount, description) VALUES (?, ?, ?, ?)",
                (parsed_date, category, amount, description),
            )
            conn.commit()
        flash("Expense added successfully.", "success")
        return redirect(url_for("expenses"))

    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, date, category, amount, description FROM expenses ORDER BY date DESC, id DESC"
        ).fetchall()
    return render_template("expenses.html", expenses=rows, today=date.today().isoformat())


@app.post("/expenses/<int:expense_id>/delete")
def delete_expense(expense_id):
    with get_db() as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("expenses"))


@app.route("/budgets", methods=["GET", "POST"])
def budgets():
    month = request.values.get("month", date.today().strftime("%Y-%m"))
    if not month_bounds(month)[0]:
        month = date.today().strftime("%Y-%m")
    if request.method == "POST":
        category = request.form.get("category", "").strip()
        try:
            limit = float(request.form.get("monthly_limit", ""))
            if not category or limit <= 0:
                raise ValueError
        except ValueError:
            flash("Enter a category and a positive budget amount.", "error")
            return redirect(url_for("budgets", month=month))
        with get_db() as conn:
            conn.execute(
                """INSERT INTO budgets(month, category, monthly_limit) VALUES (?, ?, ?)
                   ON CONFLICT(month, category) DO UPDATE SET monthly_limit=excluded.monthly_limit""",
                (month, category, limit),
            )
            conn.commit()
        flash("Budget saved.", "success")
        return redirect(url_for("budgets", month=month))

    start, next_month = month_bounds(month)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT b.category, b.monthly_limit,
                      COALESCE(SUM(e.amount), 0) AS spent
               FROM budgets b LEFT JOIN expenses e
                 ON e.category = b.category AND e.date >= ? AND e.date < ?
               WHERE b.month = ?
               GROUP BY b.category, b.monthly_limit ORDER BY b.category""",
            (start, next_month, month),
        ).fetchall()
    return render_template("budgets.html", month=month, budgets=rows)


@app.get("/reports/csv")
def export_csv():
    start_month = request.args.get("month", date.today().strftime("%Y-%m"))
    start, next_month = month_bounds(start_month)
    if not start:
        flash("Invalid month.", "error")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT date, category, amount, description FROM expenses WHERE date >= ? AND date < ? ORDER BY date",
            (start, next_month),
        ).fetchall()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Category", "Amount", "Description"])
    writer.writerows([tuple(row) for row in rows])
    return Response(
        output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=expenses-{start_month}.csv"},
    )


@app.get("/reports/pdf")
def export_pdf():
    # ReportLab is used for PDF generation; install it via requirements.txt.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet

    month = request.args.get("month", date.today().strftime("%Y-%m"))
    start, next_month = month_bounds(month)
    if not start:
        flash("Invalid month.", "error")
        return redirect(url_for("dashboard"))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT date, category, amount, description FROM expenses WHERE date >= ? AND date < ? ORDER BY date",
            (start, next_month),
        ).fetchall()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    data = [["Date", "Category", "Amount (INR)", "Description"]]
    data += [[r["date"], r["category"], f'{r["amount"]:.2f}', r["description"] or ""] for r in rows]
    total = sum(float(r["amount"]) for r in rows)
    story = [Paragraph(f"Expense Report — {month}", styles["Title"]), Spacer(1, 12),
             Paragraph(f"Total expenses: ₹{total:.2f}", styles["Heading2"]), Spacer(1, 12)]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243b53")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name=f"expenses-{month}.pdf")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
