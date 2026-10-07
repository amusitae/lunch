from flask import (
    Blueprint,
    render_template,
    request,
    session
)

from database import get_connection
import ollama

ai_assistant = Blueprint(
    "ai_assistant",
    __name__
)


@ai_assistant.route(
    "/ai-assistant",
    methods=["GET", "POST"]
)
def assistant():

    answer = ""

    if request.method == "POST":

        question = request.form.get(
            "question",
            ""
        )

        question = question.strip()
        print("QUESTION:", question)

        if not question:

            answer = "Please enter a question."

            return render_template(
                "ai_assistant.html",
                answer=answer
            )

        if "user_id" not in session:

            answer = "Please login first."

            return render_template(
                "ai_assistant.html",
                answer=answer
            )

        try:

            connection = get_connection()
            cursor = connection.cursor()

            # ==========================
            # USER PROFILE
            # ==========================

            cursor.execute("""
                SELECT
                    fullname,
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

            if not user_data:

                answer = "User profile not found."

                return render_template(
                    "ai_assistant.html",
                    answer=answer
                )

            fullname = user_data[0]
            allergy = user_data[1] or "No Allergy"
            daily_goal = user_data[2]
            monthly_budget = user_data[3]
            food_preference = user_data[4] or "No Preference"

            # ==========================
            # ORDER HISTORY
            # ==========================

            cursor.execute("""
                SELECT
                    meals.meal_name,
                    meals.calories,
                    meals.category,
                    meals.price
                FROM orders
                JOIN meals
                    ON orders.meal_id = meals.id
                WHERE orders.user_id = ?
            """, (
                session["user_id"],
            ))

            orders = cursor.fetchall()

            # ==========================
            # ALL MEALS
            # ==========================

            cursor.execute("""
                SELECT
                    meal_name,
                    calories,
                    category,
                    price,
                    ingredients
                FROM meals
            """)

            meals = cursor.fetchall()

            connection.close()

            if not orders:

                answer = (
                    "You have no meal history yet. "
                    "Please order some meals first."
                )

            else:

                # โค้ดส่วน meal_history,
                # prompt,
                # ollama.chat
                # ใช้ของเดิมต่อได้เลย

                meal_history = ""
                available_meals = ""

                total_calories = 0
                total_spending = 0

                meal_names = []

                for order in orders:

                    meal_name = order[0]
                    calories = order[1]
                    category = order[2]
                    price = order[3]

                    meal_names.append(meal_name)

                    total_calories += calories
                    total_spending += price

                    meal_history += (
                        f"{meal_name} | "
                        f"{calories} kcal | "
                        f"{category} | "
                        f"{price} THB\n"
                    )

                recent_orders = meal_names[-3:]

                
                if allergy == "Fish/Seafood":
                    allergy_words = [
                        "fish", "salmon", "tuna",
                        "shrimp", "seafood"
                    ]

                elif allergy == "Dairy":
                    allergy_words = [
                        "milk", "cheese",
                        "dairy", "butter"
                    ]

                elif allergy == "Eggs":
                    allergy_words = [
                        "egg", "eggs"
                    ]

                elif allergy == "Peanuts":
                    allergy_words = [
                        "peanut", "peanuts"
                    ]

                elif allergy == "Nuts":
                    allergy_words = [
                        "nut", "nuts",
                        "almond", "cashew", "walnut"
                    ]

                elif allergy == "Gluten":
                    allergy_words = [
                        "gluten", "wheat",
                        "pasta", "bread"
                    ]

                else:
                    allergy_words = []

                for meal in meals:

                    ingredients = (meal[4] or "").lower()

                    if any(word in ingredients for word in allergy_words):
                        continue

                    available_meals += (
                        f"{meal[0]} | "
                        f"{meal[1]} kcal | "
                        f"{meal[2]} | "
                        f"{meal[3]} THB | "
                        f"Ingredients: {meal[4]}\n"
                    )

                if not available_meals.strip():

                    answer = (
                        "No safe meals available "
                        "for your allergy."
                    )

                    return render_template(
                        "ai_assistant.html",
                        answer=answer
                    )

                average_calories = (
                    total_calories / len(orders)
                )

                favorite_meal = max(
                    set(meal_names),
                    key=meal_names.count
                )

                last_meal_calories = orders[-1][1]

                remaining_calories = (
                    daily_goal - last_meal_calories
                )

                prompt = f"""

USER PROFILE
--------------
Name: {fullname}
Food Preference: {food_preference}
Allergy: {allergy}
Daily Calorie Goal: {daily_goal}
Monthly Budget: {monthly_budget}

USER STATISTICS
--------------
Total Orders: {len(orders)}
Total Calories: {total_calories}
Average Calories: {average_calories:.0f}
Total Spending: {total_spending}
Favorite Meal: {favorite_meal}
Recent Meals: {", ".join(recent_orders)}

BALANCE INFORMATION
--------------
Daily Goal: {daily_goal}
Last Meal Calories: {last_meal_calories}
Remaining Calories: {remaining_calories:.0f}

AVAILABLE MEALS
--------------
{available_meals}

USER ORDER HISTORY
--------------
{meal_history}

IMPORTANT:

The user may ask about foods that are NOT in AVAILABLE MEALS.

Examples:
- Can I eat sushi?
- Is milk good for me?
- Can I eat seafood?

For these questions:
1. Answer directly.
2. Check allergies.
3. Explain briefly.
4. Recommend a meal only if appropriate.

USER QUESTION
--------------
{question}

RULES
--------------
1. Answer the USER QUESTION directly.
2. If the user asks about a specific meal, check its ingredients first.
3. Compare the meal ingredients with the user's allergy.
4. If the meal contains an allergy-related ingredient, clearly warn the user.
5. Only recommend meals from AVAILABLE MEALS.
6. Never create new meal names.
7. Consider food preference.
8. Consider calorie goal.
9. Consider spending and monthly budget.
10. Suggest a healthier or safer alternative when appropriate.
11. Do not use markdown.
12. Do not use ** symbols.
13. Use plain text only.
14. Keep the answer short and friendly.
15. Recommend ONLY ONE meal.
16. Never recommend multiple meals.
17. Recommendation must contain exactly one meal name.
18. Never recommend meals that contain ingredients related to the user's allergy.
19. Exclude allergic meals before selecting a recommendation.
20. If allergy = Fish/Seafood, do not recommend meals containing fish, salmon, tuna, shrimp, seafood.
21. Favorite Meal may be unsafe.
22. Never recommend Favorite Meal unless it exists in AVAILABLE MEALS.
23. Recommend only meals listed in AVAILABLE MEALS.
24. If the user frequently eats the same meal,
recommend a different meal from AVAILABLE MEALS.

25. Avoid recommending the user's favorite meal repeatedly.
26. If the user asks for an alternative to a favorite meal,
recommend the most similar meal from AVAILABLE MEALS.
27. If average calories are high,
recommend a lower calorie meal.

28. If average calories are low,
recommend a balanced meal.

29. Help the user maintain calorie balance.
30. If a meal has been ordered many times,
recommend a different meal for variety.
31. Check Recent Meals before recommending.
32. If the same meal appears multiple times in Recent Meals,
recommend a different meal.
33. Help the user maintain meal variety.
34. Use Last Meal Calories and Remaining Calories when recommending meals.
35. If Last Meal Calories is high, recommend a lower calorie meal.
36. If the user repeatedly eats the same meal in Recent Meals, recommend a different meal.
37. Use Remaining Calories to help balance the user's next meal.
38. If the user's favorite meal appears in Recent Meals, avoid recommending it again.
39. When recommending a meal, explain briefly why it matches the user's eating history.

40. If the user asks for an alternative meal, mention the meal being replaced.

41. If the user recently ate the same meal multiple times, explain that variety is recommended.
Return response in one of these formats.

If answering a general food question:

DO NOT include:
Recommendation:
Reason:

Direct Answer:
[your answer]

Health Tip:
[one short health tip]

--------------------------------

If recommending a meal:

Direct Answer:
[your answer]

Recommendation:
[meal name]

Reason:
- reason 1
- reason 2
- reason 3

Health Tip:
[one short health tip]

When recommending a meal,
you MUST include:

Recommendation:
Reason:
Health Tip:

Do not answer with only a meal name.

If the user only asks a general food question,
you may answer without giving a recommendation.
"""

                print("AVAILABLE MEALS:")
                print(available_meals)

                print("START OLLAMA")

                response = ollama.chat(
    model="qwen2.5:3b",
    options={
        "temperature": 0
    },
    messages=[
        {
            "role": "system",
            "content": """
You are LunchPilot AI.

IMPORTANT:

If the user asks for a recommendation
(example: recommend a meal, suggest food, what should I eat),
you MUST return:

Direct Answer:
...

Recommendation:
...

Reason:
- ...
- ...
- ...

Health Tip:
...

If the user asks a general food question
(example: can I eat sushi, is milk healthy),
DO NOT include Recommendation or Reason.

Never recommend meals outside AVAILABLE MEALS.
Never ignore allergies.

CRITICAL:

Before recommending a meal:
1. Check meal ingredients.
2. Compare ingredients with user allergy.
3. Remove unsafe meals.
4. Recommend only safe meals.

Never recommend a meal that contains allergy ingredients.
Never skip Recommendation.
Never skip Reason.
Never skip Health Tip.

Do not use markdown.
Use plain text only.
"""
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
)
                print("FINISH OLLAMA")


                ai_response = response["message"]["content"]

                print("========== AI RESPONSE ==========")
                print(ai_response)
                print("=================================")

                if "Recommendation:\nNone" in ai_response:
                    ai_response = ai_response.replace(
                        "Recommendation:\nNone",
                        ""
                    )

                if "Recommendation:\nNo recommendation" in ai_response:
                    ai_response = ai_response.replace(
                        "Recommendation:\nNo recommendation",
                        ""
                    )

                if "Recommendation:\nN/A" in ai_response:
                    ai_response = ai_response.replace(
                        "Recommendation:\nN/A",
                        ""
                    )

                safe_meal = (
                    available_meals.split("\n")[0]
                    .split("|")[0]
                    .strip()
                )

                recommend_keywords = [
                    "recommend",
                    "suggest",
                    "what should i eat",
                    "meal recommendation",
                    "food recommendation",
                    "recommend me"
                ]

                if (
                    any(word in question.lower() for word in recommend_keywords)
                    and "Recommendation:" not in ai_response
                ): 
                    
                    ai_response = (
                    f"Direct Answer:\n"
                    f"I recommend {safe_meal}.\n\n"
                    f"Recommendation:\n{safe_meal}\n\n"
                    "Reason:\n"
                    "- Safe for your allergy\n"
                    "- Fits your calorie goal\n"
                    "- Healthy choice\n\n"
                    "Health Tip:\n"
                    "Maintain a balanced diet."
                )

                ai_response = ai_response.replace(
                    "Recommendation:\n",
                    "<h3 class='text-success fw-bold mt-3 mb-2'>🍽️ Recommended Meal</h3>"
                    "<div class='fs-4 fw-bold mb-3'>"
                )

                ai_response = ai_response.replace(
                    "\n\nReason:",
                    "</div><strong>Reason:</strong>"
                )

                ai_response = ai_response.replace(
                    "Direct Answer:",
                    "<strong>💬 Answer:</strong>"
                )

                ai_response = ai_response.replace(
                    "Health Tip:",
                    "<br><br><strong>💡 Health Tip:</strong>"
                )

                answer = f"""
👤 USER PROFILE

Name: {fullname}
Preference: {food_preference}
Allergy: {allergy}

📊 EATING SUMMARY

Total Orders: {len(orders)}
Favorite Meal: {favorite_meal}
Recent Meals: {", ".join(recent_orders)}
Average Calories: {average_calories:.0f} kcal

Total Spending: {total_spending:.2f} THB
Monthly Budget: {monthly_budget:.2f} THB

Daily Goal: {daily_goal} kcal

<hr>

{ai_response}
"""

        except Exception as e:

            answer = (
                "AI Error: "
                + str(e)
            )

    return render_template(
        "ai_assistant.html",
        answer=answer
    )