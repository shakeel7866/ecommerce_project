from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db import mysql

order = Blueprint("order", __name__)


@order.route("/admin/orders")
def order_list():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    search = request.args.get("search", "")

    cur = mysql.connection.cursor()

    if search:

        cur.execute(
            """
            SELECT
                id,
                customer_name,
                total_amount,
                order_status,
                created_at
            FROM orders
            WHERE customer_name LIKE %s
            ORDER BY id DESC
        """,
            ("%" + search + "%",),
        )

    else:

        cur.execute("""
            SELECT
                id,
                customer_name,
                total_amount,
                order_status,
                created_at
            FROM orders
            ORDER BY id DESC
        """)

    orders = cur.fetchall()

    cur.close()

    return render_template(
        "admin/dashboard/orders/index.html", orders=orders, search=search
    )


@order.route("/admin/orders/add", methods=["GET", "POST"])
def add_order():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":

        customer_name = request.form["customer_name"]
        customer_phone = request.form["customer_phone"]
        total_amount = request.form["total_amount"]
        order_status = request.form["order_status"]

        # Get customer_id if available (for customer orders)
        customer_id = request.form.get("customer_id", None)

        cur = mysql.connection.cursor()

        if customer_id:
            cur.execute(
                """
                INSERT INTO orders
                (customer_name, customer_phone, total_amount, order_status, customer_id)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (
                    customer_name,
                    customer_phone,
                    total_amount,
                    order_status,
                    customer_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO orders
                (customer_name, customer_phone, total_amount, order_status)
                VALUES (%s, %s, %s, %s)
            """,
                (customer_name, customer_phone, total_amount, order_status),
            )

        mysql.connection.commit()
        cur.close()

        flash("Order Added Successfully!", "success")

        return redirect(url_for("order.order_list"))

    return render_template("admin/dashboard/orders/add.html")


@order.route("/admin/orders/view/<int:id>")
def view_order(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT
            id,
            customer_name,
            customer_phone,
            address,
            city,
            province,
            payment_method,
            delivery_method,
            total_amount,
            order_status,
            created_at
        FROM orders
        WHERE id=%s
        """,
        (id,),
    )

    order_data = cur.fetchone()

    cur.close()

    return render_template("admin/dashboard/orders/view.html", order=order_data)


@order.route("/admin/orders/delete/<int:id>")
def delete_order(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM orders WHERE id=%s", (id,))

    mysql.connection.commit()

    cur.close()

    flash("Order Deleted Successfully!", "success")

    return redirect(url_for("order.order_list"))


@order.route("/admin/orders/edit/<int:id>", methods=["GET", "POST"])
def edit_order(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":

        customer_name = request.form["customer_name"]
        customer_phone = request.form["customer_phone"]
        total_amount = request.form["total_amount"]
        order_status = request.form["order_status"]

        cur.execute(
            """
            UPDATE orders
            SET
                customer_name=%s,
                customer_phone=%s,
                total_amount=%s,
                order_status=%s
            WHERE id=%s
        """,
            (customer_name, customer_phone, total_amount, order_status, id),
        )

        mysql.connection.commit()

        cur.close()

        flash("Order Updated Successfully!", "success")

        return redirect(url_for("order.order_list"))

    cur.execute(
        """
        SELECT
            id,
            customer_name,
            customer_phone,
            total_amount,
            order_status
        FROM orders
        WHERE id=%s
    """,
        (id,),
    )

    order_data = cur.fetchone()

    cur.close()

    return render_template("admin/dashboard/orders/edit.html", order=order_data)


@order.route("/admin/orders/invoice/<int:id>")
def invoice(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # Order
    cur.execute(
        """
        SELECT
            id,
            customer_name,
            customer_phone,
            total_amount,
            order_status,
            created_at
        FROM orders
        WHERE id=%s
    """,
        (id,),
    )

    order = cur.fetchone()

    if not order:
        cur.close()
        flash("Order not found.", "danger")
        return redirect(url_for("order.order_list"))

    # Items
    cur.execute(
        """
        SELECT
            products.product_name,
            order_items.quantity,
            order_items.unit_price,
            order_items.total_price
        FROM order_items
        INNER JOIN products
            ON products.id = order_items.product_id
        WHERE order_items.order_id=%s
    """,
        (id,),
    )

    items = cur.fetchall()

    cur.close()

    return render_template("admin/orders/invoice.html", order=order, items=items)


@order.route("/admin/orders/history")
def order_history():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            id,
            customer_name,
            customer_phone,
            total_amount,
            order_status,
            created_at
        FROM orders
        ORDER BY id DESC
        """)

    orders = cur.fetchall()

    cur.close()

    return render_template(
        "admin/orders/history.html",
        orders=orders,
    )


# ==========================
# My Orders (Customer)
# ==========================
@order.route("/my-orders")
def my_orders():

    if "customer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT
            id,
            customer_name,
            total_amount,
            order_status,
            created_at
        FROM orders
        WHERE customer_id=%s
        ORDER BY id DESC
        """,
        (session["customer_id"],),
    )

    orders = cur.fetchall()

    cur.close()

    return render_template(
        "orders/my_orders.html",
        orders=orders,
    )


# ==========================
# Customer Order Details
# ==========================
@order.route("/order-details/<int:order_id>")
def order_details(order_id):
    """View order details for a customer with items"""

    if "customer_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/login")

    cur = mysql.connection.cursor()

    # ==========================
    # Order Information
    # ==========================
    cur.execute(
        """
        SELECT
            id,
            customer_name,
            customer_phone,
            address,
            city,
            province,
            payment_method,
            delivery_method,
            total_amount,
            order_status,
            created_at
        FROM orders
        WHERE id=%s
        AND customer_id=%s
        """,
        (
            order_id,
            session["customer_id"],
        ),
    )

    order = cur.fetchone()

    if not order:
        cur.close()

        flash("Order not found.", "danger")
        return redirect("/my-orders")

    # ==========================
    # Order Items
    # ==========================
    cur.execute(
        """
        SELECT
            p.product_name,
            oi.quantity,
            oi.unit_price,
            oi.total_price
        FROM order_items oi
        INNER JOIN products p
            ON oi.product_id = p.id
        WHERE oi.order_id=%s
        ORDER BY oi.id ASC
        """,
        (order_id,),
    )

    items = cur.fetchall()

    cur.close()

    # ==========================
    # Render Order Details
    # ==========================
    return render_template(
        "orders/order_details.html",
        order=order,
        items=items,
    )


# ==========================
# Cancel Order (Customer)
# ==========================
@order.route("/cancel-order/<int:order_id>")
def cancel_order(order_id):
    """Cancel an order if it is still Pending."""

    if "customer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # Check order belongs to logged-in customer
    cur.execute(
        """
        SELECT order_status
        FROM orders
        WHERE id=%s
        AND customer_id=%s
        """,
        (
            order_id,
            session["customer_id"],
        ),
    )

    order = cur.fetchone()

    if not order:
        cur.close()

        flash("Order not found.", "danger")
        return redirect("/my-orders")

    # Only Pending orders can be cancelled
    if order[0] == "Pending":

        cur.execute(
            """
            UPDATE orders
            SET order_status='Cancelled'
            WHERE id=%s
            AND customer_id=%s
            """,
            (
                order_id,
                session["customer_id"],
            ),
        )

        mysql.connection.commit()
        cur.close()

        flash("Order cancelled successfully!", "success")

    else:

        cur.close()

        flash(
            "Only Pending orders can be cancelled.",
            "warning",
        )

    return redirect("/my-orders")


@order.route("/admin/orders/update-status/<int:id>", methods=["POST"])
def update_order_status(id):
    """Update order status by admin"""

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    new_status = request.form.get("order_status")

    # Validate status
    valid_statuses = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
    if new_status not in valid_statuses:
        flash("Invalid order status!", "danger")
        return redirect(url_for("order.order_list"))

    cur = mysql.connection.cursor()
    cur.execute("UPDATE orders SET order_status = %s WHERE id = %s", (new_status, id))
    mysql.connection.commit()
    cur.close()

    flash(f"Order #{id} status updated to {new_status}!", "success")
    return redirect(url_for("order.order_list"))
