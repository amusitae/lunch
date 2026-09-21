from flask import Blueprint, render_template, redirect, url_for, flash, session
from datetime import date, timedelta

from database import get_connection


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
            orders.status
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