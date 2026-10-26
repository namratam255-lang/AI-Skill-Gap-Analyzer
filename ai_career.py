
import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from the main project .env file
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

client = None

if API_KEY:
    client = genai.Client(
        api_key=API_KEY,
        http_options={"timeout": 30000}
    )


def generate_ai_response(prompt):
    """
    Generate an AI response using Gemini.
    Display detailed errors in the terminal.
    """

    if client is None:
        print("ERROR: GEMINI_API_KEY was not found.", flush=True)

        return (
            "Gemini API key was not found. "
            "Please check your main project .env file."
        )

    try:
        print("Connecting to Gemini API...", flush=True)

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt
        )

        if response.text:
            print("Gemini response generated successfully.", flush=True)
            return response.text

        print("ERROR: Gemini returned an empty response.", flush=True)

        return (
            "Gemini could not generate a response. "
            "Please try again."
        )

    except Exception as error:
        print("Gemini API Error:", repr(error), flush=True)

        return (
            "AI service is temporarily unavailable. "
            "Please check the Flask terminal for the exact error."
        )


def generate_career_guidance(
    student_name,
    current_skills,
    job_role,
    missing_skills
):
    """
    Generate personalized career guidance.
    """

    skills_text = (
        ", ".join(current_skills)
        if current_skills
        else "No skills added yet"
    )

    missing_text = (
        ", ".join(missing_skills)
        if missing_skills
        else "No missing skills identified"
    )

    prompt = f"""
You are an AI career guidance assistant for students.

Student name: {student_name}
Current skills: {skills_text}
Target job role: {job_role}
Missing skills: {missing_text}

Provide personalized career guidance in simple English.

Use these headings:

1. Career Overview
2. Current Skill Strengths
3. Skills to Improve
4. Practical Project Suggestions
5. Next Steps

Give realistic and beginner-friendly advice.
Do not claim that the student is guaranteed to get a job.
Keep the response clear and easy to understand.
"""

    return generate_ai_response(prompt)


def generate_learning_roadmap(
    student_name,
    current_skills,
    job_role,
    missing_skills
):
    """
    Generate a personalized learning roadmap.
    """

    skills_text = (
        ", ".join(current_skills)
        if current_skills
        else "No skills added yet"
    )

    missing_text = (
        ", ".join(missing_skills)
        if missing_skills
        else "No missing skills identified"
    )

    prompt = f"""
You are an AI learning roadmap assistant.

Student name: {student_name}
Current skills: {skills_text}
Target job role: {job_role}
Missing skills: {missing_text}

Create a personalized learning roadmap in simple English.

Include these headings:

1. Learning Goal
2. Step-by-Step Learning Plan
3. Practice Activities
4. Mini Project Ideas
5. How to Check Progress

Arrange missing skills in a sensible learning order.
Suggest free learning resources where possible.
Keep the plan practical for a beginner.
If no skills are missing, suggest advanced practice and projects.
Do not guarantee employment.
"""

    return generate_ai_response(prompt)
