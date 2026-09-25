from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db import mysql


purchase_return = Blueprint("purchase_return", __name__)


# ==========================================
# PURCHASE RETURN LIST
# ==========================================
@purchase_return.route("/admin/purchase-returns")
def purchase_return_list():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            purchase_returns.id,
            purchase_returns.invoice_no,
            suppliers.supplier_name,
            purchase_returns.return_amount,
            purchase_returns.reason,
            purchase_returns.return_date
        FROM purchase_returns
        INNER JOIN suppliers
            ON purchase_returns.supplier_id = suppliers.id
        ORDER BY purchase_returns.id DESC
    """)

    returns = cur.fetchall()

    cur.close()

    return render_template(
        "admin/purchase_returns/list.html",
        returns=returns
    )


# ==========================================
# ADD PURCHASE RETURN
# ==========================================
@purchase_return.route(
    "/admin/purchase-returns/add",
    methods=["GET", "POST"]
)
def add_purchase_return():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # Get Purchases
    cur.execute("""
        SELECT
            purchases.id,
            purchases.invoice_no,
            suppliers.supplier_name
        FROM purchases
        INNER JOIN suppliers
            ON purchases.supplier_id = suppliers.id
        ORDER BY purchases.id DESC
    """)

    purchases = cur.fetchall()

    if request.method == "POST":

        purchase_id = request.form.get("purchase_id")
        product_id = request.form.get("product_id")
        quantity_str = request.form.get("quantity", "").strip()
        reason = request.form.get("reason", "").strip()
        return_date = request.form.get("return_date")

        # Validation
        if not purchase_id or not product_id or not quantity_str:

            flash(
                "Please fill all required fields!",
                "danger"
            )

            cur.close()

            return redirect(
                url_for("purchase_return.add_purchase_return")
            )

        try:

            quantity = int(quantity_str)

        except ValueError:

            flash(
                "Invalid quantity!",
                "danger"
            )

            cur.close()

            return redirect(
                url_for("purchase_return.add_purchase_return")
            )

        if quantity <= 0:

            flash(
                "Quantity must be greater than zero!",
                "danger"
            )

            cur.close()

            return redirect(
                url_for("purchase_return.add_purchase_return")
            )

        # ==========================================
        # GET PURCHASE INFORMATION
        # ==========================================

        cur.execute("""
            SELECT
                supplier_id,
                invoice_no
            FROM purchases
            WHERE id=%s
        """, (purchase_id,))

        purchase = cur.fetchone()

        if not purchase:

            flash(
                "Purchase not found!",
                "danger"
            )

            cur.close()

            return redirect(
                url_for("purchase_return.add_purchase_return")
            )

        supplier_id = purchase[0]
        invoice_no = purchase[1]

        # ==========================================
        # GET PURCHASE PRODUCT
        # ==========================================

        cur.execute("""
            SELECT
                quantity,
                unit_price
            FROM purchase_items
            WHERE purchase_id=%s
            AND product_id=%s
        """, (
            purchase_id,
            product_id
        ))

        item = cur.fetchone()

        if not item:

            flash(
                "Product was not found in this purchase!",
                "danger"
            )

            cur.close()

            return redirect(
                url_for("purchase_return.add_purchase_return")
            )

        purchased_quantity = item[0]
        unit_price = item[1]

        # Check quantity

        if quantity > purchased_quantity:

            flash(
                f"Return quantity cannot exceed purchased quantity ({purchased_quantity}).",
                "danger"
            )

            cur.close()

            return redirect(
                url_for("purchase_return.add_purchase_return")
            )

        # Calculate Amount

        return_amount = quantity * float(unit_price)

        # ==========================================
        # CREATE PURCHASE RETURN
        # ==========================================

        cur.execute("""
            INSERT INTO purchase_returns
            (
                purchase_id,
                supplier_id,
                invoice_no,
                return_amount,
                reason,
                return_date
            )
            VALUES(%s,%s,%s,%s,%s,%s)
        """, (
            purchase_id,
            supplier_id,
            invoice_no,
            return_amount,
            reason,
            return_date
        ))

        return_id = cur.lastrowid

        # ==========================================
        # INSERT RETURN ITEM
        # ==========================================

        cur.execute("""
            INSERT INTO purchase_return_items
            (
                return_id,
                product_id,
                quantity,
                unit_price,
                total_price
            )
            VALUES(%s,%s,%s,%s,%s)
        """, (
            return_id,
            product_id,
            quantity,
            unit_price,
            return_amount
        ))

        # ==========================================
        # REDUCE PRODUCT STOCK
        # ==========================================

        cur.execute("""
            UPDATE products
            SET stock = stock - %s
            WHERE id=%s
        """, (
            quantity,
            product_id
        ))

        # ==========================================
        # STOCK HISTORY
        # ==========================================

        cur.execute("""
            INSERT INTO stock_history
            (
                product_id,
                transaction_type,
                quantity,
                remarks
            )
            VALUES(%s,%s,%s,%s)
        """, (
            product_id,
            "Purchase Return",
            quantity,
            f"Purchase Return Invoice : {invoice_no}"
        ))

        mysql.connection.commit()

        cur.close()

        flash(
            "Purchase Return Created Successfully!",
            "success"
        )

        return redirect(
            url_for("purchase_return.purchase_return_list")
        )

    cur.close()

    return render_template(
        "admin/purchase_returns/add.html",
        purchases=purchases
    )


# ==========================================
# API - GET PRODUCTS FROM PURCHASE
# ==========================================
@purchase_return.route(
    "/api/purchase/<int:id>/products"
)
def purchase_products(id):

    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            products.id,
            products.product_name,
            purchase_items.quantity,
            purchase_items.unit_price
        FROM purchase_items
        INNER JOIN products
            ON purchase_items.product_id = products.id
        WHERE purchase_items.purchase_id=%s
    """, (id,))

    products = cur.fetchall()

    cur.close()

    product_list = []

    for product in products:

        product_list.append({
            "id": product[0],
            "name": product[1],
            "quantity": product[2],
            "price": float(product[3])
        })

    return {
        "products": product_list
    }
