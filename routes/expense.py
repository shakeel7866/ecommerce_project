from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db import mysql

expense = Blueprint("expense", __name__)


# ==========================================
# EXPENSE CATEGORY LIST + ADD
# ==========================================
@expense.route("/admin/expense-categories", methods=["GET", "POST"])
def expense_categories():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":

        category_name = request.form.get("category_name", "").strip()

        description = request.form.get("description", "").strip()

        if not category_name:

            flash("Category name is required!", "danger")

            cur.close()

            return redirect(url_for("expense.expense_categories"))

        try:

            cur.execute(
                """
                INSERT INTO expense_categories
                (
                    category_name,
                    description
                )
                VALUES(%s,%s)
            """,
                (category_name, description),
            )

            mysql.connection.commit()

            flash("Expense Category Added Successfully!", "success")

        except Exception as e:

            mysql.connection.rollback()

            flash("Category already exists!", "danger")

        return redirect(url_for("expense.expense_categories"))

    cur.execute("""
        SELECT
            id,
            category_name,
            description,
            created_at
        FROM expense_categories
        ORDER BY id DESC
    """)

    categories = cur.fetchall()

    cur.close()

    return render_template("admin/expenses/categories.html", categories=categories)


# ==========================================
# EXPENSE LIST
# ==========================================
@expense.route("/admin/expenses")
def expense_list():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # ==========================
    # FILTERS
    # ==========================
    category_id = request.args.get("category_id", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    # ==========================
    # TOTAL EXPENSE
    # ==========================

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
    """)

    total_expense = cur.fetchone()[0]

    # ==========================
    # TODAY EXPENSE
    # ==========================

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE expense_date = CURDATE()
    """)

    today_expense = cur.fetchone()[0]

    # ==========================
    # THIS MONTH EXPENSE
    # ==========================

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE MONTH(expense_date) = MONTH(CURDATE())
        AND YEAR(expense_date) = YEAR(CURDATE())
    """)

    month_expense = cur.fetchone()[0]

    # ==========================
    # EXPENSE LIST
    # ==========================

    cur.execute("""
        SELECT
            expenses.id,
            expense_categories.category_name,
            expenses.amount,
            expenses.expense_date,
            expenses.description
        FROM expenses
        INNER JOIN expense_categories
            ON expenses.category_id =
               expense_categories.id
        ORDER BY
            expenses.expense_date DESC,
            expenses.id DESC
    """)

    expenses = cur.fetchall()

    # ==========================
    # GET EXPENSE CATEGORIES
    # ==========================

    cur.execute("""
        SELECT
            id,
            category_name
        FROM expense_categories
        ORDER BY category_name ASC
    """)

    categories = cur.fetchall()

    cur.close()

    return render_template(
        "admin/expenses/list.html",
        expenses=expenses,
        total_expense=total_expense,
        today_expense=today_expense,
        month_expense=month_expense,
        categories=categories,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
    )


# ==========================================
# ADD EXPENSE
# ==========================================
@expense.route("/admin/expenses/add", methods=["GET", "POST"])
def add_expense():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":

        category_id = request.form.get("category_id")
        amount = request.form.get("amount")
        expense_date = request.form.get("expense_date")
        description = request.form.get("description", "").strip()

        if not category_id or not amount or not expense_date:

            flash("Please fill all required fields!", "danger")

            cur.close()

            return redirect(url_for("expense.add_expense"))

        try:

            amount = float(amount)

            if amount <= 0:
                raise ValueError

        except ValueError:

            flash("Please enter a valid amount!", "danger")

            cur.close()

            return redirect(url_for("expense.add_expense"))

        cur.execute(
            """
            INSERT INTO expenses
            (
                category_id,
                amount,
                expense_date,
                description
            )
            VALUES(%s,%s,%s,%s)
        """,
            (category_id, amount, expense_date, description),
        )

        mysql.connection.commit()

        cur.close()

        flash("Expense Added Successfully!", "success")

        return redirect(url_for("expense.expense_list"))

    cur.execute("""
        SELECT
            id,
            category_name
        FROM expense_categories
        ORDER BY category_name ASC
    """)

    categories = cur.fetchall()

    cur.close()

    return render_template("admin/expenses/add.html", categories=categories)


# ==========================================
# EDIT EXPENSE
# ==========================================
@expense.route("/admin/expenses/edit/<int:id>", methods=["GET", "POST"])
def edit_expense(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":

        category_id = request.form.get("category_id")
        amount = request.form.get("amount")
        expense_date = request.form.get("expense_date")
        description = request.form.get("description", "").strip()

        if not category_id or not amount or not expense_date:

            flash("Please fill all required fields!", "danger")

            return redirect(url_for("expense.edit_expense", id=id))

        try:

            amount = float(amount)

            if amount <= 0:
                raise ValueError

        except ValueError:

            flash("Please enter a valid amount!", "danger")

            return redirect(url_for("expense.edit_expense", id=id))

        cur.execute(
            """
            UPDATE expenses
            SET
                category_id=%s,
                amount=%s,
                expense_date=%s,
                description=%s
            WHERE id=%s
        """,
            (category_id, amount, expense_date, description, id),
        )

        mysql.connection.commit()

        cur.close()

        flash("Expense Updated Successfully!", "success")

        return redirect(url_for("expense.expense_list"))

    cur.execute(
        """
        SELECT
            id,
            category_id,
            amount,
            expense_date,
            description
        FROM expenses
        WHERE id=%s
    """,
        (id,),
    )

    expense_data = cur.fetchone()

    if not expense_data:

        cur.close()

        flash("Expense not found!", "danger")

        return redirect(url_for("expense.expense_list"))

    cur.execute("""
        SELECT
            id,
            category_name
        FROM expense_categories
        ORDER BY category_name ASC
    """)

    categories = cur.fetchall()

    cur.close()

    return render_template(
        "admin/expenses/edit.html", expense=expense_data, categories=categories
    )


# ==========================================
# DELETE EXPENSE
# ==========================================
@expense.route("/admin/expenses/delete/<int:id>", methods=["POST"])
def delete_expense(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute(
        """
        DELETE FROM expenses
        WHERE id=%s
    """,
        (id,),
    )

    mysql.connection.commit()

    cur.close()

    flash("Expense Deleted Successfully!", "success")

    return redirect(url_for("expense.expense_list"))


# ==========================================
# EXPENSE REPORT
# ==========================================
@expense.route("/admin/expenses/report")
def expense_report():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # ==========================
    # CATEGORY-WISE EXPENSE
    # ==========================

    cur.execute("""
        SELECT
            expense_categories.category_name,
            COALESCE(SUM(expenses.amount), 0) AS total_amount
        FROM expense_categories
        LEFT JOIN expenses
            ON expenses.category_id = expense_categories.id
        GROUP BY
            expense_categories.id,
            expense_categories.category_name
        ORDER BY total_amount DESC
    """)

    category_report = cur.fetchall()

    # ==========================
    # MONTHLY EXPENSE REPORT
    # ==========================

    cur.execute("""
        SELECT
            DATE_FORMAT(
                expense_date,
                '%M %Y'
            ) AS month_name,

            COALESCE(SUM(amount), 0) AS total_amount

        FROM expenses

        GROUP BY
            YEAR(expense_date),
            MONTH(expense_date)

        ORDER BY
            YEAR(expense_date) DESC,
            MONTH(expense_date) DESC
    """)

    monthly_report = cur.fetchall()

    cur.close()

    return render_template(
        "admin/expenses/report.html",
        category_report=category_report,
        monthly_report=monthly_report,
    )
