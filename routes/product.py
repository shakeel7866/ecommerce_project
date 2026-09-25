import os
import uuid
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db import mysql

product = Blueprint("product", __name__)


# =========================
# Product List (Admin)
# =========================
@product.route("/admin/products")
def product_list():

    search = request.args.get("search", "")
    sort_by = request.args.get("sort_by", "id_asc")  # Default sort

    cur = mysql.connection.cursor()

    # Products Count
    cur.execute("SELECT COUNT(*) FROM products")
    products_count = cur.fetchone()[0]

    # Build the base query
    query = """
        SELECT
            products.id,
            products.product_name,
            categories.category_name,
            products.stock,
            products.status,
            products.created_at,
            products.price,
            products.original_price,
            products.discount_percent,
            products.image,
            brands.brand_name,
            products.rating
        FROM products
        INNER JOIN categories
            ON products.category_id = categories.id
        INNER JOIN brands
            ON products.brand_id = brands.id
    """

    # Add search condition
    if search:
        query += """
        WHERE
            products.product_name LIKE %s
            OR categories.category_name LIKE %s
            OR brands.brand_name LIKE %s
        """

    # Add sorting
    if sort_by == "id_asc":
        query += " ORDER BY products.id ASC"
    elif sort_by == "id_desc":
        query += " ORDER BY products.id DESC"
    elif sort_by == "name_asc":
        query += " ORDER BY products.product_name ASC"
    elif sort_by == "name_desc":
        query += " ORDER BY products.product_name DESC"
    elif sort_by == "price_asc":
        query += " ORDER BY products.price ASC"
    elif sort_by == "price_desc":
        query += " ORDER BY products.price DESC"
    elif sort_by == "stock_asc":
        query += " ORDER BY products.stock ASC"
    elif sort_by == "stock_desc":
        query += " ORDER BY products.stock DESC"
    elif sort_by == "newest":
        query += " ORDER BY products.created_at DESC"
    elif sort_by == "oldest":
        query += " ORDER BY products.created_at ASC"
    else:
        query += " ORDER BY products.id ASC"  # Default

    # Execute query
    if search:
        value = "%" + search + "%"
        cur.execute(query, (value, value, value))
    else:
        cur.execute(query)

    products = cur.fetchall()

    cur.close()

    return render_template(
        "admin/products/list.html",
        products=products,
        search=search,
        sort_by=sort_by,
        products_count=products_count,
    )


# =========================
# Add Product (Admin)
# =========================
@product.route("/admin/products/add", methods=["GET", "POST"])
def add_product():

    cur = mysql.connection.cursor()

    # Category Dropdown
    cur.execute("SELECT id, category_name FROM categories ORDER BY category_name ASC")
    categories = cur.fetchall()

    # Brand Dropdown
    cur.execute("SELECT id, brand_name FROM brands ORDER BY brand_name ASC")
    brands = cur.fetchall()

    if request.method == "POST":

        category_id = request.form["category_id"]
        brand_id = request.form["brand_id"]
        product_name = request.form["product_name"]
        sku = request.form["sku"]
        barcode = request.form.get("barcode", "")
        description = request.form["description"]
        price = request.form["price"]
        original_price = request.form["original_price"]
        discount_percent = request.form["discount_percent"]
        stock = request.form["stock"]

        # =========================
        # Check Duplicate SKU
        # =========================
        cur.execute("SELECT id FROM products WHERE sku=%s", (sku,))

        if cur.fetchone():
            cur.close()
            flash("SKU already exists! Please use a different SKU.", "danger")
            return render_template(
                "admin/products/add.html",
                categories=categories,
                brands=brands,
                form_data=request.form,
            )

        # Upload Image
        image = request.files.get("image")
        filename = None

        if image and image.filename != "":
            # Validate file extension
            allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
            extension = os.path.splitext(image.filename)[1].lower()

            if extension not in allowed_extensions:
                cur.close()
                flash("Invalid file format! Allowed: JPG, JPEG, PNG, WEBP", "danger")
                return render_template(
                    "admin/products/add.html",
                    categories=categories,
                    brands=brands,
                    form_data=request.form,
                )

            filename = f"{uuid.uuid4().hex}{extension}"

            # Ensure upload directory exists
            upload_folder = os.path.join("static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)

            upload_path = os.path.join(upload_folder, filename)
            image.save(upload_path)

        # Insert Product
        cur.execute(
            """
            INSERT INTO products
            (
                category_id,
                brand_id,
                product_name,
                sku,
                barcode,
                description,
                price,
                original_price,
                discount_percent,
                stock,
                image
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                category_id,
                brand_id,
                product_name,
                sku,
                barcode,
                description,
                price,
                original_price,
                discount_percent,
                stock,
                filename,
            ),
        )

        # Get the inserted product ID
        product_id = cur.lastrowid

        # Handle gallery images
        gallery_images = request.files.getlist("gallery")
        for img in gallery_images:
            if img and img.filename != "":
                # Validate file extension
                ext = os.path.splitext(img.filename)[1].lower()
                if ext in {".jpg", ".jpeg", ".png", ".webp"}:
                    gallery_filename = f"{uuid.uuid4().hex}{ext}"
                    img.save(os.path.join("static", "uploads", gallery_filename))

                    cur.execute(
                        """
                        INSERT INTO product_images
                        (
                            product_id,
                            image
                        )
                        VALUES
                        (
                            %s,
                            %s
                        )
                        """,
                        (
                            product_id,
                            gallery_filename,
                        ),
                    )

        mysql.connection.commit()
        cur.close()

        flash("Product Added Successfully!", "success")
        return redirect(url_for("product.product_list"))

    cur.close()

    return render_template(
        "admin/products/add.html", categories=categories, brands=brands, form_data={}
    )


# =========================
# Edit Product (Admin)
# =========================
@product.route("/admin/products/edit/<int:id>", methods=["GET", "POST"])
def edit_product(id):

    cur = mysql.connection.cursor()

    # Categories
    cur.execute("SELECT id, category_name FROM categories ORDER BY category_name ASC")
    categories = cur.fetchall()

    # Brands
    cur.execute("SELECT id, brand_name FROM brands ORDER BY brand_name ASC")
    brands = cur.fetchall()

    # Current Product
    cur.execute(
        """
        SELECT
            id,
            category_id,
            brand_id,
            product_name,
            sku,
            barcode,
            description,
            price,
            original_price,
            discount_percent,
            stock,
            image
        FROM products
        WHERE id=%s
    """,
        (id,),
    )
    product_data = cur.fetchone()

    if not product_data:
        cur.close()
        flash("Product not found!", "danger")
        return redirect(url_for("product.product_list"))

    if request.method == "POST":
        category_id = request.form["category_id"]
        brand_id = request.form["brand_id"]
        product_name = request.form["product_name"]
        sku = request.form["sku"]
        barcode = request.form.get("barcode", "")
        description = request.form["description"]
        price = request.form["price"]
        original_price = request.form["original_price"]
        discount_percent = request.form["discount_percent"]
        stock = request.form["stock"]

        # Image is at index 11
        filename = product_data[11] if product_data else None

        image = request.files.get("image")

        if image and image.filename != "":
            # Validate file extension
            allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
            extension = os.path.splitext(image.filename)[1].lower()

            if extension not in allowed_extensions:
                cur.close()
                flash("Invalid file format! Allowed: JPG, JPEG, PNG, WEBP", "danger")
                return render_template(
                    "admin/products/edit.html",
                    product=product_data,
                    categories=categories,
                    brands=brands,
                )

            # Delete old image
            if filename:
                old_file = os.path.join("static", "uploads", filename)
                if os.path.exists(old_file):
                    os.remove(old_file)

            # Save new image
            filename = f"{uuid.uuid4().hex}{extension}"

            upload_folder = os.path.join("static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)

            image.save(os.path.join(upload_folder, filename))

        cur.execute(
            """
            UPDATE products
            SET
                category_id=%s,
                brand_id=%s,
                product_name=%s,
                sku=%s,
                barcode=%s,
                description=%s,
                price=%s,
                original_price=%s,
                discount_percent=%s,
                stock=%s,
                image=%s
            WHERE id=%s
            """,
            (
                category_id,
                brand_id,
                product_name,
                sku,
                barcode,
                description,
                price,
                original_price,
                discount_percent,
                stock,
                filename,
                id,
            ),
        )

        mysql.connection.commit()
        cur.close()

        flash("Product Updated Successfully!", "success")
        return redirect(url_for("product.product_list"))

    cur.close()

    return render_template(
        "admin/products/edit.html",
        product=product_data,
        categories=categories,
        brands=brands,
    )


# =========================
# Delete Product (Admin)
# Soft Delete - Keeps History Safe
# =========================
@product.route("/admin/products/delete/<int:id>", methods=["POST"])
def delete_product(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    try:
        # Check product exists
        cur.execute(
            """
            SELECT id, product_name, stock, status
            FROM products
            WHERE id=%s
            """,
            (id,),
        )

        product_data = cur.fetchone()

        if not product_data:
            flash("Product not found!", "danger")
            return redirect(url_for("product.product_list"))

        product_name = product_data[1]

        # ---------------------------------------
        # Soft Delete
        # ---------------------------------------
        # 0 = inactive
        # Stock becomes 0
        #
        # We DO NOT delete the product because
        # orders, sales and purchases may reference it.
        cur.execute(
            """
            UPDATE products
            SET stock=0,
                status=0
            WHERE id=%s
            """,
            (id,),
        )

        # ---------------------------------------
        # Remove product from active cart
        # ---------------------------------------
        cur.execute("DELETE FROM cart WHERE product_id=%s", (id,))

        # ---------------------------------------
        # Remove product view records
        # ---------------------------------------
        cur.execute("DELETE FROM product_views WHERE product_id=%s", (id,))

        mysql.connection.commit()

        flash(f"Product '{product_name}' deactivated successfully!", "success")

    except Exception as e:

        mysql.connection.rollback()

        flash(f"Error updating product: {str(e)}", "danger")

    finally:
        cur.close()

    return redirect(url_for("product.product_list"))


# =========================
# Toggle Product Status (Active/Inactive) - Admin
# =========================
@product.route("/admin/products/toggle-status/<int:id>", methods=["POST"])
def toggle_product_status(id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    cur = mysql.connection.cursor()

    try:
        cur.execute("SELECT status FROM products WHERE id=%s", (id,))
        row = cur.fetchone()

        if not row:
            cur.close()
            flash("Product not found!", "danger")
            return redirect(url_for("product.product_list"))

        # status is tinyint(1): 1 = active, 0 = inactive
        current_status = int(row[0]) if row[0] is not None else 1
        new_status = 0 if current_status == 1 else 1

        cur.execute(
            "UPDATE products SET status=%s WHERE id=%s",
            (new_status, id),
        )
        mysql.connection.commit()

        if new_status == 1:
            flash(
                "Product marked as ACTIVE. It will now appear on the store.", "success"
            )
        else:
            flash(
                "Product marked as INACTIVE. It will be hidden from the store.",
                "success",
            )

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error updating product status: {str(e)}", "danger")

    finally:
        cur.close()

    return redirect(url_for("product.product_list"))


# =========================
# Product Details (Frontend) - OPTIMIZED VERSION
# =========================
@product.route("/product/<int:id>")
def product_details(id):
    cur = mysql.connection.cursor()

    # Main Product Data
    cur.execute(
        """
        SELECT
            products.id,
            products.product_name,
            products.sku,
            products.barcode,
            products.description,
            products.price,
            products.original_price,
            products.discount_percent,
            products.stock,
            products.image,
            products.rating,
            products.created_at,
            categories.category_name,
            categories.id AS category_id,
            brands.brand_name,
            brands.id AS brand_id
        FROM products
        INNER JOIN categories
            ON products.category_id = categories.id
        INNER JOIN brands
            ON products.brand_id = brands.id
        WHERE products.id=%s
          AND products.status = 1
        """,
        (id,),
    )
    product_data = cur.fetchone()

    if not product_data:
        cur.close()
        flash("Product not found!", "danger")
        return redirect(url_for("home"))

    # =========================
    # Save Product View (No Duplicates)
    # =========================
    customer_id = session.get("customer_id")

    if customer_id:
        # Check if view already exists
        cur.execute(
            """
            SELECT id, viewed_at
            FROM product_views
            WHERE customer_id=%s AND product_id=%s
            LIMIT 1
            """,
            (customer_id, id),
        )

        existing_view = cur.fetchone()

        if existing_view:
            # Update existing view with current timestamp
            cur.execute(
                """
                UPDATE product_views
                SET viewed_at = CURRENT_TIMESTAMP
                WHERE id=%s
                """,
                (existing_view[0],),
            )
        else:
            # Insert new view
            cur.execute(
                """
                INSERT INTO product_views
                (customer_id, product_id, viewed_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                """,
                (customer_id, id),
            )

        mysql.connection.commit()

    # Product Gallery Images
    cur.execute(
        """
        SELECT image
        FROM product_images
        WHERE product_id=%s
        ORDER BY id ASC
        """,
        (id,),
    )
    gallery = cur.fetchall()

    # Product Reviews
    cur.execute(
        """
        SELECT
            id,
            customer_name,
            rating,
            review,
            created_at
        FROM product_reviews
        WHERE product_id=%s
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (id,),
    )
    reviews = cur.fetchall()

    # Rating Summary
    cur.execute(
        """
        SELECT
            COUNT(*) AS total_reviews,
            ROUND(AVG(rating), 1) AS avg_rating
        FROM product_reviews
        WHERE product_id=%s
        """,
        (id,),
    )
    rating_summary = cur.fetchone()

    # =========================
    # User Behavior Analysis (OPTIMIZED - single query)
    # =========================

    viewed_products = []
    user_category_preferences = {}
    user_brand_preferences = {}
    # Pre-loaded data for recommendation scoring
    product_view_counts = {}
    user_viewed_pairs = []

    if customer_id:
        # Get user's most viewed categories and brands with recency weighting
        cur.execute(
            """
            SELECT 
                p.category_id,
                p.brand_id,
                COUNT(*) as view_count,
                MAX(pv.viewed_at) as last_viewed,
                DATEDIFF(NOW(), MAX(pv.viewed_at)) as days_since_last_view
            FROM product_views pv
            INNER JOIN products p ON pv.product_id = p.id
            WHERE pv.customer_id = %s
            AND pv.viewed_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY p.category_id, p.brand_id
            ORDER BY view_count DESC, days_since_last_view ASC
            LIMIT 5
            """,
            (customer_id,),
        )

        viewed_products = cur.fetchall()

        # Extract category and brand preferences
        for row in viewed_products:
            category_id = row[0]
            brand_id = row[1]
            view_count = row[2]
            days_since_last_view = row[4] if row[4] is not None else 999

            # Recency weighting: newer views get more weight
            recency_weight = max(0, 1 - (days_since_last_view / 30))
            weighted_score = view_count * (1 + recency_weight)

            if category_id:
                user_category_preferences[category_id] = (
                    user_category_preferences.get(category_id, 0) + weighted_score
                )

            if brand_id:
                user_brand_preferences[brand_id] = (
                    user_brand_preferences.get(brand_id, 0) + weighted_score
                )

        # =========================
        # OPTIMIZATION: Fetch all user views at once (replaces N queries in loop)
        # =========================
        cur.execute(
            """
            SELECT pv.product_id, COUNT(*) as cnt
            FROM product_views pv
            WHERE pv.customer_id = %s
            GROUP BY pv.product_id
            """,
            (customer_id,),
        )
        for row in cur.fetchall():
            product_view_counts[row[0]] = int(row[1] or 0)

        cur.execute(
            """
            SELECT p.category_id, p.brand_id
            FROM product_views pv
            JOIN products p ON p.id = pv.product_id
            WHERE pv.customer_id = %s
            """,
            (customer_id,),
        )
        user_viewed_pairs = cur.fetchall()

    # =========================
    # Hybrid AI Recommendations
    # =========================

    # Get all other products with their details
    cur.execute(
        """
        SELECT
            id,
            product_name,
            description,
            price,
            image,
            category_id,
            brand_id,
            rating,
            stock
        FROM products
        WHERE id != %s
          AND status = 1
        """,
        (id,),
    )

    all_products = cur.fetchall()

    recommended_products = []

    if all_products:

        current_name = product_data[1] or ""
        current_description = product_data[4] or ""
        current_price = float(product_data[5] or 0)
        current_category = product_data[13]
        current_brand = product_data[15]
        current_rating = float(product_data[10] or 0)

        # Current product text for TF-IDF
        current_text = f"{current_name} {current_description}".lower()

        # Prepare product texts
        product_texts = []
        for p in all_products:
            name = p[1] or ""
            description = p[2] or ""
            product_texts.append(f"{name} {description}".lower())

        # -------------------------
        # TF-IDF Similarity
        # -------------------------
        try:
            texts = [current_text] + product_texts
            vectorizer = TfidfVectorizer(
                stop_words="english",
                max_features=500,
                ngram_range=(1, 2),
            )
            tfidf_matrix = vectorizer.fit_transform(texts)
            similarity_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[
                0
            ]
        except Exception:
            similarity_scores = [0] * len(all_products)

        # -------------------------
        # Hybrid Recommendation Score
        # -------------------------
        scored_products = []

        for index, p in enumerate(all_products):
            product_id = p[0]
            product_name = p[1]
            product_price = float(p[3] or 0)
            product_category = p[5]
            product_brand = p[6]
            product_rating = float(p[7] or 0)
            product_stock = int(p[8] or 0)

            # Skip out-of-stock products
            if product_stock <= 0:
                continue

            # =========================
            # Customer Behavior Score (from pre-loaded dict)
            # =========================
            behavior_score = 0
            if customer_id:
                view_count = product_view_counts.get(product_id, 0)
                behavior_score = min(view_count * 5, 10)

            # =========================
            # Customer Preference Score (from pre-loaded list)
            # =========================
            preference_score = 0
            if customer_id and user_viewed_pairs:
                for viewed_category, viewed_brand in user_viewed_pairs:
                    if product_category == viewed_category:
                        preference_score += 5
                    if product_brand == viewed_brand:
                        preference_score += 5
                preference_score = min(preference_score, 15)

            # =========================
            # AI Recommendation Score
            # =========================
            text_score = float(similarity_scores[index]) * 40
            category_score = 20 if product_category == current_category else 0
            brand_score = 15 if product_brand == current_brand else 0

            # =========================
            # Price Similarity Score
            # =========================
            price_score = 0
            if current_price > 0 and product_price > 0:
                price_difference = abs(current_price - product_price)
                max_price = max(current_price, product_price)
                price_similarity = max(0, 1 - (price_difference / max_price))
                price_score = price_similarity * 15

            # =========================
            # Rating Score
            # =========================
            rating_score = min(product_rating * 2, 10)

            # =========================
            # Final AI Score
            # =========================
            final_score = (
                text_score
                + category_score
                + brand_score
                + behavior_score
                + preference_score
                + price_score
                + rating_score
            )

            final_score = min(final_score, 100)

            scored_products.append((final_score, p))

        # Sort by score (highest first)
        scored_products.sort(key=lambda x: x[0], reverse=True)

        # Top 4 recommendations
        recommended_products = [
            (p, round(score, 2)) for score, p in scored_products[:4]
        ]

    # Product Specifications
    cur.execute(
        """
        SELECT
            spec_name,
            spec_value
        FROM product_specifications
        WHERE product_id=%s
        ORDER BY id ASC
        """,
        (id,),
    )
    specifications = cur.fetchall()

    cur.close()

    return render_template(
        "products/view.html",
        product=product_data,
        reviews=reviews,
        rating_summary=rating_summary,
        recommended_products=recommended_products,
        gallery=gallery,
        specifications=specifications,
        viewed_products=viewed_products,
    )


# =========================
# Add Review (Frontend)
# =========================
@product.route("/product/review", methods=["POST"])
def add_review():

    if "customer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.login"))

    product_id = request.form["product_id"]
    rating = request.form["rating"]
    review = request.form["review"]

    cur = mysql.connection.cursor()

    cur.execute(
        """
        INSERT INTO product_reviews
        (
            product_id,
            customer_id,
            customer_name,
            rating,
            review
        )
        VALUES
        (%s,%s,%s,%s,%s)
        """,
        (
            product_id,
            session["customer_id"],
            session["customer_name"],
            rating,
            review,
        ),
    )

    mysql.connection.commit()

    # Update product rating
    cur.execute(
        """
        SELECT AVG(rating)
        FROM product_reviews
        WHERE product_id=%s
        """,
        (product_id,),
    )
    avg_rating = cur.fetchone()[0]

    cur.execute(
        """
        UPDATE products
        SET rating=%s
        WHERE id=%s
        """,
        (round(avg_rating, 1) if avg_rating else 0, product_id),
    )

    mysql.connection.commit()
    cur.close()

    flash("Review Submitted Successfully!", "success")
    return redirect(url_for("product.product_details", id=product_id))
