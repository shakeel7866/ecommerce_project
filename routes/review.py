from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db import mysql

review = Blueprint("review", __name__)


@review.route("/product/<int:product_id>/reviews")
def product_reviews(product_id):

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT
            users.first_name,
            reviews.rating,
            reviews.review,
            reviews.created_at
        FROM reviews
        JOIN users
            ON reviews.customer_id = users.id
        JOIN products
            ON reviews.product_id = products.id
        WHERE reviews.product_id = %s
          AND products.status = 1
        ORDER BY reviews.id DESC
    """,
        (product_id,),
    )

    reviews = cur.fetchall()

    cur.close()

    return render_template(
        "reviews/product_reviews.html", reviews=reviews, product_id=product_id
    )


@review.route("/product/<int:product_id>/review", methods=["GET", "POST"])
def add_review(product_id):

    if "customer_id" not in session:
        flash("Please Login First!", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":

        rating = request.form["rating"]
        review = request.form["review"]

        cur = mysql.connection.cursor()

        # Check duplicate review
        cur.execute(
            """
            SELECT id
            FROM reviews
            WHERE customer_id=%s
            AND product_id=%s
        """,
            (session["customer_id"], product_id),
        )

        if cur.fetchone():

            flash("You already reviewed this product.", "warning")

            cur.close()

            return redirect(f"/product/{product_id}/reviews")

        cur.execute(
            """
            INSERT INTO reviews
            (
                customer_id,
                product_id,
                rating,
                review
            )
            VALUES
            (
                %s,%s,%s,%s
            )
        """,
            (session["customer_id"], product_id, rating, review),
        )

        mysql.connection.commit()

        cur.close()

        flash("Review Added Successfully!", "success")

        return redirect(f"/product/{product_id}/reviews")

    return render_template("reviews/add_review.html", product_id=product_id)
