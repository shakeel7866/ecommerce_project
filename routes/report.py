from flask import Blueprint, render_template, session, redirect, url_for
from database.db import mysql  # Add this import

report = Blueprint("report", __name__)


# ===============================
# Reports Home
# ===============================
@report.route("/admin/reports")
def reports_home():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    return render_template("admin/reports/index.html")


# ===============================
# Customer Report
# ===============================
@report.route("/admin/reports/customers")
def customer_report():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            id,
            full_name,
            email,
            phone,
            city
        FROM customers
        ORDER BY full_name
    """)

    customers = cur.fetchall()

    cur.close()

    return render_template("admin/reports/customer_report.html", customers=customers)


# ===============================
# Sales Report
# ===============================
@report.route("/admin/reports/sales")
def sales_report():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            sales.id,
            customers.full_name,
            sales.invoice_no,
            sales.total_amount,
            sales.sale_date
        FROM sales
        INNER JOIN customers
            ON sales.customer_id = customers.id
        ORDER BY sales.id DESC
    """)

    sales_data = cur.fetchall()

    cur.close()

    return render_template("admin/reports/sales_report.html", sales=sales_data)


# ===============================
# Supplier Report
# ===============================
@report.route("/admin/reports/suppliers")
def supplier_report():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            id,
            supplier_name,
            email,
            phone,
            address
        FROM suppliers
        ORDER BY supplier_name
    """)

    suppliers = cur.fetchall()

    cur.close()

    return render_template("admin/reports/supplier_report.html", suppliers=suppliers)


# ===============================
# Purchase Report
# ===============================
@report.route("/admin/reports/purchases")
def purchase_report():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            purchases.id,
            suppliers.supplier_name,
            purchases.invoice_no,
            purchases.total_amount,
            purchases.purchase_date
        FROM purchases
        INNER JOIN suppliers
            ON purchases.supplier_id = suppliers.id
        ORDER BY purchases.id DESC
    """)

    purchases = cur.fetchall()

    cur.close()

    return render_template("admin/reports/purchase_report.html", purchases=purchases)


# ===============================
# Stock Report
# ===============================
@report.route("/admin/reports/stock")
def stock_report():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            products.id,
            products.product_name,
            categories.category_name,
            brands.brand_name,
            products.price,
            products.stock
        FROM products
        INNER JOIN categories
            ON products.category_id = categories.id
        INNER JOIN brands
            ON products.brand_id = brands.id
        ORDER BY products.product_name
    """)

    products = cur.fetchall()

    cur.close()

    return render_template("admin/reports/stock_report.html", products=products)
