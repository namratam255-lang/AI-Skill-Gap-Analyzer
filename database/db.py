import mysql.connector


def get_database_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="ai_skill_gap_analyzer"
    )

    return connection