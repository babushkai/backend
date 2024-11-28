from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
import os
import logging

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# データベース初期化
def init_db():
    logger.debug("Initializing database...")
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'recipe_db'),
            connection_timeout=5000
        )
        cursor = conn.cursor()
        
        logger.debug(f"Database connection successful. Host: {os.getenv('DB_HOST', 'localhost')}")
        
        # create.sqlファイルの読み込みと実行
        with open('create.sql', 'r', encoding='utf-8') as file:
            sql_commands = file.read()
            logger.debug("Successfully read create.sql file")
            
        # 複数のSQLコマンドを分割して実行
        for command in sql_commands.split(';'):
            if command.strip():
                logger.debug(f"Executing SQL command: {command[:100]}...")  # 最初の100文字だけログ出力
                cursor.execute(command + ';')
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.debug("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

# データベース接続設定
def get_db_connection():
    logger.debug("Attempting database connection...")
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'recipe_db'),
            connection_timeout=5000
        )
        logger.debug("Database connection successful")
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {str(err)}")
        if err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            logger.info("Database does not exist, attempting to initialize...")
            init_db()
            return get_db_connection()
        raise

# ベースURLへのアクセス処理
@app.route('/', methods=['GET'])
def index():
    return '', 404

# レシピ作成 POST /recipes
@app.route('/recipes', methods=['POST'])
def create_recipe():
    logger.debug("Received POST request to /recipes")
    try:
        # リクエストヘッダーのログ
        logger.debug(f"Request headers: {dict(request.headers)}")
        
        # Content-Typeの確認
        if request.content_type != 'application/json':
            logger.warning(f"Invalid Content-Type: {request.content_type}")
            return jsonify({"message": "Recipe creation failed!"}), 200

        # リクエストボディの生データを確認
        raw_data = request.get_data()
        logger.debug(f"Raw request data: {raw_data}")

        if not request.is_json:
            logger.warning("Request is not JSON")
            return jsonify({"message": "Recipe creation failed!"}), 200

        data = request.get_json()
        logger.debug(f"Parsed JSON data: {data}")
        
        required_fields = ['title', 'making_time', 'serves', 'ingredients', 'cost']
        
        # 各フィールドの値を個別に確認
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing field: {field}")
                return jsonify({"message": "Recipe creation failed!"}), 200
            if not data[field]:
                logger.warning(f"Empty field: {field}")
                return jsonify({"message": "Recipe creation failed!"}), 200
            logger.debug(f"Field {field}: {data[field]}")

        try:
            # costが数値に変換できることを確認
            cost = int(data['cost'])
            if cost <= 0:
                logger.warning("Cost must be positive")
                return jsonify({"message": "Recipe creation failed!"}), 200
        except ValueError:
            logger.warning(f"Invalid cost value: {data['cost']}")
            return jsonify({"message": "Recipe creation failed!"}), 200

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # レシピの挿入
        sql = """INSERT INTO recipes (title, making_time, serves, ingredients, cost)
                VALUES (%s, %s, %s, %s, %s)"""
        values = (
            data['title'],
            data['making_time'],
            data['serves'],
            data['ingredients'],
            cost
        )
        logger.debug(f"Executing SQL: {sql} with values: {values}")
        
        try:
            cursor.execute(sql, values)
            conn.commit()
            
            recipe_id = cursor.lastrowid
            logger.debug(f"Recipe created with ID: {recipe_id}")
            
            # 作成したレシピの取得
            cursor.execute("""SELECT id, title, making_time, serves, ingredients, cost, 
                            created_at, updated_at FROM recipes WHERE id = %s""", (recipe_id,))
            recipe = cursor.fetchone()
            
            if not recipe:
                logger.error("Created recipe not found")
                return jsonify({"message": "Recipe creation failed!"}), 200
                
            logger.debug(f"Successfully created recipe: {recipe}")
            return jsonify({
                "message": "Recipe successfully created!",
                "recipe": [recipe]
            }), 200
            
        except mysql.connector.Error as err:
            logger.error(f"Database error: {err}")
            return jsonify({"message": "Recipe creation failed!"}), 200
            
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"Error creating recipe: {str(e)}", exc_info=True)
        return jsonify({"message": "Recipe creation failed!"}), 200

# 全レシピ取得 GET /recipes
@app.route('/recipes', methods=['GET'])
def get_recipes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""SELECT id, title, making_time, serves, ingredients, cost, 
                         created_at, updated_at FROM recipes""")
        recipes = cursor.fetchall()
        cursor.close()
        conn.close()

        if not recipes:
            return jsonify({"message": "No recipes found"}), 200

        return jsonify({"recipes": recipes}), 200

    except Exception as e:
        return jsonify({"message": "No recipes found"}), 200

# 指定レシピ取得 GET /recipes/{id}
@app.route('/recipes/<int:id>', methods=['GET'])
def get_recipe(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""SELECT id, title, making_time, serves, ingredients, cost, 
                         created_at, updated_at FROM recipes WHERE id = %s""", (id,))
        recipe = cursor.fetchone()
        cursor.close()
        conn.close()

        if recipe:
            return jsonify({
                "message": "Recipe details by id",
                "recipe": [recipe]
            }), 200
        else:
            return jsonify({"message": "No Recipe found"}), 200

    except Exception as e:
        return jsonify({"message": "No Recipe found"}), 200

# レシピ更新 PATCH /recipes/{id}
@app.route('/recipes/<int:id>', methods=['PATCH'])
def update_recipe(id):
    try:
        data = request.get_json()
        required_fields = ['title', 'making_time', 'serves', 'ingredients', 'cost']
        
        if not all(field in data and data[field] for field in required_fields):
            return jsonify({"message": "Recipe update failed!"}), 200

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # レシピの存在確認
        cursor.execute("SELECT id FROM recipes WHERE id = %s", (id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"message": "No Recipe found"}), 200

        # レシピの更新
        sql = """UPDATE recipes 
                SET title = %s, making_time = %s, serves = %s,
                    ingredients = %s, cost = %s
                WHERE id = %s"""
        cursor.execute(sql, (
            data['title'],
            data['making_time'],
            data['serves'],
            data['ingredients'],
            int(data['cost']),
            id
        ))
        
        conn.commit()
        
        # 更新したレシピの取得
        cursor.execute("""SELECT id, title, making_time, serves, ingredients, cost, 
                         created_at, updated_at FROM recipes WHERE id = %s""", (id,))
        recipe = cursor.fetchone()
        
        cursor.close()
        conn.close()

        return jsonify({
            "message": "Recipe successfully updated!",
            "recipe": [recipe]
        }), 200

    except Exception as e:
        print(f"Error updating recipe: {str(e)}")
        return jsonify({"message": "Recipe update failed!"}), 200

# レシピ削除 DELETE /recipes/{id}
@app.route('/recipes/<int:id>', methods=['DELETE'])
def delete_recipe(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # レシピの存在確認
        cursor.execute("SELECT id FROM recipes WHERE id = %s", (id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"message": "No Recipe found"}), 200

        # レシピの削除
        cursor.execute("DELETE FROM recipes WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Recipe successfully removed!"}), 200

    except Exception as e:
        print(f"Error deleting recipe: {str(e)}")
        return jsonify({"message": "No Recipe found"}), 200

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 3000)))
