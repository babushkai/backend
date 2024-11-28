from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
import os

app = Flask(__name__)

# データベース接続設定
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'recipe_db'),
        connection_timeout=5000  # タイムアウト設定を追加
    )

# ベースURLへのアクセス処理を追加
@app.route('/', methods=['GET'])
def index():
    return '', 404

# レシピ作成 POST /recipes
@app.route('/recipes', methods=['POST'])
def create_recipe():
    try:
        if not request.is_json:
            return jsonify({"message": "Recipe creation failed!"}), 200

        data = request.get_json()
        required_fields = ['title', 'making_time', 'serves', 'ingredients', 'cost']
        
        # 必須フィールドの確認
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Recipe creation failed!"}), 200

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # レシピの挿入
        sql = """INSERT INTO recipes (title, making_time, serves, ingredients, cost)
                VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(sql, (
            data['title'],
            data['making_time'],
            data['serves'],
            data['ingredients'],
            int(data['cost'])  # costを整数に変換
        ))
        
        # 作成したレシピの取得
        recipe_id = cursor.lastrowid
        cursor.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
        recipe = cursor.fetchone()
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "message": "Recipe successfully created!",
            "recipe": [recipe]
        }), 200

    except Exception as e:
        print(f"Error creating recipe: {str(e)}")  # エラーログを追加
        return jsonify({"message": "Recipe creation failed!"}), 200

# 全レシピ取得 GET /recipes
@app.route('/recipes', methods=['GET'])
def get_recipes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM recipes")
        recipes = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({"recipes": recipes}), 200

    except Exception as e:
        return jsonify({"message": "No recipes found"}), 404

# 指定レシピ取得 GET /recipes/{id}
@app.route('/recipes/<int:id>', methods=['GET'])
def get_recipe(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM recipes WHERE id = %s", (id,))
        recipe = cursor.fetchone()
        cursor.close()
        conn.close()

        if recipe:
            return jsonify({
                "message": "Recipe details by id",
                "recipe": [recipe]
            }), 200
        else:
            return jsonify({"message": "No Recipe found"}), 404

    except Exception as e:
        return jsonify({"message": "No Recipe found"}), 404

# レシピ更新 PATCH /recipes/{id}
@app.route('/recipes/<int:id>', methods=['PATCH'])
def update_recipe(id):
    try:
        data = request.get_json()
        required_fields = ['title', 'making_time', 'serves', 'ingredients', 'cost']

        if not all(field in data for field in required_fields):
            return jsonify({"message": "Recipe update failed!"}), 200

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

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
            data['cost'],
            id
        ))

        if cursor.rowcount > 0:
            # 更新したレシピの取得
            cursor.execute("SELECT * FROM recipes WHERE id = %s", (id,))
            recipe = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({
                "message": "Recipe successfully updated!",
                "recipe": [recipe]
            }), 200
        else:
            return jsonify({"message": "No Recipe found"}), 404

    except Exception as e:
        return jsonify({"message": "Recipe update failed!"}), 200

# レシピ削除 DELETE /recipes/{id}
@app.route('/recipes/<int:id>', methods=['DELETE'])
def delete_recipe(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM recipes WHERE id = %s", (id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"message": "No Recipe found"}), 404

        cursor.execute("DELETE FROM recipes WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Recipe successfully removed!"}), 200

    except Exception as e:
        return jsonify({"message": "No Recipe found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 3000)))
