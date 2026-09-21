from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_connection


# =========================================================
# Authentication Blueprint
# =========================================================

auth = Blueprint("auth", __name__)


# =========================================================
# Register
# =========================================================

@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:

            flash(
                "Passwords do not match!",
                "danger"
            )

            return redirect(
                url_for("auth.register")
            )

        connection = get_connection()
        cursor = connection.cursor()

        try:

            cursor.execute("""
                INSERT INTO users
                (
                    fullname,
                    email,
                    password
                )
                VALUES (?, ?, ?)
            """, (
                fullname,
                email,
                password
            ))

            connection.commit()

        except Exception as e:

            connection.close()

            if "UNIQUE" in str(e).upper():

                flash(
                    "Email already exists!",
                    "danger"
                )

            else:

                flash(
                    "Registration failed.",
                    "danger"
                )

            return redirect(
                url_for("auth.register")
            )

        connection.close()

        flash(
            "Registration successful! Please login.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "register.html"
    )


# =========================================================
# Login
# =========================================================

@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM users
            WHERE email = ?
            AND password = ?
        """, (
            email,
            password
        ))

        user = cursor.fetchone()

        connection.close()

        if user:

            session["user_id"] = user[0]
            session["fullname"] = user[1]
            session["is_admin"] = user[4]

            session["allergy"] = (
                user[5]
                if len(user) > 5 and user[5]
                else "None"
            )

            flash(
                f"Welcome, {user[1]}!",
                "success"
            )

            if user[4] == 1:

                return redirect(
                    url_for("admin.admin_plan")
                )

            return redirect(
                url_for("user.dashboard")
            )

        flash(
            "Invalid Email or Password!",
            "danger"
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "login.html"
    )


# =========================================================
# Logout
# =========================================================

@auth.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("home")
    )