from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.db import mysql

category = Blueprint("category", __name__)


# =========================
# Category List
# =========================
@category.route("/admin/categories")
def category_list():

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories ORDER BY id DESC")
    categories = cur.fetchall()
    cur.close()

    return render_template("admin/categories/list.html", categories=categories)


# =========================
# Add Category
# =========================
@category.route("/admin/categories/add", methods=["GET", "POST"])
def add_category():

    if request.method == "POST":

        category_name = request.form["category_name"]
        description = request.form["description"]

        cur = mysql.connection.cursor()

        cur.execute(
            """
            INSERT INTO categories
            (category_name, description)
            VALUES (%s, %s)
            """,
            (category_name, description),
        )

        mysql.connection.commit()
        cur.close()

        flash("Category Added Successfully!", "success")
        return redirect(url_for("category.category_list"))

    return render_template("admin/categories/add.html")


# =========================
# Edit Category
# =========================
@category.route("/admin/categories/edit/<int:id>", methods=["GET", "POST"])
def edit_category(id):

    cur = mysql.connection.cursor()

    if request.method == "POST":

        category_name = request.form["category_name"]
        description = request.form["description"]

        cur.execute(
            """
            UPDATE categories
            SET category_name=%s,
                description=%s
            WHERE id=%s
            """,
            (category_name, description, id),
        )

        mysql.connection.commit()
        cur.close()

        flash("Category Updated Successfully!", "success")

        return redirect(url_for("category.category_list"))

    cur.execute("SELECT * FROM categories WHERE id=%s", (id,))

    category_data = cur.fetchone()
    cur.close()

    return render_template("admin/categories/edit.html", category=category_data)


# =========================
# Delete Category
# =========================
@category.route("/admin/categories/delete/<int:id>")
def delete_category(id):

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM categories WHERE id=%s", (id,))

    mysql.connection.commit()
    cur.close()

    flash("Category Deleted Successfully!", "success")

    return redirect(url_for("category.category_list"))
