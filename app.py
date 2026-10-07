from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import date, timedelta
from routes.ai_assistant import ai_assistant

from database import get_connection, create_database

import os
from werkzeug.utils import secure_filename

from routes.auth import auth
from routes.user import user
from routes.meals import meals
from routes.weekly_planner import weekly_planner
from routes.orders import orders
from routes.admin import admin

app = Flask(__name__)
app.secret_key = "lunchpilot-secret-key"

create_database()

app.register_blueprint(auth)
app.register_blueprint(user)
app.register_blueprint(meals)
app.register_blueprint(weekly_planner)
app.register_blueprint(orders)
app.register_blueprint(admin)
app.register_blueprint(ai_assistant)


# =========================================================
# Home
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# RESTful API - Get All Meals
# =========================================================

@app.route("/api/meals", methods=["GET"])
def api_get_meals():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            meal_name,
            category,
            calories,
            price,
            ingredients,
            image
        FROM meals
        ORDER BY id ASC
    """)

    meals = cursor.fetchall()

    connection.close()

    meals_list = []

    for meal in meals:

        meals_list.append({
            "id": meal[0],
            "meal_name": meal[1],
            "category": meal[2],
            "calories": meal[3],
            "price": meal[4],
            "ingredients": meal[5],
            "image": meal[6]
        })

    return {
        "success": True,
        "count": len(meals_list),
        "meals": meals_list
    }


# =========================================================
# RESTful API - Add New Meal
# =========================================================

@app.route("/api/meals", methods=["POST"])
def api_add_meal():

    data = request.get_json()

    if not data:
        return {
            "success": False,
            "message": "JSON data is required"
        }, 400

    required_fields = [
        "meal_name",
        "category",
        "calories",
        "price",
        "ingredients"
    ]

    for field in required_fields:

        if field not in data:
            return {
                "success": False,
                "message": f"Missing field: {field}"
            }, 400

    meal_name = data["meal_name"]
    category = data["category"]
    calories = data["calories"]
    price = data["price"]
    ingredients = data["ingredients"]

    image = data.get(
        "image",
        "default-meal.jpg"
    )

    connection = get_connection()
    cursor = connection.cursor()

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
        image
    ))

    connection.commit()

    new_meal_id = cursor.lastrowid

    connection.close()

    return {
        "success": True,
        "message": "Meal added successfully",
        "meal_id": new_meal_id
    }, 201


# =========================================================
# RESTful API - Update Meal
# =========================================================

@app.route("/api/meals/<int:meal_id>", methods=["PUT"])
def api_update_meal(meal_id):

    data = request.get_json()

    if not data:
        return {
            "success": False,
            "message": "JSON data is required"
        }, 400

    required_fields = [
        "meal_name",
        "category",
        "calories",
        "price",
        "ingredients"
    ]

    for field in required_fields:

        if field not in data:
            return {
                "success": False,
                "message": f"Missing field: {field}"
            }, 400

    connection = get_connection()
    cursor = connection.cursor()

    # Check if meal exists
    cursor.execute(
        "SELECT id FROM meals WHERE id = ?",
        (meal_id,)
    )

    meal = cursor.fetchone()

    if not meal:

        connection.close()

        return {
            "success": False,
            "message": "Meal not found"
        }, 404

    image = data.get("image")

    # Keep current image if image is not provided
    if image:

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
            data["meal_name"],
            data["category"],
            data["calories"],
            data["price"],
            data["ingredients"],
            image,
            meal_id
        ))

    else:

        cursor.execute("""
            UPDATE meals
            SET
                meal_name = ?,
                category = ?,
                calories = ?,
                price = ?,
                ingredients = ?
            WHERE id = ?
        """, (
            data["meal_name"],
            data["category"],
            data["calories"],
            data["price"],
            data["ingredients"],
            meal_id
        ))

    connection.commit()
    connection.close()

    return {
        "success": True,
        "message": "Meal updated successfully",
        "meal_id": meal_id
    }


# =========================================================
# RESTful API - Delete Meal
# =========================================================

@app.route("/api/meals/<int:meal_id>", methods=["DELETE"])
def api_delete_meal(meal_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Check if meal exists
    cursor.execute(
        "SELECT id FROM meals WHERE id = ?",
        (meal_id,)
    )

    meal = cursor.fetchone()

    if not meal:

        connection.close()

        return {
            "success": False,
            "message": "Meal not found"
        }, 404

    # Delete meal
    cursor.execute(
        "DELETE FROM meals WHERE id = ?",
        (meal_id,)
    )

    connection.commit()
    connection.close()

    return {
        "success": True,
        "message": "Meal deleted successfully",
        "meal_id": meal_id
    }


# =========================================================
# RESTful API - Get One Meal
# =========================================================

@app.route("/api/meals/<int:meal_id>", methods=["GET"])
def api_get_meal(meal_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            meal_name,
            category,
            calories,
            price,
            ingredients,
            image
        FROM meals
        WHERE id = ?
    """, (meal_id,))

    meal = cursor.fetchone()

    connection.close()

    # Check if meal exists
    if not meal:

        return {
            "success": False,
            "message": "Meal not found"
        }, 404

    return {
        "success": True,
        "meal": {
            "id": meal[0],
            "meal_name": meal[1],
            "category": meal[2],
            "calories": meal[3],
            "price": meal[4],
            "ingredients": meal[5],
            "image": meal[6]
        }
    }


# =========================================================
# RESTful API - Get All Orders
# =========================================================

@app.route("/api/orders", methods=["GET"])
def api_get_orders():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            orders.id,
            orders.user_id,
            users.fullname,
            orders.meal_id,
            meals.meal_name,
            orders.order_date,
            orders.total_price,
            orders.status,
            orders.meal_date
        FROM orders
        JOIN users
            ON orders.user_id = users.id
        JOIN meals
            ON orders.meal_id = meals.id
        ORDER BY orders.id ASC
    """)

    orders = cursor.fetchall()

    connection.close()

    orders_list = []

    for order in orders:

        orders_list.append({
            "id": order[0],
            "user_id": order[1],
            "fullname": order[2],
            "meal_id": order[3],
            "meal_name": order[4],
            "order_date": order[5],
            "total_price": order[6],
            "status": order[7],
            "meal_date": order[8]
        })

    return {
        "success": True,
        "count": len(orders_list),
        "orders": orders_list
    }


# =========================================================
# RESTful API - Get One Order
# =========================================================

@app.route("/api/orders/<int:order_id>", methods=["GET"])
def api_get_order(order_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            orders.id,
            orders.user_id,
            users.fullname,
            orders.meal_id,
            meals.meal_name,
            orders.order_date,
            orders.total_price,
            orders.status,
            orders.meal_date
        FROM orders
        JOIN users
            ON orders.user_id = users.id
        JOIN meals
            ON orders.meal_id = meals.id
        WHERE orders.id = ?
    """, (order_id,))

    order = cursor.fetchone()

    connection.close()

    # Check if order exists
    if not order:

        return {
            "success": False,
            "message": "Order not found"
        }, 404

    return {
        "success": True,
        "order": {
            "id": order[0],
            "user_id": order[1],
            "fullname": order[2],
            "meal_id": order[3],
            "meal_name": order[4],
            "order_date": order[5],
            "total_price": order[6],
            "status": order[7],
            "meal_date": order[8]
        }
    }


# =========================================================
# RESTful API - Create New Order
# =========================================================

@app.route("/api/orders", methods=["POST"])
def api_add_order():

    data = request.get_json()

    if not data:
        return {
            "success": False,
            "message": "JSON data is required"
        }, 400

    required_fields = [
        "user_id",
        "meal_id",
        "order_date"
    ]

    for field in required_fields:

        if field not in data:
            return {
                "success": False,
                "message": f"Missing field: {field}"
            }, 400

    user_id = data["user_id"]
    meal_id = data["meal_id"]
    order_date = data["order_date"]

    connection = get_connection()
    cursor = connection.cursor()

    # Check if user exists
    cursor.execute(
        "SELECT id FROM users WHERE id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:

        connection.close()

        return {
            "success": False,
            "message": "User not found"
        }, 404

    # Check if meal exists and get its price
    cursor.execute(
        "SELECT id, price FROM meals WHERE id = ?",
        (meal_id,)
    )

    meal = cursor.fetchone()

    if not meal:

        connection.close()

        return {
            "success": False,
            "message": "Meal not found"
        }, 404

    # Use meal price automatically
    total_price = meal[1]

    status = data.get(
        "status",
        "Active"
    )

    meal_date = data.get(
        "meal_date"
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
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        meal_id,
        order_date,
        total_price,
        status,
        meal_date
    ))

    connection.commit()

    new_order_id = cursor.lastrowid

    connection.close()

    return {
        "success": True,
        "message": "Order created successfully",
        "order_id": new_order_id,
        "total_price": total_price
    }, 201


# =========================================================
# RESTful API - Update Order
# =========================================================

@app.route("/api/orders/<int:order_id>", methods=["PUT"])
def api_update_order(order_id):

    data = request.get_json()

    if not data:
        return {
            "success": False,
            "message": "JSON data is required"
        }, 400

    required_fields = [
        "user_id",
        "meal_id",
        "order_date"
    ]

    for field in required_fields:

        if field not in data:
            return {
                "success": False,
                "message": f"Missing field: {field}"
            }, 400

    connection = get_connection()
    cursor = connection.cursor()

    # Check if order exists
    cursor.execute(
        "SELECT id FROM orders WHERE id = ?",
        (order_id,)
    )

    order = cursor.fetchone()

    if not order:

        connection.close()

        return {
            "success": False,
            "message": "Order not found"
        }, 404

    # Check if user exists
    cursor.execute(
        "SELECT id FROM users WHERE id = ?",
        (data["user_id"],)
    )

    user = cursor.fetchone()

    if not user:

        connection.close()

        return {
            "success": False,
            "message": "User not found"
        }, 404

    # Check if meal exists and get its price
    cursor.execute(
        "SELECT id, price FROM meals WHERE id = ?",
        (data["meal_id"],)
    )

    meal = cursor.fetchone()

    if not meal:

        connection.close()

        return {
            "success": False,
            "message": "Meal not found"
        }, 404

    # Use the meal price automatically
    total_price = meal[1]

    status = data.get(
        "status",
        "Active"
    )

    meal_date = data.get(
        "meal_date"
    )

    cursor.execute("""
        UPDATE orders
        SET
            user_id = ?,
            meal_id = ?,
            order_date = ?,
            total_price = ?,
            status = ?,
            meal_date = ?
        WHERE id = ?
    """, (
        data["user_id"],
        data["meal_id"],
        data["order_date"],
        total_price,
        status,
        meal_date,
        order_id
    ))

    connection.commit()
    connection.close()

    return {
        "success": True,
        "message": "Order updated successfully",
        "order_id": order_id,
        "total_price": total_price
    }


# =========================================================
# RESTful API - Delete Order
# =========================================================

@app.route("/api/orders/<int:order_id>", methods=["DELETE"])
def api_delete_order(order_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Check if order exists
    cursor.execute(
        "SELECT id FROM orders WHERE id = ?",
        (order_id,)
    )

    order = cursor.fetchone()

    if not order:

        connection.close()

        return {
            "success": False,
            "message": "Order not found"
        }, 404

    # Delete order
    cursor.execute(
        "DELETE FROM orders WHERE id = ?",
        (order_id,)
    )

    connection.commit()
    connection.close()

    return {
        "success": True,
        "message": "Order deleted successfully",
        "order_id": order_id
    }


# =========================================================
# Run
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)