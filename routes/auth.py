from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash


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
        raw_password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # ตรวจสอบรหัสผ่านก่อนแฮช
        if raw_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("auth.register"))

        # เข้ารหัสรหัสผ่านก่อนบันทึกลงฐานข้อมูล
        password = generate_password_hash(raw_password)

        connection = get_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO users (fullname, email, password)
                VALUES (?, ?, ?)
            """, (fullname, email, password))

            connection.commit()

        except Exception as e:
            connection.close()

            if "UNIQUE" in str(e).upper():
                flash("Email already exists!", "danger")
            else:
                flash("Registration failed.", "danger")

            return redirect(url_for("auth.register"))

        connection.close()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


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
        """, (email,))

        user = cursor.fetchone()

        if user:
            stored_password = user[3]

            # ตรวจสอบว่าเป็นรหัสผ่านที่แฮชด้วย Werkzeug หรือไม่
            if str(stored_password).startswith(("scrypt:", "pbkdf2:")):
                try:
                    password_valid = check_password_hash(
                        stored_password, password
                    )
                except (ValueError, TypeError):
                    password_valid = False
            else:
                # รองรับบัญชีเดิมที่เก็บรหัสผ่านเป็นข้อความธรรมดา
                password_valid = (stored_password == password)

            if password_valid:
                # เปลี่ยนรหัสผ่านเดิมเป็นแฮชหลัง Login สำเร็จ
                if not str(stored_password).startswith(
                    ("scrypt:", "pbkdf2:")
                ):
                    hashed_password = generate_password_hash(password)

                    cursor.execute("""
                        UPDATE users
                        SET password = ?
                        WHERE id = ?
                    """, (hashed_password, user[0]))

                    connection.commit()

                connection.close()

                session["user_id"] = user[0]
                session["fullname"] = user[1]
                session["is_admin"] = user[4]
                session["allergy"] = (
                    user[5] if len(user) > 5 and user[5] else "None"
                )

                flash(f"Welcome, {user[1]}!", "success")

                if user[4] == 1:
                    return redirect(url_for("admin.admin_plan"))

                return redirect(url_for("user.dashboard"))

        connection.close()
        flash("Invalid Email or Password!", "danger")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


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