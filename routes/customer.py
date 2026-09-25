from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from database.db import mysql

customer = Blueprint("customer", __name__)


# ==========================
# Customer List (Admin)
# ==========================
@customer.route("/admin/customers")
def customer_list():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            id,
            full_name,
            email,
            phone,
            city
        FROM customers
        ORDER BY id DESC
    """)

    customers = cur.fetchall()

    cur.close()

    return render_template("admin/customers/list.html", customers=customers)


# ==========================
# Add Customer (Admin)  ✅ WITH VALIDATION
# ==========================
@customer.route("/admin/customers/add", methods=["GET", "POST"])
def add_customer():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        city = request.form["city"]
        address = request.form["address"]

        # ✅ Validation: Full Name required
        if not full_name:
            flash("Full Name is required!", "warning")
            return redirect(url_for("customer.add_customer"))

        # ✅ Validation: Email duplicate check
        if email:
            cur = mysql.connection.cursor()

            cur.execute("SELECT id FROM customers WHERE email=%s", (email,))

            if cur.fetchone():
                cur.close()
                flash("Email already exists!", "danger")
                return redirect(url_for("customer.add_customer"))

            cur.close()

        cur = mysql.connection.cursor()

        cur.execute(
            """
            INSERT INTO customers
            (full_name,email,phone,city,address)
            VALUES(%s,%s,%s,%s,%s)
        """,
            (full_name, email, phone, city, address),
        )

        mysql.connection.commit()
        cur.close()

        flash("Customer Added Successfully!", "success")

        return redirect(url_for("customer.customer_list"))

    return render_template("admin/customers/add.html")


# ==========================
# Edit Customer (Admin)
# ==========================
@customer.route("/admin/customers/edit/<int:id>", methods=["GET", "POST"])
def edit_customer(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        city = request.form["city"]
        address = request.form["address"]

        cur.execute(
            """
            UPDATE customers
            SET
                full_name=%s,
                email=%s,
                phone=%s,
                city=%s,
                address=%s
            WHERE id=%s
        """,
            (full_name, email, phone, city, address, id),
        )

        mysql.connection.commit()
        cur.close()

        flash("Customer Updated Successfully!", "success")

        return redirect(url_for("customer.customer_list"))

    cur.execute(
        """
        SELECT
            id,
            full_name,
            email,
            phone,
            city,
            address
        FROM customers
        WHERE id=%s
    """,
        (id,),
    )

    customer = cur.fetchone()

    cur.close()

    return render_template("admin/customers/edit.html", customer=customer)


# ==========================
# Delete Customer (Admin)
# ==========================
@customer.route("/admin/customers/delete/<int:id>", methods=["POST"])
def delete_customer(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    try:
        # Check whether customer has orders
        cur.execute(
            """
            SELECT COUNT(*)
            FROM orders
            WHERE customer_id=%s
            """,
            (id,),
        )

        order_count = cur.fetchone()[0]

        if order_count > 0:
            flash(
                "Customer cannot be deleted because orders are linked to this customer.",
                "warning",
            )
            return redirect(url_for("customer.customer_list"))

        cur.execute("DELETE FROM customers WHERE id=%s", (id,))

        mysql.connection.commit()

        flash("Customer Deleted Successfully!", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting customer: {str(e)}", "danger")

    finally:
        cur.close()

    return redirect(url_for("customer.customer_list"))


# ==========================
# Customer Dashboard
# ==========================
@customer.route("/dashboard")
def dashboard():

    if "customer_id" not in session:
        flash("Please login first!", "warning")
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    # Customer Info
    cur.execute(
        """
        SELECT
            full_name,
            email
        FROM customers
        WHERE id=%s
    """,
        (session["customer_id"],),
    )

    customer_data = cur.fetchone()

    # Total Orders
    cur.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE customer_id=%s
    """,
        (session["customer_id"],),
    )

    total_orders = cur.fetchone()[0]

    # Wishlist
    cur.execute(
        """
        SELECT COUNT(*)
        FROM wishlist
        WHERE customer_id=%s
    """,
        (session["customer_id"],),
    )

    wishlist = cur.fetchone()[0]

    # Total Spending
    cur.execute(
        """
        SELECT IFNULL(SUM(total_amount),0)
        FROM orders
        WHERE customer_id=%s
    """,
        (session["customer_id"],),
    )

    spending = cur.fetchone()[0]

    # Recent Orders
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
        LIMIT 5
    """,
        (session["customer_id"],),
    )

    recent_orders = cur.fetchall()

    cur.close()

    return render_template(
        "user/dashboard.html",
        customer=customer_data,
        total_orders=total_orders,
        wishlist=wishlist,
        spending=spending,
        recent_orders=recent_orders,
    )


# ==========================
# Customer Profile
# ==========================
@customer.route("/profile")
def profile():

    if "customer_id" not in session:
        flash("Please login first!", "warning")
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT
            id,
            first_name,
            email,
            phone
        FROM users
        WHERE id=%s
    """,
        (session["customer_id"],),
    )

    customer = cur.fetchone()

    cur.close()

    return render_template("user/profile.html", customer=customer)


# ==========================
# Edit Profile
# ==========================
@customer.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():

    if "customer_id" not in session:
        flash("Please login first!", "warning")
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        phone = request.form["phone"]

        cur.execute(
            """
            UPDATE users
            SET
                first_name=%s,
                email=%s,
                phone=%s
            WHERE id=%s
        """,
            (full_name, email, phone, session["customer_id"]),
        )

        mysql.connection.commit()

        session["customer_name"] = full_name

        flash("Profile Updated Successfully!", "success")

        cur.close()

        return redirect(url_for("customer.profile"))

    cur.execute(
        """
        SELECT
            id,
            first_name,
            email,
            phone
        FROM users
        WHERE id=%s
    """,
        (session["customer_id"],),
    )

    customer = cur.fetchone()

    cur.close()

    return render_template("user/edit_profile.html", customer=customer)


# ==========================
# Change Password
# ==========================
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()


@customer.route("/change-password", methods=["GET", "POST"])
def change_password():

    if "customer_id" not in session:
        flash("Please login first!", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("New Password and Confirm Password do not match.", "danger")
            return redirect(url_for("customer.change_password"))

        cur = mysql.connection.cursor()

        cur.execute(
            """
            SELECT password
            FROM users
            WHERE id=%s
        """,
            (session["customer_id"],),
        )

        user = cur.fetchone()

        if not user:
            cur.close()
            flash("User not found.", "danger")
            return redirect(url_for("customer.change_password"))

        if not bcrypt.check_password_hash(user[0], current_password):
            cur.close()
            flash("Current Password is incorrect.", "danger")
            return redirect(url_for("customer.change_password"))

        hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")

        cur.execute(
            """
            UPDATE users
            SET password=%s
            WHERE id=%s
        """,
            (hashed_password, session["customer_id"]),
        )

        mysql.connection.commit()
        cur.close()

        flash("Password Changed Successfully!", "success")

        return redirect(url_for("customer.profile"))

    return render_template("user/change_password.html")
