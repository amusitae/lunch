import sqlite3
from datetime import date, timedelta

DATABASE = "lunchpilot.db"


def get_connection():
    return sqlite3.connect(DATABASE)


def create_database():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            allergy TEXT DEFAULT 'None',
            daily_calorie_goal INTEGER DEFAULT 2000,
            monthly_budget REAL DEFAULT 3000,
            food_preference TEXT DEFAULT 'No Preference'
        )
    """)

    cursor.execute("PRAGMA table_info(users)")
    user_columns = [row[1] for row in cursor.fetchall()]

    if "is_admin" not in user_columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN is_admin INTEGER DEFAULT 0
        """)

    if "allergy" not in user_columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN allergy TEXT DEFAULT 'None'
        """)

    if "daily_calorie_goal" not in user_columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN daily_calorie_goal INTEGER DEFAULT 2000
        """)

    if "monthly_budget" not in user_columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN monthly_budget REAL DEFAULT 3000
        """)

    if "food_preference" not in user_columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN food_preference TEXT DEFAULT 'No Preference'
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_name TEXT NOT NULL,
            category TEXT NOT NULL,
            calories INTEGER NOT NULL,
            price REAL NOT NULL,
            ingredients TEXT,
            image TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            meal_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            total_price REAL,
            status TEXT DEFAULT 'Active',
            meal_date TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(meal_id) REFERENCES meals(id)
        )
    """)

    cursor.execute("PRAGMA table_info(orders)")
    order_columns = [row[1] for row in cursor.fetchall()]

    if "status" not in order_columns:
        cursor.execute("""
            ALTER TABLE orders
            ADD COLUMN status TEXT DEFAULT 'Active'
        """)

    if "meal_date" not in order_columns:
        cursor.execute("""
            ALTER TABLE orders
            ADD COLUMN meal_date TEXT
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day TEXT,
            meal_id INTEGER NOT NULL,
            plan_date TEXT,
            status TEXT DEFAULT 'Planned',
            meal_date TEXT,
            week_start TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(meal_id) REFERENCES meals(id)
        )
    """)

    cursor.execute("PRAGMA table_info(weekly_plans)")
    weekly_columns = [row[1] for row in cursor.fetchall()]

    if "status" not in weekly_columns:
        cursor.execute("""
            ALTER TABLE weekly_plans
            ADD COLUMN status TEXT DEFAULT 'Planned'
        """)

    if "meal_date" not in weekly_columns:
        cursor.execute("""
            ALTER TABLE weekly_plans
            ADD COLUMN meal_date TEXT
        """)

    if "week_start" not in weekly_columns:
        cursor.execute("""
            ALTER TABLE weekly_plans
            ADD COLUMN week_start TEXT
        """)

    cursor.execute("""
        SELECT id, meal_date
        FROM weekly_plans
        WHERE week_start IS NULL
    """)

    old_plans = cursor.fetchall()

    for plan_id, meal_date in old_plans:

        if meal_date:
            try:
                current_date = date.fromisoformat(meal_date)

                monday = current_date - timedelta(
                    days=current_date.weekday()
                )

                cursor.execute("""
                    UPDATE weekly_plans
                    SET week_start = ?
                    WHERE id = ?
                """, (
                    monday.strftime("%Y-%m-%d"),
                    plan_id
                ))

            except ValueError:
                pass

    connection.commit()
    connection.close()

    print("Database Created Successfully!")


def add_initial_meals():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM meals
    """)

    meal_count = cursor.fetchone()[0]

    if meal_count == 0:

        meals = [
            (
                "Chicken Salad",
                "Healthy",
                420,
                120,
                "Chicken, Lettuce, Tomato, Cucumber",
                "chicken.jpg"
            ),
            (
                "Sushi",
                "Japanese",
                380,
                180,
                "Rice, Salmon, Seaweed",
                "sushi.jpg"
            ),
            (
                "Spaghetti Bolognese",
                "Italian",
                650,
                160,
                "Pasta, Beef, Tomato Sauce",
                "spaghetti.jpg"
            ),
            (
                "Grilled Salmon",
                "Seafood",
                500,
                220,
                "Salmon, Vegetables, Lemon",
                "salmon.jpg"
            )
        ]

        cursor.executemany("""
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
        """, meals)

        connection.commit()

    connection.close()


if __name__ == "__main__":
    create_database()
    add_initial_meals()