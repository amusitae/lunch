from flask import Blueprint, render_template, redirect, url_for, flash, session
from database import get_connection

from routes.helpers import (
    get_user_allergy,
    is_meal_safe
)

meals = Blueprint("meals", __name__)


# =========================================================
# Meals
# =========================================================

@meals.route("/meals")
def meals_page():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM meals
        ORDER BY id ASC
    """)

    all_meals = cursor.fetchall()

    allergy = get_user_allergy()

    meals_list = [
        meal
        for meal in all_meals
        if is_meal_safe(
            meal[5],
            allergy
        )
    ]

    connection.close()

    return render_template(
        "meals.html",
        meals=meals_list,
        allergy=allergy
    )


# =========================================================
# Direct Order
# =========================================================

@meals.route("/order/<int:meal_id>")
def order(meal_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            price,
            ingredients,
            meal_name
        FROM meals
        WHERE id = ?
    """, (meal_id,))

    meal = cursor.fetchone()

    if not meal:

        connection.close()

        flash(
            "Meal not found!",
            "danger"
        )

        return redirect(
            url_for("meals.meals_page")
        )

    allergy = get_user_allergy()

    if not is_meal_safe(
        meal[1],
        allergy
    ):

        connection.close()

        flash(
            f"This meal is not suitable for your {allergy} allergy.",
            "danger"
        )

        return redirect(
            url_for("meals.meals_page")
        )

    cursor.execute("""
        INSERT INTO orders
        (
            user_id,
            meal_id,
            order_date,
            total_price,
            status,
            meal_date
        )
        VALUES (
            ?,
            ?,
            DATE('now'),
            ?,
            'Active',
            DATE('now')
        )
    """, (
        session["user_id"],
        meal_id,
        meal[0]
    ))

    connection.commit()
    connection.close()

    flash(
        "Order placed successfully!",
        "success"
    )

    return redirect(
        url_for("meals.meals_page")
    )