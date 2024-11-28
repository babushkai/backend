from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import DictCursor
import os
import logging
import time

# Logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database connection pool (improved performance)
db_pool = None

def init_db():
    logger.debug("Initializing database...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Read and execute SQL commands from the file
        with open(os.path.join(os.path.dirname(__file__), 'create.sql'), 'r', encoding='utf-8') as file:
            sql_commands = file.read()
            logger.debug("Successfully read create.sql file")
        
        for command in sql_commands.split(';'):
            if command.strip():
                try:
                    cursor.execute(command.strip() + ';')
                except psycopg2.Error as e:
                    logger.warning(f"Error executing SQL: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.debug("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def get_db_connection():
    global db_pool
    if db_pool is None:
        logger.debug("Setting up database connection pool...")
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'user'),
            password=os.getenv('DB_PASSWORD', 'password'),
            dbname=os.getenv('DB_NAME', 'database'),
            port=int(os.getenv('DB_PORT', 5432))
        )
    return db_pool.getconn()

def release_db_connection(conn):
    global db_pool
    if db_pool:
        db_pool.putconn(conn)

@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "Recipe API is running!"}), 200

@app.route('/health', methods=['GET'])
def health_check():
    try:
        conn = get_db_connection()
        release_db_connection(conn)
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy"}), 500

@app.route('/recipes', methods=['POST'])
def create_recipe():
    try:
        data = request.get_json()
        required_fields = ['title', 'making_time', 'serves', 'ingredients', 'cost']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"message": "Recipe creation failed!"}), 400

        try:
            cost = int(data['cost'])
            if cost <= 0:
                return jsonify({"message": "Recipe creation failed!"}), 400
        except ValueError:
            return jsonify({"message": "Invalid cost value!"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)

        sql = """INSERT INTO recipes (title, making_time, serves, ingredients, cost) 
                 VALUES (%s, %s, %s, %s, %s) RETURNING id"""
        cursor.execute(sql, (data['title'], data['making_time'], data['serves'], data['ingredients'], cost))
        recipe_id = cursor.fetchone()['id']
        conn.commit()

        cursor.execute("""SELECT * FROM recipes WHERE id = %s""", (recipe_id,))
        recipe = cursor.fetchone()
        cursor.close()
        release_db_connection(conn)

        return jsonify({
            "message": "Recipe successfully created!",
            "recipe": dict(recipe)
        }), 201

    except Exception as e:
        logger.error(f"Error creating recipe: {e}")
        return jsonify({"message": "Recipe creation failed!"}), 500

@app.route('/recipes', methods=['GET'])
def get_recipes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("""SELECT * FROM recipes""")
        recipes = cursor.fetchall()
        cursor.close()
        release_db_connection(conn)

        return jsonify({"recipes": [dict(recipe) for recipe in recipes]}), 200
    except Exception as e:
        logger.error(f"Error retrieving recipes: {e}")
        return jsonify({"message": "No recipes found"}), 500

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    init_db()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 3000)))
