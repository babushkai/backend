from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2 import pool
import os
import logging

# Logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database connection pool
db_pool = None

def init_db_pool():
    """Initialize the database connection pool."""
    global db_pool
    if db_pool is None:
        try:
            logger.debug("Initializing the database connection pool...")
            db_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=20,
                user=os.getenv('DB_USER', 'user'),
                password=os.getenv('DB_PASSWORD', 'password'),
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', 5432),
                database=os.getenv('DB_NAME', 'database')
            )
            logger.debug("Database connection pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize the database pool: {e}")
            raise

def get_db_connection():
    """Retrieve a connection from the connection pool."""
    global db_pool
    if db_pool is None:
        init_db_pool()
    try:
        return db_pool.getconn()
    except Exception as e:
        logger.error(f"Error getting connection from pool: {e}")
        raise

def release_db_connection(conn):
    """Release a connection back to the connection pool."""
    global db_pool
    if db_pool and conn:
        try:
            db_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Error releasing connection to pool: {e}")

@app.route('/recipes', methods=['GET'])
def get_recipes():
    """Retrieve all recipes."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM recipes")
        recipes = cursor.fetchall()
        cursor.close()
        release_db_connection(conn)
        return jsonify({"recipes": [dict(recipe) for recipe in recipes]}), 200
    except Exception as e:
        logger.error(f"Error retrieving recipes: {e}")
        return jsonify({"message": "No recipes found"}), 500

@app.route('/recipes', methods=['POST'])
def create_recipe():
    """Create a new recipe."""
    try:
        data = request.get_json()
        required_fields = ['title', 'making_time', 'serves', 'ingredients', 'cost']
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Recipe creation failed!"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute(
            """
            INSERT INTO recipes (title, making_time, serves, ingredients, cost)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
            (data['title'], data['making_time'], data['serves'], data['ingredients'], int(data['cost']))
        )
        recipe_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        release_db_connection(conn)
        return jsonify({"message": "Recipe successfully created!", "recipe_id": recipe_id}), 201
    except Exception as e:
        logger.error(f"Error creating recipe: {e}")
        return jsonify({"message": "Recipe creation failed!"}), 500

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    init_db_pool()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 3000)))
