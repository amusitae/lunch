from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import os
from werkzeug.utils import secure_filename

from database import get_connection


admin = Blueprint("admin", __name__)


# =========================================================
# ADMIN PLAN
# =========================================================

@admin.route("/admin-plan")
def admin_plan():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    connection.close()

    if not user or user[0] != 1:

        flash(
            "Access denied. Admins only.",
            "danger"
        )

        return redirect(
            url_for("user.dashboard")
        )

    return render_template(
        "admin_plan.html"
    )


# =========================================================
# ADMIN USERS
# =========================================================

@admin.route("/admin/users")
def admin_users():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        (session["user_id"],)
    )

    admin_user = cursor.fetchone()

    if not admin_user or admin_user[0] != 1:

        connection.close()

        flash(
            "Access denied. Admins only.",
            "danger"
        )

        return redirect(
            url_for("user.dashboard")
        )

    cursor.execute("""
        SELECT id, fullname, email, is_admin
        FROM users
        ORDER BY id ASC
    """)

    users = cursor.fetchall()

    connection.close()

    return render_template(
        "admin_users.html",
        users=users
    )


# =========================================================
# DELETE USER
# =========================================================

@admin.route("/admin/delete-user/<int:user_id>")
def delete_user(user_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if user_id == session["user_id"]:

        flash(
            "You cannot delete your own admin account.",
            "danger"
        )

        return redirect(
            url_for("admin.admin_users")
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        (session["user_id"],)
    )

    admin_user = cursor.fetchone()

    if not admin_user or admin_user[0] != 1:

        connection.close()

        flash(
            "Access denied. Admins only.",
            "danger"
        )

        return redirect(
            url_for("user.dashboard")
        )

    cursor.execute(
        "DELETE FROM weekly_plans WHERE user_id = ?",
        (user_id,)
    )

    cursor.execute(
        "DELETE FROM orders WHERE user_id = ?",
        (user_id,)
    )

    cursor.execute(
        "DELETE FROM users WHERE id = ?",
        (user_id,)
    )

    connection.commit()
    connection.close()

    flash(
        "User deleted successfully.",
        "success"
    )

    return redirect(
        url_for("admin.admin_users")
    )


# =========================================================
# ADMIN MEALS
# =========================================================

@admin.route("/admin")
def admin_panel():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != 1:

        connection.close()

        flash(
            "Access denied. Admins only.",
            "danger"
        )

        return redirect(
            url_for("user.dashboard")
        )

    cursor.execute("""
        SELECT *
        FROM meals
        ORDER BY id ASC
    """)

    meals = cursor.fetchall()

    connection.close()

    return render_template(
        "admin.html",
        meals=meals
    )


# =========================================================
# ADMIN ORDERS
# =========================================================

@admin.route("/admin/orders")
def admin_orders():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != 1:

        connection.close()

        flash(
            "Access denied. Admins only.",
            "danger"
        )

        return redirect(
            url_for("user.dashboard")
        )

    selected_date = request.args.get(
        "date",
        ""
    )

    selected_status = request.args.get(
        "status",
        ""
    )

    query = """
        SELECT
            orders.id,
            users.fullname,
            meals.meal_name,
            orders.meal_date,
            orders.total_price,
            orders.status
        FROM orders
        JOIN users
        ON orders.user_id = users.id
        JOIN meals
        ON orders.meal_id = meals.id
        WHERE 1=1
    """

    params = []

    if selected_date:

        query += """
            AND orders.meal_date = ?
        """

        params.append(
            selected_date
        )

    if selected_status:

        query += """
            AND orders.status = ?
        """

        params.append(
            selected_status
        )

    query += """
        ORDER BY orders.meal_date ASC,
                 orders.id ASC
    """

    cursor.execute(
        query,
        params
    )

    orders = cursor.fetchall()

    connection.close()

    return render_template(
        "admin_orders.html",
        orders=orders,
        selected_date=selected_date,
        selected_status=selected_status
    )


# =========================================================
# UPDATE ORDER STATUS
# =========================================================

@admin.route(
    "/admin/update-order/<int:order_id>",
    methods=["POST"]
)
def admin_update_order(order_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != 1:

        connection.close()

        flash(
            "Access denied. Admins only.",
            "danger"
        )

        return redirect(
            url_for("user.dashboard")
        )

    new_status = request.form.get(
        "status"
    )

    allowed_statuses = [
        "Active",
        "Prepared",
        "Delivered",
        "Cancelled"
    ]

    if new_status not in allowed_statuses:

        connection.close()

        flash(
            "Invalid order status.",
            "danger"
        )

        return redirect(
            url_for("admin.admin_orders")
        )

    cursor.execute("""
        UPDATE orders
        SET status = ?
        WHERE id = ?
    """, (
        new_status,
        order_id
    ))

    connection.commit()

    if cursor.rowcount > 0:

        flash(
            "Order status updated successfully!",
            "success"
        )

    else:

        flash(
            "Order not found.",
            "danger"
        )

    connection.close()

    return redirect(
        url_for("admin.admin_orders")
    )


# =========================================================
# EDIT MEAL
# =========================================================

@admin.route(
    "/admin/edit-meal/<int:meal_id>",
    methods=["GET", "POST"]
)
def edit_meal(meal_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != 1:

        connection.close()

        flash(
            "Access denied. Admins only.",
            "danger"
        )

        return redirect(
            url_for("user.dashboard")
        )

    cursor.execute(
        "SELECT * FROM meals WHERE id = ?",
        (meal_id,)
    )

    meal = cursor.fetchone()

    if not meal:

        connection.close()

        flash(
            "Meal not found.",
            "danger"
        )

        return redirect(
            url_for("admin.admin_panel")
        )

    if request.method == "POST":

        meal_name = request.form["meal_name"]
        category = request.form["category"]
        calories = request.form["calories"]
        price = request.form["price"]
        ingredients = request.form["ingredients"]

        image_filename = meal[6]

        image_file = request.files.get("image")

        if image_file and image_file.filename:

            image_filename = secure_filename(
                image_file.filename
            )

            image_path = os.path.join(
                "static",
                "images",
                image_filename
            )

            image_file.save(image_path)

        cursor.execute("""
            UPDATE meals
            SET
                meal_name = ?,
                category = ?,
                calories = ?,
                price = ?,
                ingredients = ?,
                image = ?
            WHERE id = ?
        """, (
            meal_name,
            category,
            calories,
            price,
            ingredients,
            image_filename,
            meal_id
        ))

        connection.commit()
        connection.close()

        flash(
            "Meal updated successfully!",
            "success"
        )

        return redirect(
            url_for("admin.admin_panel")
        )

    connection.close()

    return render_template(
        "edit_meal.html",
        meal=meal
    )


# =========================================================
# ADD MEAL
# =========================================================

@admin.route(
    "/admin/add-meal",
    methods=["GET", "POST"]
)
def add_meal():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != 1:

        connection.close()

        flash(
            "Access denied. Admin only.",
            "danger"
        )

        return redirect(
            url_for("meals.meals_page")
        )

    if request.method == "POST":

        meal_name = request.form["meal_name"]
        category = request.form["category"]
        calories = request.form["calories"]
        price = request.form["price"]
        ingredients = request.form["ingredients"]

        image_file = request.files.get("image")

        image_filename = "default-meal.jpg"

        if image_file and image_file.filename:

            image_filename = secure_filename(
                image_file.filename
            )

            image_path = os.path.join(
                "static",
                "images",
                image_filename
            )

            image_file.save(image_path)

        cursor.execute("""
            INSERT INTO meals
            (
                meal_name,
                category,
                calories,
                price,
                ingredients,
                image
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            meal_name,
            category,
            calories,
            price,
            ingredients,
            image_filename
        ))

        connection.commit()
        connection.close()

        flash(
            "Meal added successfully!",
            "success"
        )

        return redirect(
            url_for("admin.admin_panel")
        )

    connection.close()

    return render_template(
        "add_meal.html"
    )

# =========================================================
# DELETE MEAL
# =========================================================

@admin.route("/admin/delete-meal/<int:meal_id>")
def delete_meal(meal_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != 1:

        connection.close()

        flash(
            "Access denied. Admins only.",
            "danger"
        )

        return redirect(
            url_for("user.dashboard")
        )

    cursor.execute(
        "DELETE FROM meals WHERE id = ?",
        (meal_id,)
    )

    connection.commit()

    if cursor.rowcount > 0:

        flash(
            "Meal deleted successfully!",
            "success"
        )

    else:

        flash(
            "Meal not found.",
            "danger"
        )

    connection.close()

    return redirect(
        url_for("admin.admin_panel")
    )