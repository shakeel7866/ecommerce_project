from flask import Blueprint, render_template, session, redirect, url_for
from database.db import mysql

stock = Blueprint("stock", __name__)


@stock.route("/admin/stock/history")
def stock_history():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            stock_history.id,
            products.product_name,
            stock_history.transaction_type,
            stock_history.quantity,
            stock_history.remarks,
            stock_history.created_at
        FROM stock_history
        INNER JOIN products
            ON products.id = stock_history.product_id
        ORDER BY stock_history.id DESC
    """)

    history = cur.fetchall()

    cur.close()

    return render_template("admin/stock/history.html", history=history)
