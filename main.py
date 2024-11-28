from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2 import pool, sql
import os
import logging

# Logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database connection pool
db_pool = None

def ensure_database_and_table():
    """Ensure the database and 'recipes' table exist."""
    try:
        logger.debug("Ensuring the database and 'recipes' table exist...")
        # Connect to the default 'postgres' database
        conn = psycopg2.connect(
            dbname='postgres',
            user=os.getenv('DB_USER', 'user'),
            password=os.getenv('DB_PASSWORD', 'password'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', 5432)
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Check if the database exists
        db_name = os.getenv('DB_NAME', 'database')
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if not cursor.fetchone():
            # Create the database if it does not exist
            logger.info(f"Database '{db_name}' does not exist. Creating...")
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            logger.info(f"Database '{db_name}' created successfully.")
        
        cursor.close()
        conn.close()

        # Connect to the application database to ensure the table exists
        conn = psycopg2.connect(
            dbname=db_name,
            user=os.getenv('DB_USER', 'user'),
            password=os.getenv('DB_PASSWORD', 'password'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', 5432)
        )
        cursor = conn.cursor()

        # Create 'recipes' table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            making_time VARCHAR(255) NOT NULL,
            serves VARCHAR(255) NOT NULL,
            ingredients TEXT NOT NULL,
            cost INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        logger.info("'recipes' table ensured in the database.")
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error ensuring database and table: {e}")
        raise

def init_db_pool():
    """Initialize the database connection pool."""
    global db_pool
    if db_pool is None:
        try:
            logger.debug("Initializing the database connection pool...")
            # Ensure database and table exist
            ensure_database_and_table()

            # Initialize the connection pool
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
        recipe_id = data['id']
        conn.commit()
        cursor.close()
        release_db_connection(conn)
        return jsonify({"message": "Recipe successfully created!", "recipe_id": recipe_id}), 200
    except Exception as e:
        logger.error(f"Error creating recipe: {e}")
        return jsonify({"message": "Recipe creation failed!"}), 500

@app.route('/recipes/<int:recipe_id>', methods=['GET'])
def get_recipe_by_id(recipe_id):
    """Retrieve a specific recipe by ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
        recipe = cursor.fetchone()
        cursor.close()
        release_db_connection(conn)

        if recipe:
            return jsonify({"message": "Recipe details by id", "recipe": [dict(recipe)]}), 200
        else:
            return jsonify({"message": "Recipe not found"}), 404
    except Exception as e:
        logger.error(f"Error retrieving recipe by ID: {e}")
        return jsonify({"message": "Failed to retrieve recipe"}), 500

@app.route('/recipes/<int:recipe_id>', methods=['PATCH'])
def update_recipe(recipe_id):
    """Update a specific recipe by ID."""
    try:
        data = request.get_json()
        update_fields = ['title', 'making_time', 'serves', 'ingredients', 'cost']
        updates = {key: data[key] for key in update_fields if key in data}

        if not updates:
            return jsonify({"message": "No valid fields to update"}), 400

        # Add updated_at explicitly to ensure it gets updated
        updates['updated_at'] = 'CURRENT_TIMESTAMP'

        set_clause = ", ".join(f"{key} = %s" for key in updates.keys())
        query = f"UPDATE recipes SET {set_clause} WHERE id = %s RETURNING *"

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute(query, (*updates.values(), recipe_id))
        updated_recipe = cursor.fetchone()
        conn.commit()
        cursor.close()
        release_db_connection(conn)

        if updated_recipe:
            return jsonify({"message": "Recipe successfully updated", "recipe": dict(updated_recipe)}), 200
        else:
            return jsonify({"message": "Recipe not found"}), 404
    except Exception as e:
        logger.error(f"Error updating recipe by ID: {e}")
        return jsonify({"message": "Failed to update recipe"}), 500


@app.route('/recipes/<int:recipe_id>', methods=['DELETE'])
def delete_recipe(recipe_id):
    """Delete a specific recipe by ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM recipes WHERE id = %s RETURNING id", (recipe_id,))
        deleted_recipe = cursor.fetchone()
        conn.commit()
        cursor.close()
        release_db_connection(conn)

        if deleted_recipe:
            return jsonify({"message": "Recipe successfully deleted"}), 200
        else:
            return jsonify({"message": "Recipe not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting recipe by ID: {e}")
        return jsonify({"message": "Failed to delete recipe"}), 500

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    init_db_pool()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 3000)))
