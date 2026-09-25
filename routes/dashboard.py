from flask import Blueprint, render_template, session, redirect, url_for
from database.db import mysql

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/admin/dashboard")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # Products
    cur.execute("SELECT COUNT(*) FROM products")
    products = cur.fetchone()[0]

    # Categories
    cur.execute("SELECT COUNT(*) FROM categories")
    categories = cur.fetchone()[0]

    # Brands
    cur.execute("SELECT COUNT(*) FROM brands")
    brands = cur.fetchone()[0]

    # Customers
    cur.execute("SELECT COUNT(*) FROM customers")
    customers = cur.fetchone()[0]

    # Suppliers
    cur.execute("SELECT COUNT(*) FROM suppliers")
    suppliers = cur.fetchone()[0]

    # Purchases
    cur.execute("SELECT COUNT(*) FROM purchases")
    purchases = cur.fetchone()[0]

    # Sales
    cur.execute("SELECT COUNT(*) FROM sales")
    sales = cur.fetchone()[0]

    # Expenses
    cur.execute("SELECT COUNT(*) FROM expenses")
    expenses = cur.fetchone()[0]

    # Sales Returns
    cur.execute("SELECT COUNT(*) FROM sales_returns")
    sales_returns = cur.fetchone()[0]

    # Purchase Returns
    cur.execute("SELECT COUNT(*) FROM purchase_returns")
    purchase_returns = cur.fetchone()[0]

    # Users
    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    # Coupons
    cur.execute("SELECT COUNT(*) FROM coupons")
    coupons = cur.fetchone()[0]

    # Orders
    cur.execute("SELECT COUNT(*) FROM orders")
    orders = cur.fetchone()[0]

    # Order Status Counts
    cur.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE order_status = 'Pending'
    """)
    pending_orders = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE order_status = 'Processing'
    """)
    processing_orders = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE order_status = 'Shipped'
    """)
    shipped_orders = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE order_status = 'Delivered'
    """)
    delivered_orders = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE order_status = 'Cancelled'
    """)
    cancelled_orders = cur.fetchone()[0]

    # Contact Messages
    cur.execute("SELECT COUNT(*) FROM contact_messages")
    contact_messages_count = cur.fetchone()[0]

    # Total Purchase Amount
    cur.execute("SELECT IFNULL(SUM(total_amount),0) FROM purchases")
    purchase_amount = cur.fetchone()[0]

    # Total Sales Amount
    cur.execute("SELECT IFNULL(SUM(total_amount),0) FROM sales")
    sales_amount = cur.fetchone()[0]

    # Total Expense Amount
    cur.execute("SELECT IFNULL(SUM(amount),0) FROM expenses")
    expense_amount = cur.fetchone()[0]

    # Low Stock Products
    cur.execute("""
        SELECT
            product_name,
            stock
        FROM products
        WHERE stock <= 5
        ORDER BY stock ASC
        LIMIT 5
    """)
    low_stock = cur.fetchall()

    # Latest Sales
    cur.execute("""
        SELECT
            invoice_no,
            total_amount,
            sale_date
        FROM sales
        ORDER BY id DESC
        LIMIT 5
    """)
    latest_sales = cur.fetchall()

    # Recent Orders
    cur.execute("""
        SELECT
            id,
            customer_name,
            total_amount,
            order_status
        FROM orders
        ORDER BY id DESC
        LIMIT 5
    """)
    recent_orders = cur.fetchall()

    # Monthly Sales
    cur.execute("""
        SELECT
            MONTH(sale_date) AS month,
            SUM(total_amount) AS total
        FROM sales
        GROUP BY MONTH(sale_date)
        ORDER BY MONTH(sale_date)
    """)
    monthly_sales = cur.fetchall()

    # Monthly Purchases
    cur.execute("""
        SELECT
            MONTH(purchase_date) AS month,
            SUM(total_amount) AS total
        FROM purchases
        GROUP BY MONTH(purchase_date)
        ORDER BY MONTH(purchase_date)
    """)
    monthly_purchases = cur.fetchall()

    # Top 5 Products by Quantity Sold
    cur.execute("""
        SELECT
            products.product_name,
            SUM(sale_items.quantity) AS qty
        FROM sale_items
        INNER JOIN products ON products.id = sale_items.product_id
        GROUP BY sale_items.product_id
        ORDER BY qty DESC
        LIMIT 5
    """)
    top_products = cur.fetchall()

    cur.close()

    # Calculate Profit
    profit = float(sales_amount) - float(purchase_amount) - float(expense_amount)

    return render_template(
        "admin/dashboard/index.html",
        products=products,
        categories=categories,
        brands=brands,
        customers=customers,
        suppliers=suppliers,
        purchases=purchases,
        sales=sales,
        expenses=expenses,
        sales_returns=sales_returns,
        purchase_returns=purchase_returns,
        users=users,
        coupons=coupons,
        orders=orders,
        pending_orders=pending_orders,
        processing_orders=processing_orders,
        shipped_orders=shipped_orders,
        delivered_orders=delivered_orders,
        cancelled_orders=cancelled_orders,
        contact_messages_count=contact_messages_count,
        purchase_amount=purchase_amount,
        sales_amount=sales_amount,
        expense_amount=expense_amount,
        low_stock=low_stock,
        latest_sales=latest_sales,
        recent_orders=recent_orders,
        monthly_sales=monthly_sales,
        monthly_purchases=monthly_purchases,
        top_products=top_products,
        profit=profit,
    )
