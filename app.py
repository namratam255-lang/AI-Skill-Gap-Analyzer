from flask import Flask, render_template, request, redirect, session
from database.db import get_database_connection
from flask_bcrypt import Bcrypt
from ai_career import (
    generate_career_guidance,
    generate_learning_roadmap
)


app = Flask(__name__)
app.secret_key = "ai_skill_gap_secret"

bcrypt = Bcrypt(app)


# =========================
# Home Page
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# Registration
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        db = get_database_connection()
        cursor = db.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
                """,
                (name, email, hashed_password)
            )

            db.commit()

        except Exception as e:
            db.rollback()
            return "Registration Failed: " + str(e)

        finally:
            cursor.close()
            db.close()

        return redirect("/login")

    return render_template("register.html")


# =========================
# Login
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        db = get_database_connection()
        cursor = db.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT * FROM users WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone()

        finally:
            cursor.close()
            db.close()

        if user and bcrypt.check_password_hash(
            user["password"], password
        ):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect("/dashboard")

        return "Invalid Email or Password"

    return render_template("login.html")


# =========================
# Dashboard with Progress
# =========================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    job_role_id = session.get("selected_job_role_id")

    total_skills = 0
    completed_skills = 0
    progress_percentage = 0
    selected_role_name = None

    db = get_database_connection()
    cursor = db.cursor(dictionary=True)

    try:

        if job_role_id:

            cursor.execute(
                """
                SELECT role_name
                FROM job_roles
                WHERE id = %s
                """,
                (job_role_id,)
            )

            role = cursor.fetchone()

            if role:
                selected_role_name = role["role_name"]

                cursor.execute(
                    """
                    SELECT
                        COUNT(*) AS total,
                        COALESCE(
                            SUM(
                                CASE
                                    WHEN status = 'Completed'
                                    THEN 1
                                    ELSE 0
                                END
                            ), 0
                        ) AS completed
                    FROM progress
                    WHERE user_id = %s
                    AND job_role_id = %s
                    """,
                    (user_id, job_role_id)
                )

                result = cursor.fetchone()

                total_skills = result["total"] or 0
                completed_skills = result["completed"] or 0

                if total_skills > 0:
                    progress_percentage = int(
                        completed_skills * 100 / total_skills
                    )

    finally:
        cursor.close()
        db.close()

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        total_skills=total_skills,
        completed_skills=completed_skills,
        progress_percentage=progress_percentage,
        selected_role_name=selected_role_name
    )


# =========================
# Profile Management
# =========================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    # FIXED: Correct indentation
    db = get_database_connection()
    cursor = db.cursor(dictionary=True)

    try:

        if request.method == "POST":

            skill_name = request.form.get(
                "skill_name", ""
            ).strip()

            skill_type = request.form.get("skill_type")

            if skill_name and skill_type in ["Technical", "Soft"]:

                cursor.execute(
                    """
                    INSERT INTO skills
                    (user_id, skill_name, skill_type)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, skill_name, skill_type)
                )

                db.commit()

        cursor.execute(
            """
            SELECT id, name, email
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        cursor.execute(
            """
            SELECT id, skill_name, skill_type
            FROM skills
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (user_id,)
        )

        skills = cursor.fetchall()

    finally:
        cursor.close()
        db.close()

    return render_template(
        "profile.html",
        user=user,
        skills=skills
    )


# =========================
# Job Role Selection
# =========================

@app.route("/job-role")
def job_role():

    if "user_id" not in session:
        return redirect("/login")

    db = get_database_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, role_name, required_skills
            FROM job_roles
            ORDER BY role_name
            """
        )

        job_roles = cursor.fetchall()

    finally:
        cursor.close()
        db.close()

    return render_template(
        "job_role.html",
        job_roles=job_roles
    )


# =========================
# Select Job Role
# =========================

@app.route("/select-role", methods=["POST"])
def select_role():

    if "user_id" not in session:
        return redirect("/login")

    job_role_id = request.form.get("job_role_id")

    if not job_role_id:
        return redirect("/job-role")

    session["selected_job_role_id"] = job_role_id

    return redirect("/assessment")


# =========================
# Skill Assessment
# =========================

@app.route("/assessment", methods=["GET", "POST"])
def assessment():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    job_role_id = request.form.get("job_role_id")

    if not job_role_id:
        job_role_id = session.get("selected_job_role_id")

    if not job_role_id:
        return redirect("/job-role")

    session["selected_job_role_id"] = job_role_id

    db = get_database_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, role_name, required_skills
            FROM job_roles
            WHERE id = %s
            """,
            (job_role_id,)
        )

        job_role = cursor.fetchone()

        cursor.execute(
            """
            SELECT id, skill_name, skill_type
            FROM skills
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (user_id,)
        )

        skills = cursor.fetchall()

    finally:
        cursor.close()
        db.close()

    if not job_role:
        return "Job Role Not Found"

    return render_template(
        "assessment.html",
        job_role=job_role,
        skills=skills
    )


# =========================
# Skill Gap Analysis
# =========================

@app.route("/skill-gap", methods=["GET", "POST"])
def skill_gap():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    job_role_id = (
        request.form.get("job_role_id")
        or request.args.get("job_role_id")
        or session.get("selected_job_role_id")
    )

    if not job_role_id:
        return redirect("/job-role")

    session["selected_job_role_id"] = job_role_id

    db = get_database_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # FIXED: Correct SQL query formatting
        cursor.execute(
            """
            SELECT id, role_name, required_skills
            FROM job_roles
            WHERE id = %s
            """,
            (job_role_id,)
        )

        job_role = cursor.fetchone()

        cursor.execute(
            """
            SELECT skill_name, skill_type
            FROM skills
            WHERE user_id = %s
            """,
            (user_id,)
        )

        user_skills = cursor.fetchall()

    finally:
        cursor.close()
        db.close()

    if not job_role:
        return "Job Role Not Found"

    required_skills = [
        skill.strip().lower()
        for skill in (job_role["required_skills"] or "").split(",")
        if skill.strip()
    ]

    current_skills = [
        skill["skill_name"].strip().lower()
        for skill in user_skills
        if skill["skill_name"]
    ]

    matched_skills = [
        skill for skill in required_skills
        if skill in current_skills
    ]

    missing_skills = [
        skill for skill in required_skills
        if skill not in current_skills
    ]

    total_skills = len(required_skills)
    matched_count = len(matched_skills)

    skill_percentage = (
        int(matched_count * 100 / total_skills)
        if total_skills else 0
    )

    if skill_percentage >= 80:
        message = (
            "Excellent! You have most of the skills "
            "required for this job role."
        )

    elif skill_percentage >= 50:
        message = (
            "Good progress! You have some of the required "
            "skills, but there are still a few areas to improve."
        )

    else:
        message = (
            "You have a significant skill gap. Focus on learning "
            "the missing skills to prepare for this role."
        )

    return render_template(
        "skill_gap.html",
        job_role=job_role,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        skill_percentage=skill_percentage,
        message=message
    )


# =========================
# Learning Recommendations
# =========================

@app.route("/recommendations", methods=["GET", "POST"])
def recommendations():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    job_role_id = (
        request.form.get("job_role_id")
        or request.args.get("job_role_id")
        or session.get("selected_job_role_id")
    )

    if not job_role_id:
        return redirect("/job-role")

    session["selected_job_role_id"] = job_role_id

    db = get_database_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, role_name, required_skills
            FROM job_roles
            WHERE id = %s
            """,
            (job_role_id,)
        )

        job_role = cursor.fetchone()

        if not job_role:
            return "Job Role Not Found"

        cursor.execute(
            """
            SELECT skill_name
            FROM skills
            WHERE user_id = %s
            """,
            (user_id,)
        )

        user_skills = cursor.fetchall()

    finally:
        cursor.close()
        db.close()

    required_skills = [
        skill.strip()
        for skill in (job_role["required_skills"] or "").split(",")
        if skill.strip()
    ]

    current_skills = [
        skill["skill_name"].strip().lower()
        for skill in user_skills
        if skill["skill_name"]
    ]

    missing_skills = [
        skill for skill in required_skills
        if skill.lower() not in current_skills
    ]

    recommendations = [
        {
            "skill": skill,
            "description": (
                "Learn the fundamentals of " + skill
                + " and practice it using hands-on exercises and projects."
            ),
            "resource": (
                "Online courses, official documentation, tutorials "
                "and practical projects."
            )
        }
        for skill in missing_skills
    ]

    if not recommendations:
        recommendations.append(
            {
                "skill": "All Required Skills",
                "description": (
                    "Great job! You currently have all the required "
                    "skills for this job role."
                ),
                "resource": (
                    "Continue practicing and build advanced projects "
                    "to strengthen your skills."
                )
            }
        )

    return render_template(
        "recommendations.html",
        job_role=job_role,
        recommendations=recommendations
    )


# =========================
# Direct Skill Gap
# =========================

@app.route("/skill-gap-direct")
def skill_gap_direct():

    if "user_id" not in session:
        return redirect("/login")

    job_role_id = session.get("selected_job_role_id")

    if not job_role_id:
        return redirect("/job-role")

    return redirect(
        "/skill-gap?job_role_id=" + str(job_role_id)
    )


# =========================
# Direct Recommendations
# =========================

@app.route("/recommendations-direct")
def recommendations_direct():

    if "user_id" not in session:
        return redirect("/login")

    job_role_id = session.get("selected_job_role_id")

    if not job_role_id:
        return redirect("/job-role")

    return redirect(
        "/recommendations?job_role_id=" + str(job_role_id)
    )


# =========================
# Progress Update
# =========================

@app.route("/progress", methods=["GET", "POST"])
def progress():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    job_role_id = session.get("selected_job_role_id")

    if not job_role_id:
        return redirect("/job-role")

    db = get_database_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, role_name, required_skills
            FROM job_roles
            WHERE id = %s
            """,
            (job_role_id,)
        )

        job_role = cursor.fetchone()

        if not job_role:
            return redirect("/job-role")

        required_skills = [
            skill.strip()
            for skill in (job_role["required_skills"] or "").split(",")
            if skill.strip()
        ]

        # Automatically add missing progress rows
        for skill in required_skills:

            cursor.execute(
                """
                SELECT id
                FROM progress
                WHERE user_id = %s
                  AND job_role_id = %s
                  AND LOWER(skill_name) = LOWER(%s)
                """,
                (user_id, job_role_id, skill)
            )

            existing = cursor.fetchone()

            if not existing:
                cursor.execute(
                    """
                    INSERT INTO progress
                    (user_id, job_role_id, skill_name, status)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, job_role_id, skill, "Not Started")
                )

        db.commit()

        # Update selected skill status
        if request.method == "POST":

            skill_name = request.form.get(
                "skill_name", ""
            ).strip()

            status = request.form.get("status")

            allowed_statuses = [
                "Not Started",
                "In Progress",
                "Completed"
            ]

            if (
                skill_name in required_skills
                and status in allowed_statuses
            ):
                cursor.execute(
                    """
                    UPDATE progress
                    SET status = %s
                    WHERE user_id = %s
                      AND job_role_id = %s
                      AND LOWER(skill_name) = LOWER(%s)
                    """,
                    (status, user_id, job_role_id, skill_name)
                )

                db.commit()

            return redirect("/progress")

        cursor.execute(
            """
            SELECT skill_name, status
            FROM progress
            WHERE user_id = %s
              AND job_role_id = %s
            ORDER BY skill_name
            """,
            (user_id, job_role_id)
        )

        progress_list = cursor.fetchall()

        total = len(progress_list)

        completed = sum(
            1 for item in progress_list
            if item["status"] == "Completed"
        )

        percentage = (
            int(completed * 100 / total)
            if total else 0
        )

    finally:
        cursor.close()
        db.close()

    return render_template(
        "progress.html",
        progress_list=progress_list,
        percentage=percentage,
        job_role=job_role
    )


# =========================
# AI Career Guidance
# =========================

@app.route("/ai-career")
def ai_career():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    job_role_id = session.get("selected_job_role_id")

    if not job_role_id:
        return redirect("/job-role")

    db = get_database_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT role_name, required_skills
            FROM job_roles
            WHERE id = %s
            """,
            (job_role_id,)
        )
        job_role = cursor.fetchone()

        cursor.execute(
            """
            SELECT skill_name
            FROM skills
            WHERE user_id = %s
            """,
            (user_id,)
        )
        user_skills = cursor.fetchall()

        cursor.execute(
            """
            SELECT name
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )
        user = cursor.fetchone()

    finally:
        cursor.close()
        db.close()

    if not job_role:
        return redirect("/job-role")

    current_skills = [
        item["skill_name"]
        for item in user_skills
        if item["skill_name"]
    ]

    current_lower = {
        skill.strip().lower()
        for skill in current_skills
    }

    required_skills = [
        skill.strip()
        for skill in (job_role["required_skills"] or "").split(",")
        if skill.strip()
    ]

    missing_skills = [
        skill
        for skill in required_skills
        if skill.lower() not in current_lower
    ]

    guidance = generate_career_guidance(
        student_name=user["name"] if user else "Student",
        current_skills=current_skills,
        job_role=job_role["role_name"],
        missing_skills=missing_skills
    )

    return render_template(
        "ai_career.html",
        job_role=job_role,
        guidance=guidance
    )


# =========================
# AI Learning Roadmap
# =========================

@app.route("/ai-roadmap")
def ai_roadmap():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    job_role_id = session.get("selected_job_role_id")

    if not job_role_id:
        return redirect("/job-role")

    db = get_database_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT role_name, required_skills
            FROM job_roles
            WHERE id = %s
            """,
            (job_role_id,)
        )
        job_role = cursor.fetchone()

        cursor.execute(
            """
            SELECT skill_name
            FROM skills
            WHERE user_id = %s
            """,
            (user_id,)
        )
        user_skills = cursor.fetchall()

        cursor.execute(
            """
            SELECT name
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )
        user = cursor.fetchone()

    finally:
        cursor.close()
        db.close()

    if not job_role:
        return redirect("/job-role")

    current_skills = [
        item["skill_name"]
        for item in user_skills
        if item["skill_name"]
    ]

    current_lower = {
        skill.strip().lower()
        for skill in current_skills
    }

    required_skills = [
        skill.strip()
        for skill in (job_role["required_skills"] or "").split(",")
        if skill.strip()
    ]

    missing_skills = [
        skill
        for skill in required_skills
        if skill.lower() not in current_lower
    ]

    roadmap = generate_learning_roadmap(
        student_name=user["name"] if user else "Student",
        current_skills=current_skills,
        job_role=job_role["role_name"],
        missing_skills=missing_skills
    )

    return render_template(
        "ai_roadmap.html",
        job_role=job_role,
        roadmap=roadmap
    )


# =========================
# Logout
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================
# Run Application
# =========================

if __name__ == "__main__":
    app.run(debug=True)