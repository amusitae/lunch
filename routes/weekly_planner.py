from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import date, timedelta

from database import get_connection
from routes.helpers import get_user_allergy, is_meal_safe


weekly_planner = Blueprint("weekly_planner", __name__)


@weekly_planner.route("/weekly-planner", methods=["GET", "POST"])
def weekly_planner_page():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    selected_week = request.args.get("week_start")

    if not selected_week:
        today = date.today()
        selected_week = today - timedelta(days=today.weekday())
    else:
        try:
            selected_week = date.fromisoformat(selected_week)
        except ValueError:
            today = date.today()
            selected_week = today - timedelta(days=today.weekday())

    week_start = selected_week
    week_end = week_start + timedelta(days=4)

    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    selected_week_start = week_start.isoformat()

    # -----------------------------------
    # Create Monday - Friday dates
    # -----------------------------------

    week_days = []

    for i in range(5):
        current_date = week_start + timedelta(days=i)

        week_days.append({
            "date": current_date.isoformat(),
            "display_date": current_date.strftime("%A, %d %B"),
            "day_name": current_date.strftime("%A"),
            "offset": i
        })

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------
    # Get all meals
    # -----------------------------------

    cursor.execute("""
        SELECT *
        FROM meals
        ORDER BY id ASC
    """)

    all_meals = cursor.fetchall()

    allergy = get_user_allergy()

    meals = [
        meal
        for meal in all_meals
        if is_meal_safe(meal[5], allergy)
    ]

    # -----------------------------------
    # Get weekly plans
    # -----------------------------------

    cursor.execute("""
        SELECT
            weekly_plans.id,
            weekly_plans.meal_id,
            weekly_plans.plan_date,
            weekly_plans.status,
            meals.meal_name,
            meals.price,
            meals.calories
        FROM weekly_plans
        JOIN meals
            ON weekly_plans.meal_id = meals.id
        WHERE weekly_plans.user_id = ?
        AND weekly_plans.plan_date BETWEEN ? AND ?
        ORDER BY weekly_plans.plan_date ASC,
                 weekly_plans.id ASC
    """, (
        user_id,
        week_start.isoformat(),
        week_end.isoformat()
    ))

    plans = cursor.fetchall()

    # -----------------------------------
    # Organize plans by day
    # -----------------------------------

    plans_by_day = {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": []
    }

    for plan in plans:

        try:
            plan_date = date.fromisoformat(plan[2])
        except ValueError:
            continue

        day_name = plan_date.strftime("%A")

        if day_name in plans_by_day:
            plans_by_day[day_name].append(plan)

    # -----------------------------------
    # Weekly totals
    # -----------------------------------

    total_price = sum(
        float(plan[5] or 0)
        for plan in plans
    )

    total_calories = sum(
        int(plan[6] or 0)
        for plan in plans
    )

    # -----------------------------------
    # Check weekly status
    # -----------------------------------

    has_planned = any(
        plan[3] == "Planned"
        for plan in plans
    )

    has_confirmed = any(
        plan[3] == "Confirmed"
        for plan in plans
    )

    has_ordered = any(
        plan[3] == "Ordered"
        for plan in plans
    )

    locked = has_confirmed or has_ordered

    # ===================================
    # ADD MEAL TO WEEKLY PLAN
    # ===================================

    if request.method == "POST":

        if locked:

            flash(
                "This week has already been confirmed or ordered.",
                "warning"
            )

            connection.close()

            return redirect(
                url_for(
                    "weekly_planner.weekly_planner_page",
                    week_start=selected_week_start
                )
            )

        meal_id = request.form.get("meal_id")

        plan_date = request.form.get("plan_date")

        day_offset = request.form.get("day_offset")

        # -----------------------------------
        # Calculate date from day offset
        # -----------------------------------

        if not plan_date and day_offset is not None:

            try:

                day_offset = int(day_offset)

                plan_date = (
                    week_start +
                    timedelta(days=day_offset)
                ).isoformat()

            except ValueError:

                plan_date = None

        # -----------------------------------
        # Validate meal and date
        # -----------------------------------

        if not meal_id or not plan_date:

            flash(
                "Please select a meal and date.",
                "danger"
            )

            connection.close()

            return redirect(
                url_for(
                    "weekly_planner.weekly_planner_page",
                    week_start=selected_week_start
                )
            )

        # -----------------------------------
        # Get selected meal
        # -----------------------------------

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

            flash(
                "Meal not found!",
                "danger"
            )

            connection.close()

            return redirect(
                url_for(
                    "weekly_planner.weekly_planner_page",
                    week_start=selected_week_start
                )
            )

        # -----------------------------------
        # Allergy check
        # -----------------------------------

        if not is_meal_safe(
            meal[1],
            allergy
        ):

            flash(
                f"This meal is not suitable for your {allergy} allergy.",
                "danger"
            )

            connection.close()

            return redirect(
                url_for(
                    "weekly_planner.weekly_planner_page",
                    week_start=selected_week_start
                )
            )

        # -----------------------------------
        # Validate selected date
        # -----------------------------------

        try:

            selected_plan_date = date.fromisoformat(
                plan_date
            )

        except ValueError:

            flash(
                "Invalid date selected.",
                "danger"
            )

            connection.close()

            return redirect(
                url_for(
                    "weekly_planner.weekly_planner_page",
                    week_start=selected_week_start
                )
            )

        # -----------------------------------
        # Make sure date is Monday-Friday
        # -----------------------------------

        if (
            selected_plan_date < week_start
            or
            selected_plan_date > week_end
        ):

            flash(
                "Please select a date within the current week.",
                "danger"
            )

            connection.close()

            return redirect(
                url_for(
                    "weekly_planner.weekly_planner_page",
                    week_start=selected_week_start
                )
            )

        # -----------------------------------
        # Maximum 2 meals per day
        # -----------------------------------

        cursor.execute("""
            SELECT COUNT(*)
            FROM weekly_plans
            WHERE user_id = ?
            AND plan_date = ?
        """, (
            user_id,
            plan_date
        ))

        meal_count = cursor.fetchone()[0]

        if meal_count >= 2:

            flash(
                "You can add a maximum of 2 meals per day.",
                "warning"
            )

            connection.close()

            return redirect(
                url_for(
                    "weekly_planner.weekly_planner_page",
                    week_start=selected_week_start
                )
            )

        # -----------------------------------
        # Get day name
        # -----------------------------------

        day_name = selected_plan_date.strftime("%A")

        # ===================================
        # INSERT WEEKLY PLAN
        # ===================================

        cursor.execute("""
            INSERT INTO weekly_plans
            (
                user_id,
                meal_id,
                plan_date,
                day,
                status
            )
            VALUES (?, ?, ?, ?, 'Planned')
        """, (
            user_id,
            meal_id,
            plan_date,
            day_name
        ))

        connection.commit()

        connection.close()

        flash(
            "Meal added to your weekly plan!",
            "success"
        )

        return redirect(
            url_for(
                "weekly_planner.weekly_planner_page",
                week_start=selected_week_start
            )
        )

    # -----------------------------------
    # Close connection
    # -----------------------------------

    connection.close()

    # -----------------------------------
    # Render page
    # -----------------------------------

    return render_template(
        "weekly_planner.html",
        meals=meals,
        plans=plans,
        plans_by_day=plans_by_day,
        week_start=week_start,
        week_end=week_end,
        week_days=week_days,
        locked=locked,
        allergy=allergy,
        total_price=total_price,
        total_calories=total_calories,
        previous_week=previous_week.isoformat(),
        next_week=next_week.isoformat(),
        selected_week_start=selected_week_start,
        has_planned=has_planned,
        has_confirmed=has_confirmed,
        has_ordered=has_ordered
    )


# ==========================================
# REMOVE PLAN
# ==========================================

@weekly_planner.route("/remove-plan/<int:plan_id>")
def remove_plan(plan_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM weekly_plans
        WHERE id = ?
        AND user_id = ?
        AND status = 'Planned'
    """, (
        plan_id,
        session["user_id"]
    ))

    connection.commit()
    connection.close()

    flash(
        "Meal removed from your weekly plan.",
        "success"
    )

    return redirect(
        url_for(
            "weekly_planner.weekly_planner_page"
        )
    )


# ==========================================
# CONFIRM WEEKLY PLAN
# ==========================================

@weekly_planner.route(
    "/confirm-weekly-plan",
    methods=["POST"]
)
def confirm_weekly_plan():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    week_start = request.form.get("week_start")

    if not week_start:
        return redirect(
            url_for(
                "weekly_planner.weekly_planner_page"
            )
        )

    try:

        week_start_date = date.fromisoformat(
            week_start
        )

    except ValueError:

        return redirect(
            url_for(
                "weekly_planner.weekly_planner_page"
            )
        )

    week_end_date = (
        week_start_date +
        timedelta(days=4)
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE weekly_plans
        SET status = 'Confirmed'
        WHERE user_id = ?
        AND plan_date BETWEEN ? AND ?
        AND status = 'Planned'
    """, (
        session["user_id"],
        week_start_date.isoformat(),
        week_end_date.isoformat()
    ))

    connection.commit()
    connection.close()

    flash(
        "Weekly plan confirmed successfully!",
        "success"
    )

    return redirect(
        url_for(
            "weekly_planner.weekly_planner_page",
            week_start=week_start
        )
    )


# ==========================================
# ORDER FULL WEEK
# ==========================================

@weekly_planner.route(
    "/order-full-week",
    methods=["POST", "GET"]
)
def order_full_week():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    week_start = request.values.get(
        "week_start"
    )

    if not week_start:

        return redirect(
            url_for(
                "weekly_planner.weekly_planner_page"
            )
        )

    try:

        week_start_date = date.fromisoformat(
            week_start
        )

    except ValueError:

        return redirect(
            url_for(
                "weekly_planner.weekly_planner_page"
            )
        )

    week_end_date = (
        week_start_date +
        timedelta(days=4)
    )

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------
    # Get confirmed meals
    # -----------------------------------

    cursor.execute("""
        SELECT
            weekly_plans.meal_id,
            weekly_plans.plan_date,
            meals.price
        FROM weekly_plans
        JOIN meals
            ON weekly_plans.meal_id = meals.id
        WHERE weekly_plans.user_id = ?
        AND weekly_plans.plan_date BETWEEN ? AND ?
        AND weekly_plans.status = 'Confirmed'
    """, (
        session["user_id"],
        week_start_date.isoformat(),
        week_end_date.isoformat()
    ))

    plans = cursor.fetchall()

    if not plans:

        connection.close()

        flash(
            "No confirmed meals found for this week.",
            "warning"
        )

        return redirect(
            url_for(
                "weekly_planner.weekly_planner_page",
                week_start=week_start
            )
        )

    # -----------------------------------
    # Create orders
    # -----------------------------------

    for plan in plans:

        meal_id = plan[0]
        plan_date = plan[1]
        price = plan[2]

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
                ?
            )
        """, (
            session["user_id"],
            meal_id,
            price,
            plan_date
        ))

    # -----------------------------------
    # Change plans to Ordered
    # -----------------------------------

    cursor.execute("""
        UPDATE weekly_plans
        SET status = 'Ordered'
        WHERE user_id = ?
        AND plan_date BETWEEN ? AND ?
        AND status = 'Confirmed'
    """, (
        session["user_id"],
        week_start_date.isoformat(),
        week_end_date.isoformat()
    ))

    connection.commit()
    connection.close()

    flash(
        "All meals for the week have been ordered successfully!",
        "success"
    )

    return redirect(
        url_for(
            "orders.my_orders"
        )
    )