# routes/helpers.py

from database import get_connection


# =========================
# Allergy Keywords
# =========================

ALLERGY_KEYWORDS = {
    "Fish/Seafood": ["fish", "salmon", "seafood"],
    "Dairy": ["milk", "cheese", "dairy", "butter"],
    "Eggs": ["egg", "eggs"],
    "Peanuts": ["peanut", "peanuts"],
    "Nuts": ["nut", "nuts", "almond", "cashew", "walnut"],
    "Gluten": ["gluten", "wheat", "pasta", "bread"]
}


# =========================
# Get Allergies List
# =========================

def get_allergies_list(allergy):
    if not allergy:
        return []

    return [
        item.strip()
        for item in allergy.split(",")
        if item.strip()
    ]


# =========================
# Check Meal Safety
# =========================

def is_meal_safe(ingredients, allergy):
    if not allergy:
        return True

    ingredients = (ingredients or "").lower()

    allergies = get_allergies_list(allergy)

    for allergy_name in allergies:

        keywords = ALLERGY_KEYWORDS.get(allergy_name, [])

        for keyword in keywords:
            if keyword.lower() in ingredients:
                return False

    return True


# =========================
# Get Current User Allergy
# =========================

def get_user_allergy():
    from flask import session

    user_id = session.get("user_id")

    if not user_id:
        return ""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT allergy FROM users WHERE id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    conn.close()

    if user and user[0]:
        return user[0]

    return ""