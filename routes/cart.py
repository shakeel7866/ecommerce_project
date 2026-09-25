from flask import send_file
from reportlab.pdfgen import canvas
import os


from flask import (
    Blueprint,
    session,
    redirect,
    url_for,
    flash,
    render_template,
    request,
)
from database.db import mysql

cart = Blueprint("cart", __name__)


# ==========================
# View Cart
# ==========================
@cart.route("/cart")
def view_cart():
    cart_items = session.get("cart", {})
    grand_total = 0

    for item in cart_items.values():
        grand_total += item["price"] * item["qty"]

    return render_template("cart.html", cart=cart_items, grand_total=grand_total)


# ==========================
# Add To Cart
# ==========================
@cart.route("/cart/add/<int:id>")
def add_to_cart(id):
    if "customer_id" not in session:
        flash("Please login first!", "warning")
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT
            id,
            product_name,
            price,
            image
        FROM products
        WHERE id=%s
        """,
        (id,),
    )

    product = cur.fetchone()
    cur.close()

    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("shop"))

    cart = session.get("cart", {})
    pid = str(product[0])

    if pid in cart:
        cart[pid]["qty"] += 1
    else:
        cart[pid] = {
            "id": product[0],
            "name": product[1],
            "price": float(product[2]),
            "image": product[3],
            "qty": 1,
        }

    session["cart"] = cart
    flash("Product added to cart.", "success")
    return redirect(request.referrer or url_for("shop"))


# ==========================
# Remove Item
# ==========================
@cart.route("/cart/remove/<int:id>")
def remove_cart(id):
    cart = session.get("cart", {})
    pid = str(id)

    if pid in cart:
        del cart[pid]

    session["cart"] = cart
    flash("Item removed.", "success")
    return redirect("/cart")


# ==========================
# Checkout Page
# ==========================
@cart.route("/checkout")
def checkout():
    if "customer_id" not in session:
        flash("Please login first!", "warning")
        return redirect(url_for("auth.login"))
    cart_items = session.get("cart", {})

    if not cart_items:
        flash("Your cart is empty.", "warning")
        return redirect("/cart")

    grand_total = 0
    for item in cart_items.values():
        grand_total += item["price"] * item["qty"]

    return render_template("checkout.html", cart=cart_items, grand_total=grand_total)


# ==========================
# Invoice Generation
# ==========================
@cart.route("/invoice/<int:order_id>")
def invoice(order_id):
    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT
            customer_name,
            customer_phone,
            total_amount
        FROM orders
        WHERE id=%s
        """,
        (order_id,),
    )

    order = cur.fetchone()

    if not order:
        cur.close()
        flash("Order not found.", "danger")
        return redirect("/cart")

    cur.execute(
        """
        SELECT
            products.product_name,
            order_items.quantity,
            order_items.unit_price,
            order_items.total_price
        FROM order_items
        INNER JOIN products
            ON order_items.product_id = products.id
        WHERE order_items.order_id=%s
        """,
        (order_id,),
    )

    items = cur.fetchall()
    cur.close()

    folder = "static/invoices"

    if not os.path.exists(folder):
        os.makedirs(folder)

    filename = f"invoice_{order_id}.pdf"
    filepath = os.path.join(folder, filename)

    pdf = canvas.Canvas(filepath)

    pdf.setTitle("Invoice")

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(180, 810, "TechStore")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(40, 780, f"Invoice No : {order_id}")
    pdf.drawString(40, 760, f"Customer : {order[0]}")
    pdf.drawString(40, 740, f"Phone : {order[1]}")

    y = 690

    pdf.line(40, 700, 560, 700)

    pdf.drawString(40, y, "Product")
    pdf.drawString(250, y, "Qty")
    pdf.drawString(330, y, "Price")
    pdf.drawString(430, y, "Total")

    y -= 25

    for item in items:
        pdf.drawString(40, y, str(item[0]))
        pdf.drawString(250, y, str(item[1]))
        pdf.drawString(330, y, str(item[2]))
        pdf.drawString(430, y, str(item[3]))
        y -= 20

    pdf.line(40, y, 560, y)

    y -= 30

    pdf.setFont("Helvetica-Bold", 12)

    pdf.drawString(330, y, "Grand Total")
    pdf.drawString(450, y, f"Rs. {order[2]}")

    pdf.save()

    return send_file(filepath, as_attachment=False)


# ==========================
# Place Order
# ==========================
@cart.route("/place-order", methods=["POST"])
def place_order():
    if "cart" not in session:
        flash("Cart is Empty!", "warning")
        return redirect("/cart")

    customer_name = request.form["customer_name"]
    customer_phone = request.form["customer_phone"]
    address = request.form["address"]
    city = request.form["city"]
    province = request.form["province"]
    payment_method = request.form["payment_method"]
    delivery_method = request.form["delivery_method"]

    print("=" * 50)
    print(request.form)
    print("=" * 50)
    cart_items = session["cart"]

    grand_total = 0
    for item in cart_items.values():
        grand_total += item["price"] * item["qty"]

    cur = mysql.connection.cursor()

    # Save Order
    cur.execute(
        """
    INSERT INTO orders
    (
        customer_id,
        customer_name,
        customer_phone,
        address,
        city,
        province,
        payment_method,
        delivery_method,
        total_amount,
        order_status
    )
    VALUES
    (
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        'Pending'
    )
    """,
        (
            session["customer_id"],
            customer_name,
            customer_phone,
            address,
            city,
            province,
            payment_method,
            delivery_method,
            grand_total,
        ),
    )

    mysql.connection.commit()
    order_id = cur.lastrowid

    # Save Order Items
    for item in cart_items.values():
        cur.execute(
            """
            INSERT INTO order_items
            (
                order_id,
                product_id,
                quantity,
                unit_price,
                total_price
            )
            VALUES
            (
                %s, %s, %s, %s, %s
            )
            """,
            (
                order_id,
                item["id"],
                item["qty"],
                item["price"],
                item["price"] * item["qty"],
            ),
        )

        # Reduce Product Stock
        cur.execute(
            """
            UPDATE products
            SET stock = stock - %s
            WHERE id = %s
            """,
            (
                item["qty"],
                item["id"],
            ),
        )

    mysql.connection.commit()
    cur.close()

    session.pop("cart", None)

    flash("Order Placed Successfully!", "success")

    return render_template(
        "order_success.html",
        order_id=order_id,
        customer_name=customer_name,
        grand_total=grand_total,
    )


# ==========================
# Increase Quantity
# ==========================
@cart.route("/cart/increase/<int:id>")
def increase_cart(id):

    cart = session.get("cart", {})
    pid = str(id)

    if pid in cart:
        cart[pid]["qty"] += 1

    session["cart"] = cart

    return redirect("/cart")


# ==========================
# Decrease Quantity
# ==========================
@cart.route("/cart/decrease/<int:id>")
def decrease_cart(id):

    cart = session.get("cart", {})
    pid = str(id)

    if pid in cart:

        if cart[pid]["qty"] > 1:
            cart[pid]["qty"] -= 1
        else:
            del cart[pid]

    session["cart"] = cart

    return redirect("/cart")


# ==========================
# My Orders
# ==========================
@cart.route("/my-orders")
def my_orders():

    if "customer_id" not in session:
        flash("Please login first!", "warning")
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT
            id,
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
    print("Customer ID:", session["customer_id"])
    print("Orders:", orders)

    cur.close()

    return render_template(
        "my_orders.html",
        orders=orders,
    )
