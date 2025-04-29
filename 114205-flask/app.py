from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import mysql.connector
import json
import os
import secrets  # 用於生成安全的 secret key
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # 設定安全的 secret key

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
# 登入檢查裝飾器
# ----------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('route_not_login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------------------------------------
# 獲取當前登入用戶的資訊
# ----------------------------------------------

def get_user_info():
    """獲取當前登入用戶的資訊"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if session.get('user_type') == 'customer':
            cursor.execute("SELECT username, phone FROM Customer WHERE email = %s", (session.get('user_email'),))
        else:  # chef
            cursor.execute("SELECT username, phone FROM Chef WHERE email = %s", (session.get('user_email'),))
            
        result = cursor.fetchone()
        return {
            'username': result['username'] if result else '',
            'phone': result['phone'] if result else ''
        }
    except Exception as e:
        print(f"Error getting user info: {str(e)}")
        return {'username': '', 'phone': ''}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

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
@login_required
def route_after_login():
    user_info = get_user_info()
    return render_template('AfterLogin.html', 
                         user_email=session.get('user_email'),
                         username=user_info['username'],
                         phone=user_info['phone'])

@app.route('/CancelOrder')
@login_required
def route_cancel_order():
    username = get_user_info()['username']
    return render_template('CancelOrder.html', user_email=session.get('user_email'), username=username)

@app.route('/Charging')
@login_required
def route_charging():
    username = get_user_info()['username']
    return render_template('Charging.html', user_email=session.get('user_email'), username=username)

@app.route('/ChefAfterLogin')
@login_required
def route_chef_after_login():
    username = get_user_info()['username']
    return render_template('ChefAfterLogin.html', user_email=session.get('user_email'), username=username)

@app.route('/ChefLogin')
def route_chef_login():
    return render_template('ChefLogin.html')

@app.route('/ChefMain')
@login_required
def route_chef_main():
    username = get_user_info()['username']
    return render_template('ChefMain.html', user_email=session.get('user_email'), username=username)

@app.route('/ChefOrder')
@login_required
def route_chef_order():
    username = get_user_info()['username']
    return render_template('ChefOrder.html', user_email=session.get('user_email'), username=username)

@app.route('/ChefRegister')
def route_chef_register():
    return render_template('ChefRegister.html')

@app.route('/ChefRegister2')
def route_chef_register2():
    return render_template('ChefRegister2.html')

@app.route('/ChefUnOrder')
@login_required
def route_chef_unorder():
    username = get_user_info()['username']
    return render_template('ChefUnOrder.html', user_email=session.get('user_email'), username=username)

@app.route('/CookingMethod')
@login_required
def route_cooking_method():
    username = get_user_info()['username']
    return render_template('CookingMethod.html', user_email=session.get('user_email'), username=username)

@app.route('/CusLogin')
def route_cus_login():
    return render_template('CusLogin.html')

@app.route('/CusRegister')
def route_cus_register():
    return render_template('CusRegister.html')

@app.route('/evaluate')
@login_required
def route_evaluate():
    username = get_user_info()['username']
    return render_template('evaluate.html', user_email=session.get('user_email'), username=username)

@app.route('/my-order')
@login_required
def route_my_order():
    username = get_user_info()['username']
    return render_template('my-order.html', user_email=session.get('user_email'), username=username)

@app.route('/Order')
@login_required
def route_order():
    username = get_user_info()['username']
    return render_template('Order.html', user_email=session.get('user_email'), username=username)

@app.route('/Order1')
@login_required
def route_order1():
    username = get_user_info()['username']
    return render_template('Order1.html', user_email=session.get('user_email'), username=username)

@app.route('/OrderfinalPrice')
@login_required
def route_order_final_price():
    username = get_user_info()['username']
    return render_template('OrderfinalPrice.html', user_email=session.get('user_email'), username=username)

@app.route('/OrderfinalPrice1')
@login_required
def route_order_final_price1():
    username = get_user_info()['username']
    return render_template('OrderfinalPrice1.html', user_email=session.get('user_email'), username=username)

@app.route('/PriceRules')
@login_required
def route_price_rules():
    username = get_user_info()['username']
    return render_template('PriceRules.html', user_email=session.get('user_email'), username=username)

@app.route('/orderDetail')
@login_required
def route_order_detail():
    username = get_user_info()['username']
    return render_template('orderDetail.html', user_email=session.get('user_email'), username=username)

@app.route('/orderDetail2')
@login_required
def route_order_detail2():
    username = get_user_info()['username']
    return render_template('orderDetail2.html', user_email=session.get('user_email'), username=username)

@app.route('/orderDetail3')
@login_required
def route_order_detail3():
    username = get_user_info()['username']
    return render_template('orderDetail3.html', user_email=session.get('user_email'), username=username)

@app.route('/OrderDone')
@login_required
def route_order_done():
    username = get_user_info()['username']
    return render_template('OrderDone.html', user_email=session.get('user_email'), username=username)

@app.route('/OrderPrice')
@login_required
def route_order_price():
    username = get_user_info()['username']
    return render_template('OrderPrice.html', user_email=session.get('user_email'), username=username)

@app.route('/reserve')
@login_required
def route_reserve():
    username = get_user_info()['username']
    return render_template('reserve.html', user_email=session.get('user_email'), username=username)

@app.route('/reserve2_change')
@login_required
def route_reserve2_change():
    username = get_user_info()['username']
    return render_template('reserve2-change.html', user_email=session.get('user_email'), username=username)

@app.route('/reserve2')
@login_required
def route_reserve2():
    username = get_user_info()['username']
    return render_template('reserve2.html', user_email=session.get('user_email'), username=username)

@app.route('/reserve3')
@login_required
def route_reserve3():
    username = get_user_info()['username']
    return render_template('reserve3.html', user_email=session.get('user_email'), username=username)

@app.route('/reserve4')
@login_required
def route_reserve4():
    username = get_user_info()['username']
    return render_template('reserve4.html', user_email=session.get('user_email'), username=username)

@app.route('/SearchChef')
@login_required
def route_search_chef():
    username = get_user_info()['username']
    return render_template('SearchChef.html', user_email=session.get('user_email'), username=username)

# ----------------------------------------------
# API (GET/POST)
# ----------------------------------------------
#  廚師註冊 API
@app.route('/api/register_chef', methods=['POST'])
def register_chef():
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

# 顧客登入 API
@app.route('/api/login_customer', methods=['POST'])
def login_customer():
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

        # 儲存用戶資訊到 session
        session['user_type'] = 'customer'
        session['user_email'] = customer['email']
        session['user_id'] = customer['id']

        return jsonify({'message': '登入成功！', 'id': customer['id']}), 200
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

        # 儲存用戶資訊到 session
        session['user_type'] = 'chef'
        session['user_email'] = chef['email']
        session['user_id'] = chef['id']

        return jsonify({'message': '登入成功！', 'id': chef['id']}), 200
    except Exception as e:
        return jsonify({'error': f'伺服器內部錯誤：{str(e)}，請稍後再試！'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 登出 API
@app.route('/api/logout', methods=['POST'])
def logout(): 
    session.clear()
    return jsonify({'message': '登出成功！', 'redirect_url': url_for('route_not_login')}), 200

# 刪除帳號 API 
@app.route('/api/delete_account', methods=['POST'])
@login_required
def delete_account():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        user_type = session.get('user_type')
        user_email = session.get('user_email')
        
        if user_type == 'customer':
            # 檢查是否有未完成的訂單
            # cursor.execute("SELECT COUNT(*) as count FROM Orders WHERE customer_email = %s AND status != 'completed'", (user_email,))
            # result = cursor.fetchone()
            # if result and result['count'] > 0:
            #     return jsonify({'error': '您有未完成的訂單，無法刪除帳號！'}), 400
                
            # 刪除顧客資料
            cursor.execute("DELETE FROM Customer WHERE email = %s", (user_email,))
            
        else:  # chef
            # 檢查是否有未完成的訂單
            # cursor.execute("SELECT COUNT(*) as count FROM Orders WHERE chef_email = %s AND status != 'completed'", (user_email,))
            # result = cursor.fetchone()
            # if result and result['count'] > 0:
            #     return jsonify({'error': '您有未完成的訂單，無法刪除帳號！'}), 400
                
            # 刪除廚師資料
            cursor.execute("DELETE FROM Chef WHERE email = %s", (user_email,))
        
        conn.commit()
        session.clear()
        
        return jsonify({
            'message': '帳號已成功刪除！',
            'redirect_url': url_for('route_not_login')
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'刪除帳號時發生錯誤：{str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 更新個人資料 API
@app.route('/api/update_profile', methods=['POST'])
@login_required
def update_profile():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        phone = data.get('phone')
        password = data.get('password')
        
        # 驗證必填欄位
        if not all([username, email, phone]):
            return jsonify({'error': '姓名、電子郵件和電話都是必填欄位！'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        user_type = session.get('user_type')
        current_email = session.get('user_email')
        
        # 檢查新的 email 是否已被其他用戶使用
        if email != current_email:
            if user_type == 'customer':
                cursor.execute("SELECT id FROM Customer WHERE email = %s AND email != %s", (email, current_email))
            else:
                cursor.execute("SELECT id FROM Chef WHERE email = %s AND email != %s", (email, current_email))
            if cursor.fetchone():
                return jsonify({'error': '此電子郵件已被使用！'}), 400
        
        # 檢查新的電話是否已被其他用戶使用
        if user_type == 'customer':
            cursor.execute("SELECT id FROM Customer WHERE phone = %s AND email != %s", (phone, current_email))
        else:
            cursor.execute("SELECT id FROM Chef WHERE phone = %s AND email != %s", (phone, current_email))
        if cursor.fetchone():
            return jsonify({'error': '此電話號碼已被使用！'}), 400
            
        # 更新資料
        if user_type == 'customer':
            if password:
                cursor.execute("""
                    UPDATE Customer 
                    SET username = %s, email = %s, phone = %s, password = %s 
                    WHERE email = %s
                """, (username, email, phone, password, current_email))
            else:
                cursor.execute("""
                    UPDATE Customer 
                    SET username = %s, email = %s, phone = %s 
                    WHERE email = %s
                """, (username, email, phone, current_email))
        else:  # chef
            if password:
                cursor.execute("""
                    UPDATE Chef 
                    SET username = %s, email = %s, phone = %s, password = %s 
                    WHERE email = %s
                """, (username, email, phone, password, current_email))
            else:
                cursor.execute("""
                    UPDATE Chef 
                    SET username = %s, email = %s, phone = %s 
                    WHERE email = %s
                """, (username, email, phone, current_email))
        
        conn.commit()
        
        # 更新 session 中的 email
        if email != current_email:
            session['user_email'] = email
            
        return jsonify({
            'message': '個人資料更新成功！',
            'new_email': email
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'更新個人資料時發生錯誤：{str(e)}'}), 500
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
