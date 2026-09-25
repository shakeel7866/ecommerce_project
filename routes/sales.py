from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_file,
)
from database.db import mysql
import os
from reportlab.pdfgen import canvas

sales = Blueprint("sales", __name__)


@sales.route("/admin/sales")
def sales_list():

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

    return render_template("admin/sales/list.html", sales=sales_data)


@sales.route("/admin/sales/add", methods=["GET", "POST"])
def add_sale():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # Customers
    cur.execute("SELECT id, full_name FROM customers ORDER BY full_name")
    customers = cur.fetchall()

    # Products
    cur.execute("""
        SELECT
            id,
            product_name,
            price,
            stock
        FROM products
        WHERE status=1
        ORDER BY product_name
    """)
    products = cur.fetchall()

    if request.method == "POST":

        customer_id = request.form.get("customer_id")
        invoice_no = request.form.get("invoice_no")
        total_amount = request.form.get("total_amount")
        sale_date = request.form.get("sale_date")

        # FIX: Properly handle None values with validation
        # Get all form values with proper error handling
        customer_id = request.form.get("customer_id")
        invoice_no = request.form.get("invoice_no")
        total_amount = request.form.get("total_amount")
        sale_date = request.form.get("sale_date")
        product_id = request.form.get("product_id")

        # Validate required fields
        if not customer_id:
            flash("Customer is required", "danger")
            cur.close()
            return render_template(
                "admin/sales/add.html", customers=customers, products=products
            )

        if not invoice_no:
            flash("Invoice number is required", "danger")
            cur.close()
            return render_template(
                "admin/sales/add.html", customers=customers, products=products
            )

        if not product_id:
            flash("Product is required", "danger")
            cur.close()
            return render_template(
                "admin/sales/add.html", customers=customers, products=products
            )

        # FIX: Handle quantity with proper validation
        quantity_str = request.form.get("quantity", "").strip()
        if not quantity_str:
            flash("Quantity is required", "danger")
            cur.close()
            return render_template(
                "admin/sales/add.html", customers=customers, products=products
            )

        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                flash("Quantity must be greater than 0", "danger")
                cur.close()
                return render_template(
                    "admin/sales/add.html", customers=customers, products=products
                )
        except ValueError:
            flash("Quantity must be a valid number", "danger")
            cur.close()
            return render_template(
                "admin/sales/add.html", customers=customers, products=products
            )

        # FIX: Handle unit_price with proper validation
        unit_price_str = request.form.get("unit_price", "").strip()
        if not unit_price_str:
            flash("Unit price is required", "danger")
            cur.close()
            return render_template(
                "admin/sales/add.html", customers=customers, products=products
            )

        try:
            unit_price = float(unit_price_str)
            if unit_price < 0:
                flash("Unit price cannot be negative", "danger")
                cur.close()
                return render_template(
                    "admin/sales/add.html", customers=customers, products=products
                )
        except ValueError:
            flash("Unit price must be a valid number", "danger")
            cur.close()
            return render_template(
                "admin/sales/add.html", customers=customers, products=products
            )

        # Stock Check
        cur.execute(
            """
            SELECT stock
            FROM products
            WHERE id=%s
        """,
            (product_id,),
        )

        stock = cur.fetchone()[0]

        # If stock is insufficient
        if quantity > stock:
            flash("Insufficient Stock!", "danger")
            cur.close()
            return render_template(
                "admin/sales/add.html", customers=customers, products=products
            )

        # Calculate total automatically
        total_amount = quantity * unit_price

        # Sale Save
        cur.execute(
            """
            INSERT INTO sales
            (customer_id,invoice_no,total_amount,sale_date)
            VALUES(%s,%s,%s,%s)
        """,
            (customer_id, invoice_no, total_amount, sale_date),
        )

        # Sale ID
        sale_id = cur.lastrowid

        # sale_items
        total_price = quantity * unit_price

        cur.execute(
            """
            INSERT INTO sale_items
            (sale_id,product_id,quantity,unit_price,total_price)
            VALUES(%s,%s,%s,%s,%s)
        """,
            (sale_id, product_id, quantity, unit_price, total_price),
        )

        # Stock Minus
        cur.execute(
            """
            UPDATE products
            SET stock = stock - %s
            WHERE id=%s
        """,
            (quantity, product_id),
        )

        # Commit
        mysql.connection.commit()

        cur.close()

        flash("Invoice Created Successfully!", "success")

        return redirect(url_for("sales.sales_list"))

    cur.close()

    return render_template(
        "admin/sales/add.html", customers=customers, products=products
    )


@sales.route("/admin/sales/edit/<int:id>", methods=["GET", "POST"])
def edit_sale(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # Customer List
    cur.execute("SELECT id, full_name FROM customers ORDER BY full_name")
    customers = cur.fetchall()

    if request.method == "POST":

        customer_id = request.form["customer_id"]
        invoice_no = request.form["invoice_no"]
        sale_date = request.form["sale_date"]

        cur.execute(
            """
            SELECT COALESCE(SUM(total_price), 0)
            FROM sale_items
            WHERE sale_id=%s
            """,
            (id,),
        )

        total_amount = cur.fetchone()[0]

        cur.execute(
            """
            UPDATE sales
            SET
                customer_id=%s,
                invoice_no=%s,
                total_amount=%s,
                sale_date=%s
            WHERE id=%s
        """,
            (customer_id, invoice_no, total_amount, sale_date, id),
        )

        mysql.connection.commit()

        flash("Sale Updated Successfully!", "success")

        cur.close()

        return redirect(url_for("sales.sales_list"))

    cur.execute(
        """
        SELECT
            id,
            customer_id,
            invoice_no,
            total_amount,
            sale_date
        FROM sales
        WHERE id=%s
    """,
        (id,),
    )

    sale = cur.fetchone()

    cur.close()

    return render_template("admin/sales/edit.html", sale=sale, customers=customers)


@sales.route("/admin/sales/delete/<int:id>")
def delete_sale(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    try:
        # Get sold items before deleting the sale
        cur.execute(
            """
            SELECT product_id, quantity
            FROM sale_items
            WHERE sale_id=%s
            """,
            (id,),
        )

        items = cur.fetchall()

        # Restore stock
        for product_id, quantity in items:
            cur.execute(
                """
                UPDATE products
                SET stock = stock + %s
                WHERE id=%s
                """,
                (quantity, product_id),
            )

        # Delete sale items
        cur.execute(
            """
            DELETE FROM sale_items
            WHERE sale_id=%s
            """,
            (id,),
        )

        # Delete sale
        cur.execute(
            """
            DELETE FROM sales
            WHERE id=%s
            """,
            (id,),
        )

        mysql.connection.commit()

        flash("Sale Deleted Successfully and Stock Restored!", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting sale: {str(e)}", "danger")

    finally:
        cur.close()

    return redirect(url_for("sales.sales_list"))


@sales.route("/api/product/<int:id>")
def product_info(id):

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT
            id,
            product_name,
            price,
            stock
        FROM products
        WHERE id=%s
    """,
        (id,),
    )

    product = cur.fetchone()

    cur.close()

    if product:

        return jsonify(
            {
                "id": product[0],
                "name": product[1],
                "price": float(product[2]),
                "stock": product[3],
            }
        )

    return jsonify({})


# =========================
# Sales Invoice PDF
# =========================
@sales.route("/admin/sales/invoice/<int:id>")
def sales_invoice(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # Sale Header
    cur.execute(
        """
        SELECT
            sales.invoice_no,
            sales.sale_date,
            customers.full_name,
            sales.total_amount
        FROM sales
        INNER JOIN customers
            ON sales.customer_id = customers.id
        WHERE sales.id=%s
        """,
        (id,),
    )

    sale = cur.fetchone()

    # Sale not found
    if not sale:
        cur.close()
        flash("Sale Invoice not found!", "danger")
        return redirect(url_for("sales.sales_list"))

    # Sale Items
    cur.execute(
        """
        SELECT
            products.product_name,
            sale_items.quantity,
            sale_items.unit_price,
            sale_items.total_price
        FROM sale_items
        INNER JOIN products
            ON sale_items.product_id = products.id
        WHERE sale_items.sale_id=%s
        """,
        (id,),
    )

    items = cur.fetchall()

    cur.close()

    # Create invoices folder
    folder = "static/invoices"

    if not os.path.exists(folder):
        os.makedirs(folder)

    filename = f"sale_{id}.pdf"
    filepath = os.path.join(folder, filename)

    # Create PDF
    pdf = canvas.Canvas(filepath)

    pdf.setTitle("Sales Invoice")

    # =========================
    # Header
    # =========================

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(220, 810, "TechStore")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(185, 790, "Mobile & Electronics")
    pdf.drawString(175, 775, "Hyderabad, Sindh, Pakistan")
    pdf.drawString(200, 760, "Phone: +92-300-0339862")

    pdf.line(40, 745, 560, 745)

    # =========================
    # Invoice Information
    # =========================

    pdf.setFont("Helvetica", 11)

    pdf.drawString(40, 720, f"Invoice No : {sale[0]}")

    pdf.drawString(40, 700, f"Customer : {sale[2]}")

    pdf.drawString(40, 680, f"Date : {sale[1]}")

    # =========================
    # Table Header
    # =========================

    y = 640

    pdf.line(40, 655, 560, 655)
    pdf.line(40, 625, 560, 625)

    pdf.setFont("Helvetica-Bold", 11)

    pdf.drawString(50, y, "Product")
    pdf.drawString(270, y, "Qty")
    pdf.drawString(340, y, "Price")
    pdf.drawString(450, y, "Total")

    # Vertical lines
    pdf.line(40, 655, 40, 625)
    pdf.line(250, 655, 250, 625)
    pdf.line(320, 655, 320, 625)
    pdf.line(430, 655, 430, 625)
    pdf.line(560, 655, 560, 625)

    # =========================
    # Items
    # =========================

    y = 605

    pdf.setFont("Helvetica", 10)

    for item in items:

        # New page if too many products
        if y < 100:
            pdf.showPage()

            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, 800, "TechStore - Sales Invoice")

            y = 760
            pdf.setFont("Helvetica", 10)

        product_name = str(item[0])

        # Keep long product names inside table
        if len(product_name) > 30:
            product_name = product_name[:27] + "..."

        pdf.drawString(50, y, product_name)
        pdf.drawString(270, y, str(item[1]))
        pdf.drawString(340, y, f"Rs. {item[2]}")
        pdf.drawString(450, y, f"Rs. {item[3]}")

        y -= 20

    # =========================
    # Total
    # =========================

    pdf.line(40, y + 5, 560, y + 5)

    pdf.setFont("Helvetica-Bold", 12)

    pdf.drawString(330, y - 25, "Grand Total :")
    pdf.drawString(450, y - 25, f"Rs. {sale[3]}")

    # =========================
    # Footer
    # =========================

    pdf.setFont("Helvetica", 10)

    pdf.drawString(200, 60, "Thank you for shopping with TechStore!")

    pdf.save()

    return send_file(filepath, as_attachment=False, mimetype="application/pdf")
