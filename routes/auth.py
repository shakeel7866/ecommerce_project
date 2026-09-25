from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
from database.db import mysql

auth = Blueprint("auth", __name__)
bcrypt = Bcrypt()


# ==========================
# Login
# ==========================
@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT id, first_name, email, password FROM users WHERE email=%s", (email,)
        )

        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user[3], password):

            # Admin/User Session
            session["user_id"] = user[0]
            session["user_name"] = user[1]

            # Customer Session
            session["customer_id"] = user[0]
            session["customer_name"] = user[1]

            # 🔍 DEBUG LINE - Temporary test
            print("DEBUG CUSTOMER ID:", session.get("customer_id"))

            flash("Login Successful!", "success")

            return redirect(url_for("dashboard.admin_dashboard"))

        else:
            flash("Invalid Email or Password!", "danger")

    return render_template("auth/login.html")


# ==========================
# Register
# ==========================
@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        username = request.form["username"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Password Match Check
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("auth.register"))

        cur = mysql.connection.cursor()

        # Check Email
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))

        if cur.fetchone():
            flash("Email already exists!", "danger")
            cur.close()
            return redirect(url_for("auth.register"))

        # Check Username
        cur.execute("SELECT id FROM users WHERE username=%s", (username,))

        if cur.fetchone():
            flash("Username already exists!", "danger")
            cur.close()
            return redirect(url_for("auth.register"))

        # Hash Password
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # Insert User
        cur.execute(
            """
            INSERT INTO users
            (first_name, last_name, username, email, phone, password)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (first_name, last_name, username, email, phone, hashed_password),
        )

        mysql.connection.commit()
        cur.close()

        flash("Registration Successful! Please Login.", "success")

        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


# ==========================
# Logout
# ==========================
@auth.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully!", "success")

    return redirect(url_for("auth.login"))
