import pandas as pd
import matplotlib.pyplot as plt
import os

FILE_NAME = "expenses.csv"


# Create CSV file if not exists
if not os.path.exists(FILE_NAME):
    df = pd.DataFrame(columns=["Date", "Category", "Amount", "Description"])
    df.to_csv(FILE_NAME, index=False)


# Add Expense
def add_expense():
    date = input("Enter date (YYYY-MM-DD): ")
    category = input("Enter category (Food, Travel, Shopping etc): ")
    amount = float(input("Enter amount: "))
    description = input("Enter description: ")

    new_data = pd.DataFrame({
        "Date": [date],
        "Category": [category],
        "Amount": [amount],
        "Description": [description]
    })

    new_data.to_csv(FILE_NAME, mode='a', header=False, index=False)

    print("Expense Added Successfully!")


# View Expenses
def view_expenses():
    df = pd.read_csv(FILE_NAME)

    if df.empty:
        print("No expenses found.")
    else:
        print("\nAll Expenses:\n")
        print(df)


# Monthly Summary
def monthly_summary():
    df = pd.read_csv(FILE_NAME)

    if df.empty:
        print("No data available.")
        return

    df["Date"] = pd.to_datetime(df["Date"])

    month = input("Enter month (YYYY-MM): ")

    monthly_data = df[df["Date"].dt.strftime('%Y-%m') == month]

    if monthly_data.empty:
        print("No expenses found for this month.")
        return

    total = monthly_data["Amount"].sum()

    print(f"\nTotal Expenses for {month}: ₹{total}")

    print("\nCategory-wise Spending:")
    print(monthly_data.groupby("Category")["Amount"].sum())


# Pie Chart Visualization
def show_pie_chart():
    df = pd.read_csv(FILE_NAME)

    if df.empty:
        print("No data available.")
        return

    category_sum = df.groupby("Category")["Amount"].sum()

    plt.figure(figsize=(7, 7))
    plt.pie(
        category_sum,
        labels=category_sum.index,
        autopct='%1.1f%%'
    )

    plt.title("Expense Distribution")
    plt.show()


# Main Menu
while True:
    print("\n===== Expense Tracker =====")
    print("1. Add Expense")
    print("2. View Expenses")
    print("3. Monthly Summary")
    print("4. Show Pie Chart")
    print("5. Exit")

    choice = input("Enter your choice: ")

    if choice == "1":
        add_expense()

    elif choice == "2":
        view_expenses()

    elif choice == "3":
        monthly_summary()

    elif choice == "4":
        show_pie_chart()

    elif choice == "5":
        print("Goodbye!")
        break

    else:
        print("Invalid Choice!")