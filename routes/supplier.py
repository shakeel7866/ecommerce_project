from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from database.db import mysql  # Add this import

supplier = Blueprint("supplier", __name__)


@supplier.route("/admin/suppliers")
def supplier_list():

    search = request.args.get("search", "")

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    if search:
        cur.execute(
            """
            SELECT
                id,
                supplier_name,
                email,
                phone,
                address
            FROM suppliers
            WHERE supplier_name LIKE %s
            ORDER BY id DESC
        """,
            ("%" + search + "%",),
        )
    else:
        cur.execute("""
            SELECT
                id,
                supplier_name,
                email,
                phone,
                address
            FROM suppliers
            ORDER BY id DESC
        """)

    suppliers = cur.fetchall()

    cur.close()

    return render_template(
        "admin/suppliers/list.html", suppliers=suppliers, search=search
    )


@supplier.route("/admin/suppliers/add", methods=["GET", "POST"])
def add_supplier():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":

        supplier_name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        address = request.form["address"]

        cur = mysql.connection.cursor()

        cur.execute(
            """
            INSERT INTO suppliers
            (supplier_name, email, phone, address)
            VALUES (%s, %s, %s, %s)
        """,
            (supplier_name, email, phone, address),
        )

        mysql.connection.commit()
        cur.close()

        flash("Supplier Added Successfully!", "success")

        return redirect(url_for("supplier.supplier_list"))

    return render_template("admin/suppliers/add.html")


@supplier.route("/admin/suppliers/edit/<int:id>", methods=["GET", "POST"])
def edit_supplier(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":

        supplier_name = request.form["supplier_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        address = request.form["address"]

        cur.execute(
            """
            UPDATE suppliers
            SET
                supplier_name=%s,
                email=%s,
                phone=%s,
                address=%s
            WHERE id=%s
        """,
            (supplier_name, email, phone, address, id),
        )

        mysql.connection.commit()
        cur.close()

        flash("Supplier Updated Successfully!", "success")

        return redirect(url_for("supplier.supplier_list"))

    cur.execute(
        """
        SELECT
            id,
            supplier_name,
            email,
            phone,
            address
        FROM suppliers
        WHERE id=%s
    """,
        (id,),
    )

    supplier = cur.fetchone()

    cur.close()

    return render_template("admin/suppliers/edit.html", supplier=supplier)


@supplier.route("/admin/suppliers/delete/<int:id>")
def delete_supplier(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM suppliers WHERE id=%s", (id,))

    mysql.connection.commit()
    cur.close()

    flash("Supplier Deleted Successfully!", "success")

    return redirect(url_for("supplier.supplier_list"))
