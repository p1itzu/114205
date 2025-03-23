# app.py

from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector

app = Flask(__name__)

# ----------------------------------------------
# 1) 資料庫連線資訊
# ----------------------------------------------
DB_HOST = '140.131.114.242'       # 你的 MySQL IP
DB_USER = '114205'                # 你的 MySQL 帳號
DB_PASSWORD = '9yW&LLm35w+Z'      # 你的 MySQL 密碼
DB_NAME = '114205'          # 你的資料庫名稱
DB_PORT = 3306                    # 若不是3306再改

def get_db_connection():
    """ 建立並回傳一個新的資料庫連線物件 """
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )

# ----------------------------------------------
# 2) 頁面路由 (渲染 HTML)
# ----------------------------------------------

@app.route('/')
def route_home():
    # 你可以預設進到 NotLogin.html，或跳轉到 AfterLogin.html
    return redirect(url_for('route_not_login'))

@app.route('/NotLogin')
def route_not_login():
    return render_template('NotLogin.html')

@app.route('/AfterLogin')
def route_after_login():
    return render_template('AfterLogin.html')

@app.route('/CancelOrder')
def route_cancel_order():
    return render_template('CancelOrder.html')

@app.route('/Charging')
def route_charging():
    return render_template('Charging.html')

@app.route('/ChefAfterLogin')
def route_chef_after_login():
    return render_template('ChefAfterLogin.html')

@app.route('/ChefLogin')
def route_chef_login():
    return render_template('ChefLogin.html')

@app.route('/ChefMain')
def route_chef_main():
    return render_template('ChefMain.html')

@app.route('/ChefOrder')
def route_chef_order():
    return render_template('ChefOrder.html')

@app.route('/ChefRegister')
def route_chef_register():
    return render_template('ChefRegister.html')

@app.route('/ChefRegister2')
def route_chef_register2():
    return render_template('ChefRegister2.html')

@app.route('/ChefUnOrder')
def route_chef_unorder():
    return render_template('ChefUnOrder.html')

@app.route('/CookingMethod')
def route_cooking_method():
    return render_template('CookingMethod.html')

@app.route('/CusLogin')
def route_cus_login():
    return render_template('CusLogin.html')

@app.route('/CusRegister')
def route_cus_register():
    return render_template('CusRegister.html')

@app.route('/CustomerLogin')
def route_customer_login():
    return render_template('CustomerLogin.html')

@app.route('/evaluate')
def route_evaluate():
    return render_template('evaluate.html')

@app.route('/my-order')
def route_my_order():
    return render_template('my-order.html')

@app.route('/Order')
def route_order():
    return render_template('Order.html')

@app.route('/orderDetail')
def route_order_detail():
    return render_template('orderDetail.html')

@app.route('/orderDetail2')
def route_order_detail2():
    return render_template('orderDetail2.html')

@app.route('/orderDetail3')
def route_order_detail3():
    return render_template('orderDetail3.html')

@app.route('/OrderDone')
def route_order_done():
    return render_template('OrderDone.html')

@app.route('/OrderPrice')
def route_order_price():
    return render_template('OrderPrice.html')

@app.route('/reserve')
def route_reserve():
    return render_template('reserve.html')

@app.route('/reserve2_change')
def route_reserve2_change():
    return render_template('reserve2-change.html')

@app.route('/reserve2')
def route_reserve2():
    return render_template('reserve2.html')

@app.route('/reserve3')
def route_reserve3():
    return render_template('reserve3.html')

@app.route('/reserve4')
def route_reserve4():
    return render_template('reserve4.html')

@app.route('/SearchChef')
def route_search_chef():
    return render_template('SearchChef.html')


# ----------------------------------------------
# 3) 範例 API (GET/POST), 後續可再擴充
# ----------------------------------------------
# @app.route('/api/test-get', methods=['GET'])
# def api_test_get():
#     """
#     範例：從資料庫取資料 (假設有個 test_table)
#     """
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)
#         cursor.execute("SELECT id, name FROM test_table LIMIT 10")
#         rows = cursor.fetchall()
#         return jsonify({"data": rows}), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()

# @app.route('/api/test-post', methods=['POST'])
# def api_test_post():
#     """
#     範例：接收前端提交的 JSON，插入資料庫
#     Body JSON: {"name": "xxx"}
#     """
#     data = request.get_json()
#     name_val = data.get("name", "")
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "INSERT INTO test_table (name) VALUES (%s)"
#         cursor.execute(sql, (name_val,))
#         conn.commit()
#         return jsonify({"message": "success", "insert_id": cursor.lastrowid}), 201
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()

# ----------------------------------------------
# 4) 主程式入口
# ----------------------------------------------
if __name__ == '__main__':
    # debug=True: 方便開發時即時查看變動
    # host='0.0.0.0': 讓外部可以訪問 (如你虛擬機 IP)
    app.run(host='0.0.0.0', port=5000, debug=True)
