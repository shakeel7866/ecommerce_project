from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from database.db import mysql

contact = Blueprint("contact", __name__)


# ==========================
# Admin Contact Messages
# ==========================
@contact.route("/admin/contact-messages")
def contact_messages():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    search = request.args.get("search", "").strip()

    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    if page < 1:
        page = 1

    per_page = 10
    offset = (page - 1) * per_page

    cur = mysql.connection.cursor()

    # Total messages
    if search:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM contact_messages
            WHERE
                name LIKE %s
                OR email LIKE %s
                OR subject LIKE %s
                OR message LIKE %s
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
            ),
        )
    else:
        cur.execute("SELECT COUNT(*) FROM contact_messages")

    total_messages = cur.fetchone()[0]

    # Messages for current page
    if search:
        cur.execute(
            """
            SELECT
                id,
                name,
                email,
                subject,
                message,
                created_at
            FROM contact_messages
            WHERE
                name LIKE %s
                OR email LIKE %s
                OR subject LIKE %s
                OR message LIKE %s
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                per_page,
                offset,
            ),
        )
    else:
        cur.execute(
            """
            SELECT
                id,
                name,
                email,
                subject,
                message,
                created_at
            FROM contact_messages
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            (per_page, offset),
        )

    messages = cur.fetchall()

    cur.close()

    total_pages = (total_messages + per_page - 1) // per_page

    return render_template(
        "admin/dashboard/contact_messages.html",
        messages=messages,
        search=search,
        page=page,
        total_pages=total_pages,
        total_messages=total_messages,
    )


# ==========================
# View Contact Message
# ==========================
@contact.route("/admin/contact-messages/view/<int:id>")
def view_contact_message(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    search = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT
            id,
            name,
            email,
            subject,
            message,
            created_at
        FROM contact_messages
        WHERE id=%s
        """,
        (id,),
    )

    message = cur.fetchone()

    cur.close()

    if not message:
        flash("Message not found.", "danger")
        return redirect(url_for("contact.contact_messages", search=search, page=page))

    return render_template(
        "admin/dashboard/contact_message_view.html",
        message=message,
        search=search,
        page=page,
    )


# ==========================
# Delete Contact Message
# ==========================
@contact.route("/admin/contact-messages/delete/<int:id>")
def delete_contact_message(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    cur.execute(
        """
        DELETE FROM contact_messages
        WHERE id=%s
        """,
        (id,),
    )

    mysql.connection.commit()

    cur.close()

    flash("Contact message deleted successfully.", "success")

    return redirect(url_for("contact.contact_messages"))
