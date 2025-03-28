from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector
import json
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ----------------------------------------------
# 資料庫連線資訊
# ----------------------------------------------
DB_HOST = '140.131.114.242'       # 你的 MySQL IP
DB_USER = '114205'                # 你的 MySQL 帳號
DB_PASSWORD = '9yW&LLm35w+Z'      # 你的 MySQL 密碼
DB_NAME = '114-205'          # 你的資料庫名稱
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
# 頁面路由 (渲染 HTML)
# ----------------------------------------------

@app.route('/')
def route_home():
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
# API (GET/POST), 後續可再擴充
# ----------------------------------------------
# Chef 註冊 API
@app.route('/api/register_chef', methods=['POST'])
def register_chef():
    """
    廚師註冊 API
    支援即時檢查 Email 和電話是否已被註冊，並處理完整的註冊流程
    """
    conn = None
    cursor = None
    try:
        # 檢查請求的 Content-Type
        if request.content_type == 'application/json':
            data = request.get_json()  # JSON 請求
        else:
            data = request.form  # 表單請求

        check_only = data.get('check_only', False)

        # 即時檢查模式
        if check_only:
            email = data.get('email')
            phone = data.get('phone')

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if email:
                cursor.execute("SELECT * FROM Chef WHERE email = %s", (email,))
                exists = cursor.fetchone() is not None
                return jsonify({'exists': exists}), 200

            if phone:
                cursor.execute("SELECT * FROM Chef WHERE phone = %s", (phone,))
                exists = cursor.fetchone() is not None
                return jsonify({'exists': exists}), 200

            return jsonify({'error': '請提供 Email 或電話進行檢查'}), 400

        # 正常註冊模式
        username = data.get('name')
        email = data.get('email')
        password = data.get('password')
        phone = data.get('phone')
        service_areas = data.getlist('service_areas') if not request.is_json else data.get('service_areas', [])
        specialties = data.getlist('specialties') if not request.is_json else data.get('specialties', [])
        kitchen_address = data.get('kitchen_address')

        # 驗證輸入資料
        if not username or not email or not password or not phone or not kitchen_address:
            return jsonify({'error': '所有欄位都是必填的，請檢查輸入內容！'}), 400

        if not service_areas:
            return jsonify({'error': '請至少選擇一個服務地區！'}), 400

        if not specialties:
            return jsonify({'error': '請至少選擇一個擅長領域！'}), 400

        # 建立資料庫連線
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 生成帶前綴的 ID（廚師 ID 以 2 開頭）
        cursor.execute("SELECT MAX(CAST(SUBSTRING(id, 2) AS UNSIGNED)) FROM Chef")
        max_id = cursor.fetchone()['MAX(CAST(SUBSTRING(id, 2) AS UNSIGNED))'] or 0
        chef_id = f"2{max_id + 1:03d}"

        # 儲存廚師證照檔案
        file = request.files.get('certificate')
        certificate_path = None
        if file:
            # 獲取原始檔案名稱和副檔名
            original_filename = file.filename
            file_extension = os.path.splitext(original_filename)[1]  # 取得副檔名（例如 .png, .jpg）

            # 生成新的檔案名稱，格式為 "ID_原始檔案名稱"
            new_filename = f"{chef_id}_{original_filename}"

            # 儲存檔案到指定目錄
            certificate_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(certificate_path)

        # 插入資料庫
        sql = """
            INSERT INTO Chef (id, username, email, password, phone, service_areas, certificate_path, specialties, kitchen_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            chef_id,
            username,
            email,
            password,
            phone,
            json.dumps(service_areas),  # 將多選框轉為 JSON 字串存入資料庫
            certificate_path,
            json.dumps(specialties),  # 將多選框轉為 JSON 字串存入資料庫
            kitchen_address
        ))
        conn.commit()

        # 返回成功訊息和重定向 URL
        return jsonify({'message': '廚師註冊成功！', 'redirect_url': url_for('route_chef_login')}), 201
    except Exception as e:
        return jsonify({'error': f'伺服器內部錯誤：{str(e)}，請稍後再試！'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 顧客註冊 API
@app.route('/api/register_customer', methods=['POST'])
def register_customer():
    """
    顧客註冊 API
    接收表單資料，將顧客資訊存入資料庫
    """
    conn = None
    cursor = None
    try:
        # 從請求中獲取資料
        data = request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        phone = data.get('phone')

        # 驗證輸入資料
        if not username or not email or not password or not phone:
            return jsonify({'error': '所有欄位都是必填的，請檢查輸入內容！'}), 400

        # 檢查 Email 或電話是否已被註冊
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Customer WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'error': '此 Email 已被註冊，請使用其他 Email！'}), 400

        cursor.execute("SELECT * FROM Customer WHERE phone = %s", (phone,))
        if cursor.fetchone():
            return jsonify({'error': '此電話號碼已被使用，請使用其他電話號碼！'}), 400

        # 生成帶前綴的 ID（顧客 ID 以 1 開頭）
        cursor.execute("SELECT MAX(CAST(SUBSTRING(id, 2) AS UNSIGNED)) FROM Customer")
        max_id = cursor.fetchone()['MAX(CAST(SUBSTRING(id, 2) AS UNSIGNED))'] or 0
        customer_id = f"1{max_id + 1:03d}"

        # 插入資料庫
        sql = """
            INSERT INTO Customer (id, username, email, password, phone)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (customer_id, username, email, password, phone))
        conn.commit()

        # 返回成功訊息和重定向 URL
        return jsonify({'message': '顧客註冊成功！', 'redirect_url': url_for('route_cus_login')}), 201
    except Exception as e:
        return jsonify({'error': f'伺服器內部錯誤：{str(e)}，請稍後再試！'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 廚師登入 API
@app.route('/api/login_chef', methods=['POST'])
def login_chef():
    """
    廚師登入 API
    驗證 Email 和密碼，成功後返回登入狀態
    """
    conn = None
    cursor = None
    try:
        # 從請求中獲取資料
        data = request.form
        email = data.get('email')  # 使用 Email 作為登入帳號
        password = data.get('password')  # 密碼比對

        # 驗證輸入資料
        if not email or not password:
            return jsonify({'error': 'Email 和密碼都是必填的，請檢查輸入內容！'}), 400

        # 查詢資料庫
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM Chef WHERE email = %s"
        cursor.execute(sql, (email,))
        chef = cursor.fetchone()

        # 檢查 Email 是否存在
        if not chef:
            return jsonify({'error': '此 Email 尚未註冊，請確認輸入的 Email 是否正確！'}), 404

        # 驗證密碼
        if chef['password'] != password:
            return jsonify({'error': '密碼錯誤，請重新輸入！'}), 401

        return jsonify({'message': '登入成功！', 'id': chef['id']}), 200
    except Exception as e:
        return jsonify({'error': f'伺服器內部錯誤：{str(e)}，請稍後再試！'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 顧客登入 API
@app.route('/api/login_customer', methods=['POST'])
def login_customer():
    """
    顧客登入 API
    驗證 Email 和密碼，成功後返回登入狀態
    """
    conn = None
    cursor = None
    try:
        # 從請求中獲取資料
        data = request.form
        email = data.get('email')  # 使用 Email 作為登入帳號
        password = data.get('password')  # 密碼比對

        # 驗證輸入資料
        if not email or not password:
            return jsonify({'error': 'Email 和密碼都是必填的，請檢查輸入內容！'}), 400

        # 查詢資料庫
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM Customer WHERE email = %s"
        cursor.execute(sql, (email,))
        customer = cursor.fetchone()

        # 檢查 Email 是否存在
        if not customer:
            return jsonify({'error': '此 Email 尚未註冊，請確認輸入的 Email 是否正確！'}), 404

        # 驗證密碼
        if customer['password'] != password:
            return jsonify({'error': '密碼錯誤，請重新輸入！'}), 401

        return jsonify({'message': '登入成功！', 'id': customer['id']}), 200
    except Exception as e:
        return jsonify({'error': f'伺服器內部錯誤：{str(e)}，請稍後再試！'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ----------------------------------------------
# 主程式入口
# ----------------------------------------------
if __name__ == '__main__':
    # debug=True: 方便開發時即時查看變動
    # host='0.0.0.0': 讓外部可以訪問 (如你虛擬機 IP)
    app.run(host='0.0.0.0', port=5000, debug=True)
