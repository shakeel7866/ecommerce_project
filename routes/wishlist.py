from flask import Blueprint, render_template, redirect, flash, session
from database.db import mysql

wishlist = Blueprint("wishlist", __name__)


# ===========================
# Wishlist Page
# ===========================
@wishlist.route("/wishlist")
def wishlist_page():

    # Check if user is logged in
    if "customer_id" not in session:
        flash("Please login to view your wishlist.", "warning")
        return redirect("/login")

    cur = mysql.connection.cursor()

    # Customer-wise wishlist products
    cur.execute(
        """
        SELECT
            wishlist.id AS wishlist_id,
            products.id AS product_id,
            products.product_name,
            products.price,
            products.image
        FROM wishlist
        INNER JOIN products
            ON wishlist.product_id = products.id
        WHERE wishlist.customer_id = %s
        ORDER BY wishlist.id DESC
        """,
        (session["customer_id"],),
    )

    products = cur.fetchall()
    cur.close()

    return render_template("wishlist.html", products=products)


# ===========================
# Add To Wishlist
# ===========================
@wishlist.route("/wishlist/add/<int:id>")
def add_wishlist(id):

    print("=" * 50)
    print("URL Product ID =", id)
    print("Session Customer =", session.get("customer_id"))
    print("=" * 50)

    # Check if user is logged in
    if "customer_id" not in session:
        flash("Please login to add items to wishlist.", "warning")
        return redirect("/login")

    cur = mysql.connection.cursor()

    # Check if product already exists in customer's wishlist
    cur.execute(
        """
        SELECT id 
        FROM wishlist 
        WHERE customer_id = %s 
        AND product_id = %s
        """,
        (session["customer_id"], id),
    )

    exists = cur.fetchone()

    if exists:
        flash("Product already in wishlist.", "warning")
        cur.close()
        return redirect("/shop")

    # FIXED: These lines were outside the function indentation
    print("=" * 40)
    print("Customer ID:", session["customer_id"])
    print("Product ID:", id)

    # Added the line above "INSERT" as requested
    print("Product ID =", id)

    cur.execute("SELECT id FROM products WHERE id=%s", (id,))

    print("Product Exists =", cur.fetchone())
    print("=" * 40)

    # Insert product with customer_id
    cur.execute(
        """
        INSERT INTO wishlist(customer_id, product_id)
        VALUES(%s, %s)
        """,
        (
            session["customer_id"],
            id,
        ),
    )

    mysql.connection.commit()
    cur.close()

    flash("Product added to wishlist.", "success")
    return redirect("/shop")


# ===========================
# Remove From Wishlist
# ===========================
@wishlist.route("/wishlist/remove/<int:id>")
def remove_wishlist(id):

    # Check if user is logged in
    if "customer_id" not in session:
        flash("Please login to remove items from wishlist.", "warning")
        return redirect("/login")

    cur = mysql.connection.cursor()

    # Delete only if it belongs to the logged-in customer
    cur.execute(
        "DELETE FROM wishlist WHERE id=%s AND customer_id=%s",
        (id, session["customer_id"]),
    )

    mysql.connection.commit()
    cur.close()

    flash("Product removed from wishlist.", "success")
    return redirect("/wishlist")
