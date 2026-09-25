from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from database.db import mysql
from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

purchase = Blueprint("purchase", __name__)


@purchase.route("/admin/purchases")
def purchase_list():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            purchases.id,
            suppliers.supplier_name,
            purchases.invoice_no,
            products.product_name,
            purchase_items.quantity,
            purchase_items.unit_price,
            purchases.total_amount,
            purchases.purchase_date
        FROM purchases
        INNER JOIN suppliers
            ON purchases.supplier_id = suppliers.id
        INNER JOIN purchase_items
            ON purchases.id = purchase_items.purchase_id
        INNER JOIN products
            ON purchase_items.product_id = products.id
        ORDER BY purchases.id DESC
    """)

    purchases = cur.fetchall()

    cur.close()

    return render_template("admin/purchases/list.html", purchases=purchases)


@purchase.route("/admin/purchases/add", methods=["GET", "POST"])
def add_purchase():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # Supplier Dropdown
    cur.execute("SELECT id, supplier_name FROM suppliers ORDER BY supplier_name")
    suppliers = cur.fetchall()

    # Product Dropdown
    cur.execute("""
        SELECT
            id,
            product_name
        FROM products
        ORDER BY product_name
    """)
    products = cur.fetchall()

    cur.close()

    if request.method == "POST":

        supplier_id = request.form.get("supplier_id")
        invoice_no = request.form.get("invoice_no")
        purchase_date = request.form.get("purchase_date")
        product_id = request.form.get("product_id")

        quantity = int(request.form.get("quantity"))
        unit_price = float(request.form.get("unit_price"))

        # Automatically calculate total
        total_amount = quantity * unit_price

        # Validation
        if not all([supplier_id, invoice_no, purchase_date]):
            flash("All fields are required!", "danger")
            return render_template(
                "admin/purchases/add.html", suppliers=suppliers, products=products
            )

        try:
            cur = mysql.connection.cursor()

            # Insert Purchase
            cur.execute(
                """
                INSERT INTO purchases
                (supplier_id, invoice_no, total_amount, purchase_date)
                VALUES (%s,%s,%s,%s)
            """,
                (supplier_id, invoice_no, total_amount, purchase_date),
            )
            # REMOVED: mysql.connection.commit() - Don't commit here

            purchase_id = cur.lastrowid

            total_price = quantity * unit_price

            # Insert Purchase Items
            cur.execute(
                """
                INSERT INTO purchase_items
                (purchase_id, product_id, quantity, unit_price, total_price)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (purchase_id, product_id, quantity, unit_price, total_price),
            )

            # Step 2.1: Update Product Stock
            cur.execute(
                """
                UPDATE products
                SET stock = stock + %s
                WHERE id = %s
            """,
                (quantity, product_id),
            )

            # Step 2.2: Add Stock History Entry
            cur.execute(
                """
                INSERT INTO stock_history
                (
                    product_id,
                    transaction_type,
                    quantity,
                    remarks
                )
                VALUES
                (%s,%s,%s,%s)
            """,
                (product_id, "Purchase", quantity, "Purchase Invoice : " + invoice_no),
            )

            # Step 2.3: Commit all changes
            mysql.connection.commit()

            cur.close()

            flash("Purchase Added Successfully!", "success")
            return redirect(url_for("purchase.purchase_list"))

        except Exception as e:
            mysql.connection.rollback()  # Rollback on error
            flash(f"Error adding purchase: {str(e)}", "danger")
            return render_template(
                "admin/purchases/add.html", suppliers=suppliers, products=products
            )

    # Final return - GET request
    return render_template(
        "admin/purchases/add.html", suppliers=suppliers, products=products
    )


@purchase.route("/admin/purchases/edit/<int:id>", methods=["GET", "POST"])
def edit_purchase(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # Supplier List
    cur.execute("SELECT id, supplier_name FROM suppliers ORDER BY supplier_name")
    suppliers = cur.fetchall()

    if request.method == "POST":

        supplier_id = request.form["supplier_id"]
        invoice_no = request.form["invoice_no"]
        purchase_date = request.form["purchase_date"]

        # Auto-calculate total_amount from purchase_items (source of truth)
        cur.execute(
            """
            SELECT COALESCE(SUM(total_price), 0)
            FROM purchase_items
            WHERE purchase_id=%s
            """,
            (id,),
        )

        total_amount = cur.fetchone()[0]

        cur.execute(
            """
            UPDATE purchases
            SET
                supplier_id=%s,
                invoice_no=%s,
                total_amount=%s,
                purchase_date=%s
            WHERE id=%s
        """,
            (supplier_id, invoice_no, total_amount, purchase_date, id),
        )

        mysql.connection.commit()

        flash("Purchase Updated Successfully!", "success")

        cur.close()

        return redirect(url_for("purchase.purchase_list"))

    cur.execute(
        """
        SELECT
            id,
            supplier_id,
            invoice_no,
            total_amount,
            purchase_date
        FROM purchases
        WHERE id=%s
    """,
        (id,),
    )

    purchase = cur.fetchone()

    cur.close()

    return render_template(
        "admin/purchases/edit.html", purchase=purchase, suppliers=suppliers
    )


@purchase.route("/admin/purchases/delete/<int:id>")
def delete_purchase(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    try:
        # Get invoice number
        cur.execute(
            """
            SELECT invoice_no
            FROM purchases
            WHERE id=%s
            """,
            (id,),
        )

        purchase_data = cur.fetchone()

        if not purchase_data:
            flash("Purchase not found!", "danger")
            cur.close()
            return redirect(url_for("purchase.purchase_list"))

        invoice_no = purchase_data[0]

        # Get purchase items
        cur.execute(
            """
            SELECT product_id, quantity
            FROM purchase_items
            WHERE purchase_id=%s
            """,
            (id,),
        )

        items = cur.fetchall()

        # Remove purchased quantity from stock
        for product_id, quantity in items:
            cur.execute(
                """
                UPDATE products
                SET stock = stock - %s
                WHERE id=%s
                """,
                (quantity, product_id),
            )

        # Delete stock history for this purchase
        cur.execute(
            """
            DELETE FROM stock_history
            WHERE transaction_type=%s
              AND remarks=%s
            """,
            ("Purchase", "Purchase Invoice : " + invoice_no),
        )

        # Delete purchase items
        cur.execute(
            """
            DELETE FROM purchase_items
            WHERE purchase_id=%s
            """,
            (id,),
        )

        # Delete purchase
        cur.execute(
            """
            DELETE FROM purchases
            WHERE id=%s
            """,
            (id,),
        )

        mysql.connection.commit()

        flash("Purchase Deleted Successfully and Stock Restored!", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting purchase: {str(e)}", "danger")

    finally:
        cur.close()

    return redirect(url_for("purchase.purchase_list"))


@purchase.route("/admin/purchases/invoice/<int:id>")
def purchase_invoice(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # Purchase Header
    cur.execute(
        """
        SELECT
            purchases.id,
            purchases.purchase_date,
            suppliers.supplier_name,
            purchases.total_amount
        FROM purchases
        INNER JOIN suppliers
        ON purchases.supplier_id = suppliers.id
        WHERE purchases.id=%s
    """,
        (id,),
    )

    purchase = cur.fetchone()

    # Purchase Items
    cur.execute(
        """
        SELECT
            products.product_name,
            purchase_items.quantity,
            purchase_items.unit_price,
            purchase_items.total_price
        FROM purchase_items
        INNER JOIN products
        ON purchase_items.product_id = products.id
        WHERE purchase_items.purchase_id=%s
    """,
        (id,),
    )

    items = cur.fetchall()
    cur.close()  # Close cursor after fetching data

    # Create invoices folder
    folder = "static/invoices"

    if not os.path.exists(folder):
        os.makedirs(folder)

    filename = f"purchase_{id}.pdf"
    filepath = os.path.join(folder, filename)

    # Create PDF
    pdf = canvas.Canvas(filepath, pagesize=letter)

    page_width, page_height = letter

    pdf.setTitle(f"Purchase Invoice - {purchase[0]}")

    # ==========================================
    # HEADER
    # ==========================================

    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(page_width / 2, 750, "TechStore")

    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(page_width / 2, 732, "Mobile & Electronics")

    pdf.drawCentredString(page_width / 2, 716, "Hyderabad, Sindh, Pakistan")

    pdf.drawCentredString(page_width / 2, 700, "Phone: +92-300-0339862")

    # ==========================================
    # INVOICE TITLE
    # ==========================================

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(45, 660, "PURCHASE INVOICE")

    pdf.line(45, 650, 567, 650)

    # ==========================================
    # INVOICE INFORMATION
    # ==========================================

    pdf.setFont("Helvetica-Bold", 11)

    pdf.drawString(45, 625, "Invoice No:")
    pdf.drawString(45, 602, "Supplier:")
    pdf.drawString(45, 579, "Purchase Date:")

    pdf.setFont("Helvetica", 11)

    pdf.drawString(130, 625, str(purchase[0]))
    pdf.drawString(130, 602, str(purchase[2]))
    pdf.drawString(130, 579, str(purchase[1]))

    # ==========================================
    # TABLE HEADER
    # ==========================================

    table_top = 535
    row_height = 30

    pdf.setFont("Helvetica-Bold", 11)

    # Header background
    pdf.setFillColorRGB(0.93, 0.93, 0.93)
    pdf.rect(45, table_top - row_height, 522, row_height, fill=1, stroke=0)

    pdf.setFillColorRGB(0, 0, 0)

    pdf.drawString(55, table_top - 20, "Product")
    pdf.drawString(330, table_top - 20, "Qty")
    pdf.drawString(395, table_top - 20, "Unit Price")
    pdf.drawString(500, table_top - 20, "Total")

    # Header borders
    pdf.rect(45, table_top - row_height, 522, row_height, fill=0, stroke=1)

    pdf.line(320, table_top, 320, table_top - row_height)
    pdf.line(385, table_top, 385, table_top - row_height)
    pdf.line(490, table_top, 490, table_top - row_height)

    # ==========================================
    # PRODUCT ITEMS
    # ==========================================

    y = table_top - row_height

    pdf.setFont("Helvetica", 10)

    for item in items:

        y -= row_height

        product_name = str(item[0])
        quantity = str(item[1])
        unit_price = f"{float(item[2]):,.2f}"
        total_price = f"{float(item[3]):,.2f}"

        pdf.drawString(55, y + 10, product_name)

        pdf.drawString(330, y + 10, quantity)

        pdf.drawRightString(475, y + 10, unit_price)

        pdf.drawRightString(555, y + 10, total_price)

        # Row border
        pdf.line(45, y, 567, y)

    # ==========================================
    # TABLE OUTER BORDER
    # ==========================================

    table_bottom = y

    pdf.rect(45, table_bottom, 522, table_top - table_bottom, fill=0, stroke=1)

    # Vertical lines
    pdf.line(320, table_bottom, 320, table_top)
    pdf.line(385, table_bottom, 385, table_top)
    pdf.line(490, table_bottom, 490, table_top)

    # ==========================================
    # GRAND TOTAL
    # ==========================================

    y -= 35

    pdf.setFont("Helvetica-Bold", 13)

    pdf.drawRightString(490, y, "Grand Total:")

    pdf.drawRightString(555, y, f"Rs. {float(purchase[3]):,.2f}")

    # ==========================================
    # FOOTER
    # ==========================================

    pdf.line(45, 100, 567, 100)

    pdf.setFont("Helvetica", 10)

    pdf.drawCentredString(page_width / 2, 80, "Thank you for your business!")

    pdf.drawCentredString(page_width / 2, 64, "TechStore - Mobile & Electronics")

    pdf.save()

    return send_file(filepath, as_attachment=False)
