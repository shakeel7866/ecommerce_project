from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.db import mysql

brand = Blueprint("brand", __name__)


# =========================
# Brand List
# =========================
@brand.route("/admin/brands")
def brand_list():

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM brands ORDER BY id DESC")

    brands = cur.fetchall()

    cur.close()

    return render_template("admin/brands/list.html", brands=brands)


# =========================
# Add Brand
# =========================
@brand.route("/admin/brands/add", methods=["GET", "POST"])
def add_brand():

    if request.method == "POST":

        brand_name = request.form["brand_name"]

        cur = mysql.connection.cursor()

        # Duplicate Check
        cur.execute("SELECT id FROM brands WHERE brand_name=%s", (brand_name,))

        if cur.fetchone():

            flash("Brand already exists!", "danger")

            cur.close()

            return redirect(url_for("brand.add_brand"))

        # Insert Brand
        cur.execute(
            """
            INSERT INTO brands (brand_name)
            VALUES (%s)
            """,
            (brand_name,),
        )

        mysql.connection.commit()

        cur.close()

        flash("Brand Added Successfully!", "success")

        return redirect(url_for("brand.brand_list"))

    return render_template("admin/brands/add.html")


# =========================
# Edit Brand
# =========================
@brand.route("/admin/brands/edit/<int:id>", methods=["GET", "POST"])
def edit_brand(id):

    cur = mysql.connection.cursor()

    if request.method == "POST":

        brand_name = request.form["brand_name"].strip()

        # Duplicate Check
        cur.execute(
            "SELECT id FROM brands WHERE brand_name=%s AND id!=%s", (brand_name, id)
        )

        if cur.fetchone():

            flash("Brand already exists!", "danger")
            cur.close()

            return redirect(url_for("brand.edit_brand", id=id))

        # Update Brand
        cur.execute(
            """
            UPDATE brands
            SET brand_name=%s
            WHERE id=%s
            """,
            (brand_name, id),
        )

        mysql.connection.commit()
        cur.close()

        flash("Brand Updated Successfully!", "success")

        return redirect(url_for("brand.brand_list"))

    # Get existing brand
    cur.execute("SELECT * FROM brands WHERE id=%s", (id,))

    brand_data = cur.fetchone()

    cur.close()

    if not brand_data:
        flash("Brand not found!", "danger")
        return redirect(url_for("brand.brand_list"))

    return render_template("admin/brands/edit.html", brand=brand_data)


# =========================
# Delete Brand
# =========================
@brand.route("/admin/brands/delete/<int:id>")
def delete_brand(id):

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM brands WHERE id=%s", (id,))

    mysql.connection.commit()

    cur.close()

    flash("Brand Deleted Successfully!", "success")

    return redirect(url_for("brand.brand_list"))
