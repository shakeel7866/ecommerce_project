from flask import Blueprint, render_template, request, redirect, flash, url_for, session
from database.db import mysql

coupon = Blueprint("coupon", __name__)


# =========================
# Coupon List (Admin)
# =========================
@coupon.route("/admin/coupons")
def coupon_list():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            id,
            coupon_code,
            discount_percent,
            minimum_amount,
            expiry_date,
            status
        FROM coupons
        ORDER BY id DESC
    """)

    coupons = cur.fetchall()
    cur.close()

    return render_template("admin/coupons/list.html", coupons=coupons)


# =========================
# Add Coupon (Admin)
# =========================
@coupon.route("/admin/coupons/add", methods=["GET", "POST"])
def add_coupon():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        coupon_code = request.form.get("coupon_code")
        discount_percent = request.form.get("discount_percent")
        minimum_amount = request.form.get("minimum_amount")
        expiry_date = request.form.get("expiry_date")
        status = request.form.get("status")

        # Validation: required fields
        # NOTE: status "0" is a valid value (inactive), so we DON'T
        # include it in `all()` check because "0" is truthy as a string
        # but it's safer to check explicitly.
        if not all([coupon_code, discount_percent, minimum_amount, expiry_date]):
            flash("All fields are required!", "danger")
            return render_template("admin/coupons/add.html")

        if status is None or status == "":
            flash("Status is required!", "danger")
            return render_template("admin/coupons/add.html")

        try:
            discount_percent = float(discount_percent)
            minimum_amount = float(minimum_amount)

            if discount_percent < 0 or discount_percent > 100:
                flash("Discount percent must be between 0 and 100!", "danger")
                return render_template("admin/coupons/add.html")

            if minimum_amount < 0:
                flash("Minimum amount cannot be negative!", "danger")
                return render_template("admin/coupons/add.html")

        except ValueError:
            flash("Invalid numeric values!", "danger")
            return render_template("admin/coupons/add.html")

        cur = mysql.connection.cursor()

        try:
            cur.execute(
                """
                INSERT INTO coupons
                (
                    coupon_code,
                    discount_percent,
                    minimum_amount,
                    expiry_date,
                    status
                )
                VALUES(%s, %s, %s, %s, %s)
                """,
                (coupon_code, discount_percent, minimum_amount, expiry_date, status),
            )

            mysql.connection.commit()

            flash("Coupon Added Successfully!", "success")
            return redirect(url_for("coupon.coupon_list"))

        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error adding coupon: {str(e)}", "danger")
            return render_template("admin/coupons/add.html")

        finally:
            cur.close()

    return render_template("admin/coupons/add.html")


# =========================
# Edit Coupon (Admin)
# =========================
@coupon.route("/admin/coupons/edit/<int:id>", methods=["GET", "POST"])
def edit_coupon(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    try:
        if request.method == "POST":

            coupon_code = request.form.get("coupon_code")
            discount_percent = request.form.get("discount_percent")
            minimum_amount = request.form.get("minimum_amount")
            expiry_date = request.form.get("expiry_date")
            status = request.form.get("status")

            # Validation: required fields
            if not all([coupon_code, discount_percent, minimum_amount, expiry_date]):
                flash("All fields are required!", "danger")
                return redirect(url_for("coupon.edit_coupon", id=id))

            if status is None or status == "":
                flash("Status is required!", "danger")
                return redirect(url_for("coupon.edit_coupon", id=id))

            try:
                discount_percent = float(discount_percent)
                minimum_amount = float(minimum_amount)

                if discount_percent < 0 or discount_percent > 100:
                    flash("Discount percent must be between 0 and 100!", "danger")
                    return redirect(url_for("coupon.edit_coupon", id=id))

                if minimum_amount < 0:
                    flash("Minimum amount cannot be negative!", "danger")
                    return redirect(url_for("coupon.edit_coupon", id=id))

            except ValueError:
                flash("Invalid numeric values!", "danger")
                return redirect(url_for("coupon.edit_coupon", id=id))

            cur.execute(
                """
                UPDATE coupons
                SET coupon_code=%s,
                    discount_percent=%s,
                    minimum_amount=%s,
                    expiry_date=%s,
                    status=%s
                WHERE id=%s
                """,
                (
                    coupon_code,
                    discount_percent,
                    minimum_amount,
                    expiry_date,
                    status,
                    id,
                ),
            )

            mysql.connection.commit()

            flash("Coupon updated successfully!", "success")
            return redirect(url_for("coupon.coupon_list"))

        cur.execute(
            """
            SELECT id, coupon_code, discount_percent,
                   minimum_amount, expiry_date, status
            FROM coupons
            WHERE id=%s
            """,
            (id,),
        )

        coupon_data = cur.fetchone()

        if not coupon_data:
            flash("Coupon not found!", "danger")
            return redirect(url_for("coupon.coupon_list"))

        return render_template("admin/coupons/edit.html", coupon=coupon_data)

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error updating coupon: {str(e)}", "danger")
        return redirect(url_for("coupon.coupon_list"))

    finally:
        cur.close()


# =========================
# Delete Coupon (Admin)
# =========================
@coupon.route("/admin/coupons/delete/<int:id>", methods=["POST"])
def delete_coupon(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    try:
        cur.execute("SELECT coupon_code FROM coupons WHERE id=%s", (id,))

        coupon_data = cur.fetchone()

        if not coupon_data:
            flash("Coupon not found!", "danger")
            return redirect(url_for("coupon.coupon_list"))

        coupon_code = coupon_data[0]

        cur.execute("DELETE FROM coupons WHERE id=%s", (id,))

        mysql.connection.commit()

        flash(f"Coupon '{coupon_code}' deleted successfully!", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting coupon: {str(e)}", "danger")

    finally:
        cur.close()

    return redirect(url_for("coupon.coupon_list"))
