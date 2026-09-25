from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    flash,
    request,
)  # Added 'request' here
from database.db import mysql

user = Blueprint("user", __name__)


@user.route("/dashboard")
def dashboard():

    if "customer_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/login")

    return render_template("user/dashboard.html")


@user.route("/profile")
def profile():

    if "customer_id" not in session:
        return redirect("/login")

    from database.db import mysql

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT
            id,
            full_name,
            email,
            phone
        FROM customers
        WHERE id=%s
        """,
        (session["customer_id"],),
    )

    customer = cur.fetchone()

    cur.close()

    return render_template(
        "user/profile.html",
        customer=customer,
    )


@user.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():

    if "customer_id" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        phone = request.form["phone"]

        cur.execute(
            """
            UPDATE customers
            SET
                full_name=%s,
                email=%s,
                phone=%s
            WHERE id=%s
            """,
            (
                full_name,
                email,
                phone,
                session["customer_id"],
            ),
        )

        mysql.connection.commit()

        session["customer_name"] = full_name

        flash("Profile Updated Successfully.", "success")

        cur.close()

        return redirect("/profile")

    cur.execute(
        """
        SELECT
            id,
            full_name,
            email,
            phone
        FROM customers
        WHERE id=%s
        """,
        (session["customer_id"],),
    )

    customer = cur.fetchone()

    cur.close()

    return render_template(
        "user/edit_profile.html",
        customer=customer,
    )


@user.route("/change-password", methods=["GET", "POST"])
def change_password():

    if "customer_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("New passwords do not match!", "danger")
            return redirect("/change-password")

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT password FROM customers WHERE id=%s",
            (session["customer_id"],),
        )

        customer = cur.fetchone()

        if not customer:
            cur.close()
            flash("Customer not found.", "danger")
            return redirect("/change-password")

        # Agar passwords plain text hain
        if customer[0] != old_password:
            cur.close()
            flash("Old password is incorrect.", "danger")
            return redirect("/change-password")

        cur.execute(
            "UPDATE customers SET password=%s WHERE id=%s",
            (new_password, session["customer_id"]),
        )

        mysql.connection.commit()
        cur.close()

        flash("Password changed successfully.", "success")

        return redirect("/profile")

    return render_template("user/change_password.html")
