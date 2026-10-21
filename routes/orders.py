from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from datetime import date, timedelta

from database import get_connection
from routes.helpers import get_user_allergy, is_meal_safe


orders = Blueprint("orders", __name__)


# =========================================================
# My Orders
# =========================================================

@orders.route("/my-orders")
def my_orders():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    
    cursor.execute("""
        SELECT
            orders.id,
            meals.meal_name,
            meals.category,
            meals.calories,
            orders.meal_date,
            orders.total_price,
            orders.status,
            meals.ingredients
        FROM orders
        JOIN meals
        ON orders.meal_id = meals.id
        WHERE orders.user_id = ?
        ORDER BY orders.meal_date DESC,
                 orders.id DESC
    """, (session["user_id"],))

    raw_orders = cursor.fetchall()

    connection.close()

    orders_list = []
    allergy = get_user_allergy()

    for order in raw_orders:

        order_date = date.fromisoformat(
            order[4]
        )

        orders_list.append({
            "id": order[0],
            "meal": order[1],
            "category": order[2],
            "calories": order[3],
            "date": order[4],
            "day": order_date.strftime("%A"),
            "price": order[5],
            "status": order[6],
            "has_allergy_warning": not is_meal_safe(
                order[7],
                allergy
            ),
            "allergy": allergy,
            "can_edit": (
                order[6] == "Active"
                and date.today() < order_date
            ),
            "can_cancel": (
                order[6] == "Active"
                and date.today() < order_date
            )
        })

    weekly_orders = {}

    for order in orders_list:

        order_date = date.fromisoformat(
            order["date"]
        )

        monday = (
            order_date
            - timedelta(
                days=order_date.weekday()
            )
        )

        friday = (
            monday
            + timedelta(days=4)
        )

        week_key = (
            monday.strftime("%Y-%m-%d"),
            friday.strftime("%Y-%m-%d")
        )

        if week_key not in weekly_orders:
            weekly_orders[week_key] = []

        weekly_orders[week_key].append(order)

    total_price = sum(
        order["price"]
        for order in orders_list
        if order["status"] == "Active"
    )

    return render_template(
        "my_orders.html",
        orders=orders_list,
        weekly_orders=weekly_orders,
        total_price=total_price
    )



# =========================================================
# Edit Order
# =========================================================

@orders.route("/edit-order/<int:order_id>", methods=["GET", "POST"])
def edit_order(order_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    # Get the order owned by the current user
    cursor.execute("""
        SELECT id, meal_id, meal_date, status
        FROM orders
        WHERE id = ?
        AND user_id = ?
    """, (order_id, session["user_id"]))

    order = cursor.fetchone()

    if not order:
        connection.close()
        flash("Order not found.", "danger")
        return redirect(url_for("orders.my_orders"))

    # Only active orders with a future meal date can be edited
    try:
        original_date = date.fromisoformat(order[2])
    except (ValueError, TypeError):
        connection.close()
        flash("This order has an invalid meal date.", "danger")
        return redirect(url_for("orders.my_orders"))

    if order[3] != "Active" or original_date <= date.today():
        connection.close()
        flash("This order can no longer be edited.", "warning")
        return redirect(url_for("orders.my_orders"))

    # Get available meals
    
    cursor.execute("""
        SELECT id, meal_name, category, calories, price, ingredients
        FROM meals
        ORDER BY meal_name
    """)

    raw_meals = cursor.fetchall()

    allergy = get_user_allergy()
    meals = []

    for meal in raw_meals:
        meals.append({
            "id": meal[0],
            "name": meal[1],
            "category": meal[2],
            "calories": meal[3],
            "price": meal[4],
            "ingredients": meal[5],
            "has_allergy_warning": not is_meal_safe(
                meal[5],
                allergy
            )
        })

    selected_meal_has_allergy_warning = any(
        meal["id"] == order[1] and meal["has_allergy_warning"]
        for meal in meals
    )


    if request.method == "POST":

        meal_id = request.form.get("meal_id", type=int)
        meal_date_text = request.form.get("meal_date", "")

        # Validate the new date
        try:
            new_date = date.fromisoformat(meal_date_text)
        except (ValueError, TypeError):
            connection.close()
            flash("Please select a valid meal date.", "danger")
            return redirect(url_for("orders.edit_order", order_id=order_id))

        
        if new_date <= date.today():
            connection.close()
            flash("You cannot select today or a past date.", "warning")
            return redirect(url_for("orders.edit_order", order_id=order_id))

        if new_date.weekday() >= 5:
            connection.close()
            flash("Please select a weekday (Monday to Friday).", "warning")
            return redirect(url_for("orders.edit_order", order_id=order_id))


        # Ensure the selected meal exists
        cursor.execute("""
            SELECT id, price, ingredients
            FROM meals
            WHERE id = ?
        """, (meal_id,))

        selected_meal = cursor.fetchone()

        if not selected_meal:
            connection.close()
            flash("Please select a valid meal.", "danger")
            return redirect(url_for("orders.edit_order", order_id=order_id))

        # Check allergy confirmation on the server
        has_allergy_warning = not is_meal_safe(
            selected_meal[2],
            allergy
        )

        if (
            has_allergy_warning
            and request.form.get("confirm_allergy") != "yes"
        ):
            connection.close()
            flash(
                "Please confirm the allergy warning before saving.",
                "warning"
            )
            return redirect(
                url_for("orders.edit_order", order_id=order_id)
            )

        # Update the order and its price
        cursor.execute("""
            UPDATE orders
            SET meal_id = ?,
                meal_date = ?,
                total_price = ?
            WHERE id = ?
            AND user_id = ?
            AND status = 'Active'
            AND meal_date > ?
        """, (
            meal_id,
            new_date.isoformat(),
            selected_meal[1],
            order_id,
            session["user_id"],
            date.today().isoformat()
        ))

        updated = cursor.rowcount

        connection.commit()
        connection.close()

        if updated > 0:
            flash("Order updated successfully.", "success")
        else:
            flash(
                "This order can no longer be edited.",
                "warning"
            )

        return redirect(url_for("orders.my_orders"))

    connection.close()

    
    return render_template(
        "edit_order.html",
        order=order,
        meals=meals,
        allergy=allergy,
        min_date=date.today().isoformat(),
        selected_meal_has_allergy_warning=(
            selected_meal_has_allergy_warning
        )
    )



# =========================================================
# Cancel Order
# =========================================================

@orders.route(
    "/cancel-order/<int:order_id>"
)
def cancel_order(order_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    today = date.today().strftime(
        "%Y-%m-%d"
    )

    cursor.execute("""
        UPDATE orders
        SET status = 'Cancelled'
        WHERE id = ?
        AND user_id = ?
        AND status = 'Active'
        AND meal_date > ?
    """, (
        order_id,
        session["user_id"],
        today
    ))

    connection.commit()

    if cursor.rowcount > 0:

        flash(
            "Your order has been cancelled successfully.",
            "success"
        )

    else:

        flash(
            "This order can no longer be cancelled.",
            "warning"
        )

    connection.close()

    return redirect(
        url_for("orders.my_orders")
    )