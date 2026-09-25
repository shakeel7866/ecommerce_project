from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db import mysql

sales_return = Blueprint("sales_return", __name__)


@sales_return.route("/admin/sales-returns")
def sales_return_list():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            sales_returns.id,
            sales_returns.invoice_no,
            customers.full_name,
            sales_returns.return_amount,
            sales_returns.reason,
            sales_returns.return_date
        FROM sales_returns
        INNER JOIN customers
            ON sales_returns.customer_id = customers.id
        ORDER BY sales_returns.id DESC
    """)

    returns = cur.fetchall()
    cur.close()

    return render_template("admin/sales_returns/list.html", returns=returns)


@sales_return.route("/admin/sales-returns/add", methods=["GET", "POST"])
def add_sales_return():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            sales.id,
            sales.invoice_no,
            customers.full_name
        FROM sales
        INNER JOIN customers
            ON sales.customer_id = customers.id
        ORDER BY sales.id DESC
    """)

    sales = cur.fetchall()

    if request.method == "POST":

        sale_id = request.form.get("sale_id")
        product_id = request.form.get("product_id")
        quantity_str = request.form.get("quantity", "").strip()
        reason = request.form.get("reason", "").strip()
        return_date = request.form.get("return_date")

        if not sale_id or not product_id or not quantity_str:
            flash("Please fill all required fields!", "danger")
            cur.close()
            return redirect(url_for("sales_return.add_sales_return"))

        try:
            quantity = int(quantity_str)
        except ValueError:
            flash("Invalid quantity!", "danger")
            cur.close()
            return redirect(url_for("sales_return.add_sales_return"))

        if quantity <= 0:
            flash("Quantity must be greater than zero!", "danger")
            cur.close()
            return redirect(url_for("sales_return.add_sales_return"))

        cur.execute(
            """
            SELECT
                sales.customer_id,
                sales.invoice_no
            FROM sales
            WHERE sales.id=%s
        """,
            (sale_id,),
        )

        sale = cur.fetchone()

        if not sale:
            flash("Sale not found!", "danger")
            cur.close()
            return redirect(url_for("sales_return.add_sales_return"))

        customer_id = sale[0]
        invoice_no = sale[1]

        cur.execute(
            """
            SELECT
                quantity,
                unit_price
            FROM sale_items
            WHERE sale_id=%s AND product_id=%s
        """,
            (sale_id, product_id),
        )

        item = cur.fetchone()

        if not item:
            flash("Product was not found in this sale!", "danger")
            cur.close()
            return redirect(url_for("sales_return.add_sales_return"))

        sold_quantity = item[0]
        unit_price = item[1]

        if quantity > sold_quantity:
            flash(
                f"Return quantity cannot exceed sold quantity ({sold_quantity}).",
                "danger",
            )
            cur.close()
            return redirect(url_for("sales_return.add_sales_return"))

        return_amount = quantity * float(unit_price)

        cur.execute(
            """
            INSERT INTO sales_returns
            (
                sale_id,
                customer_id,
                invoice_no,
                return_amount,
                reason,
                return_date
            )
            VALUES(%s,%s,%s,%s,%s,%s)
        """,
            (sale_id, customer_id, invoice_no, return_amount, reason, return_date),
        )

        return_id = cur.lastrowid

        cur.execute(
            """
            INSERT INTO sales_return_items
            (
                return_id,
                product_id,
                quantity,
                unit_price,
                total_price
            )
            VALUES(%s,%s,%s,%s,%s)
        """,
            (return_id, product_id, quantity, unit_price, return_amount),
        )

        # Return stock back to inventory
        cur.execute(
            """
            UPDATE products
            SET stock = stock + %s
            WHERE id=%s
        """,
            (quantity, product_id),
        )
        # Add Stock History

        cur.execute(
            """
            INSERT INTO stock_history
            (
                product_id,
                transaction_type,
                quantity,
                remarks
            )
            VALUES (%s, %s, %s, %s)
        """,
            (
                product_id,
                "Sales Return",
                quantity,
                "Sales Return Invoice : " + invoice_no,
            ),
        )
        mysql.connection.commit()
        cur.close()

        flash("Sales Return Created Successfully!", "success")

        return redirect(url_for("sales_return.sales_return_list"))

    cur.close()

    return render_template("admin/sales_returns/add.html", sales=sales)


@sales_return.route("/api/sale/<int:id>/products")
def sale_products(id):

    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT
            products.id,
            products.product_name,
            sale_items.quantity,
            sale_items.unit_price
        FROM sale_items
        INNER JOIN products
            ON sale_items.product_id = products.id
        WHERE sale_items.sale_id=%s
    """,
        (id,),
    )

    products = cur.fetchall()

    cur.close()

    product_list = []

    for product in products:

        product_list.append(
            {
                "id": product[0],
                "name": product[1],
                "quantity": product[2],
                "price": float(product[3]),
            }
        )

    return {"products": product_list}
