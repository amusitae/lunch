# routes/user.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import date, timedelta

from database import get_connection
from routes.helpers import is_meal_safe


user = Blueprint("user", __name__)


# =========================================================
# My Preferences
# =========================================================

@user.route("/my-preferences", methods=["GET", "POST"])
def my_preferences():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":

        selected_allergies = request.form.getlist("allergy")

        other_allergy = request.form.get(
            "allergy_other",
            ""
        ).strip()

        if len(selected_allergies) > 1 and "None" in selected_allergies:
            selected_allergies.remove("None")

        if other_allergy:
            selected_allergies.append(other_allergy)

        if not selected_allergies:
            allergy = "None"
        else:
            allergy = ", ".join(selected_allergies)

        daily_calorie_goal = request.form.get(
            "daily_calorie_goal",
            2000,
            type=int
        )

        monthly_budget = request.form.get(
            "monthly_budget",
            3000,
            type=float
        )

        food_preference = request.form.get(
            "food_preference",
            "No Preference"
        )

        if daily_calorie_goal <= 0:

            connection.close()

            flash(
                "Daily calorie goal must be greater than 0.",
                "danger"
            )

            return redirect(
                url_for("user.my_preferences")
            )

        if monthly_budget < 0:

            connection.close()

            flash(
                "Monthly budget cannot be negative.",
                "danger"
            )

            return redirect(
                url_for("user.my_preferences")
            )

        cursor.execute("""
            UPDATE users
            SET
                allergy = ?,
                daily_calorie_goal = ?,
                monthly_budget = ?,
                food_preference = ?
            WHERE id = ?
        """, (
            allergy,
            daily_calorie_goal,
            monthly_budget,
            food_preference,
            session["user_id"]
        ))

        connection.commit()

        session["allergy"] = allergy

        connection.close()

        flash(
            "Your preferences have been updated successfully!",
            "success"
        )

        return redirect(
            url_for("user.my_preferences")
        )

    cursor.execute("""
        SELECT
            allergy,
            daily_calorie_goal,
            monthly_budget,
            food_preference
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    ))

    user_data = cursor.fetchone()

    connection.close()

    allergy = (
        user_data[0]
        if user_data and user_data[0]
        else "None"
    )

    standard_allergies = [
        "Fish/Seafood",
        "Dairy",
        "Eggs",
        "Peanuts",
        "Nuts",
        "Gluten"
    ]

    allergy_other = ""

    if allergy != "None":

        saved_allergies = [
            item.strip()
            for item in allergy.split(",")
        ]

        custom_allergies = [
            item
            for item in saved_allergies
            if item not in standard_allergies
            and item != "None"
        ]

        allergy_other = ", ".join(
            custom_allergies
        )

    return render_template(
        "my_preferences.html",
        allergy=allergy,
        allergy_other=allergy_other,
        daily_calorie_goal=(
            user_data[1]
            if user_data and user_data[1]
            else 2000
        ),
        monthly_budget=(
            user_data[2]
            if user_data and user_data[2] is not None
            else 3000
        ),
        food_preference=(
            user_data[3]
            if user_data and user_data[3]
            else "No Preference"
        )
    )


# =========================================================
# Dashboard
# =========================================================

@user.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    today = date.today()

    monday = today - timedelta(
        days=today.weekday()
    )

    friday = monday + timedelta(days=4)

    # =====================================================
    # Weekly Statistics
    # =====================================================

    cursor.execute("""
        SELECT
            COUNT(*),
            COALESCE(SUM(meals.calories), 0),
            COALESCE(SUM(orders.total_price), 0)
        FROM orders
        JOIN meals
        ON orders.meal_id = meals.id
        WHERE orders.user_id = ?
        AND orders.status = 'Active'
        AND orders.meal_date BETWEEN ? AND ?
    """, (
        session["user_id"],
        monday.strftime("%Y-%m-%d"),
        friday.strftime("%Y-%m-%d")
    ))

    result = cursor.fetchone()

    order_count = (
        result[0]
        if result and result[0] is not None
        else 0
    )

    total_calories = (
        result[1]
        if result and result[1] is not None
        else 0
    )

    total_spent = (
        result[2]
        if result and result[2] is not None
        else 0
    )

    # =====================================================
    # User Preferences
    # =====================================================

    cursor.execute("""
        SELECT
            allergy,
            daily_calorie_goal,
            monthly_budget,
            food_preference
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    ))

    user_data = cursor.fetchone()

    allergy = (
        user_data[0]
        if user_data and user_data[0]
        else "None"
    )

    daily_calorie_goal = (
        user_data[1]
        if user_data and user_data[1] is not None
        else 2000
    )

    monthly_budget = (
        user_data[2]
        if user_data and user_data[2] is not None
        else 3000
    )

    food_preference = (
        user_data[3]
        if user_data and user_data[3]
        else "No Preference"
    )

    # =====================================================
    # Make sure numeric values are valid
    # =====================================================

    try:
        daily_calorie_goal = float(
            daily_calorie_goal
        )
    except (TypeError, ValueError):
        daily_calorie_goal = 2000

    try:
        monthly_budget = float(
            monthly_budget
        )
    except (TypeError, ValueError):
        monthly_budget = 3000

    try:
        total_calories = float(
            total_calories
        )
    except (TypeError, ValueError):
        total_calories = 0

    try:
        total_spent = float(
            total_spent
        )
    except (TypeError, ValueError):
        total_spent = 0

    # =====================================================
    # Monthly Spending
    # =====================================================

    first_day_of_month = today.replace(day=1)

    cursor.execute("""
        SELECT
            COALESCE(SUM(total_price), 0)
        FROM orders
        WHERE user_id = ?
        AND status = 'Active'
        AND meal_date >= ?
    """, (
        session["user_id"],
        first_day_of_month.strftime("%Y-%m-%d")
    ))

    monthly_result = cursor.fetchone()

    if monthly_result and monthly_result[0] is not None:
        monthly_spent = monthly_result[0]
    else:
        monthly_spent = 0

    try:
        monthly_spent = float(
            monthly_spent
        )
    except (TypeError, ValueError):
        monthly_spent = 0

    # =====================================================
    # Remaining Budget
    # =====================================================

    remaining_budget = max(
        monthly_budget - monthly_spent,
        0
    )

    # =====================================================
    # Budget Progress
    # =====================================================

    if monthly_budget > 0:

        budget_percentage = (
            monthly_spent
            / monthly_budget
        ) * 100

    else:

        budget_percentage = 0

    budget_percentage = min(
        max(budget_percentage, 0),
        100
    )

    # =====================================================
    # Calorie Progress
    # =====================================================

    if daily_calorie_goal > 0:

        calorie_percentage = (
            total_calories
            / daily_calorie_goal
        ) * 100

    else:

        calorie_percentage = 0

    calorie_percentage = min(
        max(calorie_percentage, 0),
        100
    )

    # =====================================================
    # Smart Meal Recommendation
    # =====================================================

    cursor.execute("""
        SELECT *
        FROM meals
        ORDER BY id ASC
    """)

    all_meals = cursor.fetchall()

    recommendation = None
    best_score = -1

    for meal in all_meals:

        if not is_meal_safe(
            meal[5],
            allergy
        ):
            continue

        score = 0

        meal_name = meal[1]
        meal_category = meal[2]
        meal_calories = meal[3]
        meal_price = meal[4]

        # Food Preference
        if (
            food_preference != "No Preference"
            and food_preference.lower()
            in meal_category.lower()
        ):
            score += 4

        elif (
            food_preference != "No Preference"
            and food_preference.lower()
            in meal_name.lower()
        ):
            score += 3

        # Calorie Goal
        if meal_calories <= daily_calorie_goal:
            score += 2

        if meal_calories <= daily_calorie_goal * 0.8:
            score += 1

        # Monthly Budget
        if meal_price <= remaining_budget:
            score += 2

        # Choose Best Meal
        if score > best_score:
            best_score = score
            recommendation = meal

    # =====================================================
    # Upcoming Meal
    # =====================================================

    cursor.execute("""
        SELECT
            orders.meal_date,
            meals.meal_name,
            meals.calories,
            meals.price
        FROM orders
        JOIN meals
        ON orders.meal_id = meals.id
        WHERE orders.user_id = ?
        AND orders.status = 'Active'
        AND orders.meal_date >= ?
        ORDER BY orders.meal_date ASC
        LIMIT 1
    """, (
        session["user_id"],
        today.strftime("%Y-%m-%d")
    ))

    upcoming_meal = cursor.fetchone()

    connection.close()

    # =====================================================
    # Dashboard
    # =====================================================

    return render_template(
        "dashboard.html",

        order_count=order_count,

        total_calories=total_calories,

        total_spent=total_spent,

        monthly_spent=monthly_spent,

        remaining_budget=remaining_budget,

        monthly_budget=monthly_budget,

        budget_percentage=budget_percentage,

        daily_calorie_goal=daily_calorie_goal,

        calorie_percentage=calorie_percentage,

        food_preference=food_preference,

        recommendation=recommendation,

        upcoming_meal=upcoming_meal,

        allergy=allergy
    )