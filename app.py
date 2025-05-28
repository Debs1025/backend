from flask import Flask, request, jsonify
from flask_cors import CORS
from controllers.userController import UserController
from controllers.transactionController import TransactionController
from database.connection import create_connection
from functools import wraps
import jwt
from flask_socketio import SocketIO, emit, join_room 
from datetime import datetime, timedelta
from decimal import Decimal
import json

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
app.config['SECRET_KEY'] = '1025'

# Initialize controllers
user_controller = UserController()
transaction_controller = TransactionController()

# Socket event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    return True

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_shop_room')
def handle_join_shop(data):
    shop_id = data.get('shop_id')
    if shop_id:
        join_room(f"shop_{shop_id}")
        emit('room_joined', {'room': f"shop_{shop_id}"})
        print(f"Shop {shop_id} joined room")

@socketio.on('join_user_room')
def handle_join_user(data):
    user_id = data.get('user_id')
    if user_id:
        join_room(f"user_{user_id}")
        emit('room_joined', {'room': f"user_{user_id}"})
        print(f"User {user_id} joined room")

# JWT decorator for protected routes
def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
            
        try:
            if ' ' not in token:
                return jsonify({'message': 'Invalid token format'}), 401
                
            scheme, token = token.split(' ')
            if scheme.lower() != 'bearer':
                return jsonify({'message': 'Invalid authentication scheme'}), 401

            # Debug prints
            print(f"Debug - Token being decoded: {token}")
            print(f"Debug - Secret key being used: {app.config['SECRET_KEY']}")
            
            data = jwt.decode(
                token, 
                app.config['SECRET_KEY'],
                algorithms=["HS256"]
            )
            
            print(f"Debug - Decoded token data: {data}")
            
            request.user = data
            return f(*args, **kwargs)
            
        except jwt.InvalidTokenError as e:
            print(f"Debug - Token error: {str(e)}")
            return jsonify({'message': f'Token is invalid: {str(e)}'}), 401
            
    return decorated

@app.route('/verify_token', methods=['POST'])
def verify_token():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'valid': False, 'message': 'No token provided'}), 401
        
    try:
        scheme, token = token.split(' ')
        if scheme.lower() != 'bearer':
            return jsonify({'valid': False, 'message': 'Invalid token format'}), 401
            
        decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        return jsonify({
            'valid': True,
            'user_id': decoded.get('user_id'),
            'email': decoded.get('email')
        })
    except Exception as e:
        return jsonify({'valid': False, 'message': str(e)}), 401

# User Routes
@app.route('/signup', methods=['POST'])
def signup():
    try:
        result = user_controller.signup(request.json)
        return jsonify(result), result['status']
    except Exception as e:
        return jsonify({'status': 500, 'message': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        result = user_controller.login(request.json)
        return jsonify(result), result['status']
    except Exception as e:
        return jsonify({'status': 500, 'message': str(e)}), 500

@app.route('/user/<int:user_id>', methods=['GET'])
@jwt_required
def get_user(user_id):
    try:
        result = user_controller.get_user_details(user_id)
        return jsonify(result), result['status']
    except Exception as e:
        return jsonify({'status': 500, 'message': str(e)}), 500

@app.route('/update_user_details/<int:user_id>', methods=['PUT'])
@jwt_required
def update_user_details(user_id):
    try:
        result = user_controller.update_profile(user_id, request.json)
        return jsonify(result), result['status']
    except Exception as e:
        return jsonify({'status': 500, 'message': str(e)}), 500

@app.route('/update_password/<int:user_id>', methods=['PUT'])
@jwt_required
def update_password(user_id):
    try:
        result = user_controller.update_password(user_id, request.json)
        return jsonify(result), result['status']
    except Exception as e:
        return jsonify({'status': 500, 'message': str(e)}), 500

@app.route('/delete_account/<int:user_id>', methods=['DELETE'])
@jwt_required
def delete_account(user_id):
    result = user_controller.delete_account(user_id)
    return jsonify(result), result['status']


# Shop Routes
@app.route('/register_shop/<int:user_id>', methods=['POST'])
@jwt_required
def register_shop(user_id):
    connection = None
    try:
        data = request.json
        if not data:
            return jsonify({'status': 400, 'message': 'No data provided'}), 400

        # Update required fields (remove services)
        required_fields = ['shop_name', 'contact_number', 'zone', 'street', 
                         'barangay', 'opening_time', 'closing_time']
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 400, 
                    'message': f'Missing required field: {field}'
                }), 400

        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Create shop without services
        shop_query = """
            INSERT INTO shops (
                user_id, shop_name, contact_number, zone, street, 
                barangay, building, opening_time, closing_time
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(shop_query, (
            user_id,
            data['shop_name'],
            data['contact_number'],
            data['zone'],
            data['street'],
            data['barangay'],
            data.get('building'),
            data['opening_time'],
            data['closing_time']
        ))
        
        shop_id = cursor.lastrowid

        # Update user to shop owner
        cursor.execute(
            "UPDATE users SET is_shop_owner = TRUE WHERE id = %s",
            (user_id,)
        )
        
        connection.commit()
        return jsonify({
            'status': 201,
            'message': 'Shop registered successfully',
            'shop_id': shop_id
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'status': 500, 'message': f'Error: {str(e)}'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shops', methods=['GET'])
def get_shops():
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT s.*, u.name as owner_name, u.email as owner_email,
                   GROUP_CONCAT(
                       JSON_OBJECT(
                           'name', ss.service_name,
                           'price', ss.price
                       )
                   ) as services
            FROM shops s
            JOIN users u ON s.user_id = u.id
            LEFT JOIN shop_services ss ON s.id = ss.shop_id
            GROUP BY s.id
        """
        cursor.execute(query)
        shops = cursor.fetchall()
        
        return jsonify({"shops": shops}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/user/<int:user_id>', methods=['GET'])
@jwt_required
def get_user_shop(user_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        print(f"DEBUG: Checking shop for user_id: {user_id}")
        
        cursor.execute("""
            SELECT * FROM shops WHERE user_id = %s
        """, (user_id,))
        
        shop = cursor.fetchone()
        print(f"DEBUG: Shop query result: {shop}")
        
        if shop:
            return jsonify(shop), 200
        return jsonify({}), 404
        
    except Exception as e:
        print(f"DEBUG: Error in get_user_shop: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shops/recent', methods=['GET'])
def get_recent_shops():
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Query to fetch the most recent shops
        query = """
            SELECT id, shop_name, contact_number, zone, street, barangay, building, 
                opening_time, closing_time, created_at
            FROM shops
            ORDER BY created_at DESC
            LIMIT 10
        """
        cursor.execute(query)
        shops = cursor.fetchall()
        
        return jsonify(shops), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()       
            
@app.route('/shop/<int:shop_id>', methods=['GET'])
@jwt_required
def get_shop_by_id(shop_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get shop details
        cursor.execute("""
            SELECT id, shop_name, contact_number, zone, street, barangay, 
                   building, opening_time, closing_time, created_at 
            FROM shops
            WHERE id = %s
        """, (shop_id,))
        
        shop = cursor.fetchone()
        
        if not shop:
            return jsonify({'error': 'Shop not found'}), 404

        # Format datetime for JSON
        if shop and 'created_at' in shop:
            shop['created_at'] = shop['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            
        return jsonify(shop)
        
    except Exception as e:
        print(f"Error fetching shop {shop_id}: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/update_shop/<int:shop_id>', methods=['PUT'])
@jwt_required
def update_shop(shop_id):
    connection = None
    try:
        data = request.json
        connection = create_connection()
        cursor = connection.cursor()
        
        query = """
            UPDATE shops 
            SET shop_name = %s,
                contact_number = %s,
                opening_time = %s,
                closing_time = %s
            WHERE id = %s
        """
        
        values = (
            data['shop_name'],
            data['contact_number'],
            data['opening_time'],
            data['closing_time'],
            shop_id
        )
        
        cursor.execute(query, values)
        connection.commit()
        
        if cursor.rowcount > 0:
            return jsonify({
                'message': 'Shop updated successfully',
                'shop_id': shop_id
            }), 200
        else:
            return jsonify({'message': 'No shop found with that ID'}), 404
            
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error updating shop: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            
# Transaction Routes
@app.route('/create_transaction/<int:user_id>', methods=['POST'])
@jwt_required
def create_transaction(user_id):
    try:
        result = transaction_controller.create_transaction(user_id, request.json)
        if result['status'] == 201:
            shop_id = request.json['shop_id']
            transaction_data = {
                'transaction_id': result['transaction_id'],
                'user_id': user_id,
                'shop_id': shop_id,
                'service_name': request.json.get('service_name'),
                'items': request.json.get('items', []),
                'status': 'Pending',
                'total_amount': request.json['total_amount'],
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Emit to both shop and user rooms
            socketio.emit('new_transaction', transaction_data, room=f"shop_{shop_id}")
            socketio.emit('transaction_update', transaction_data, room=f"user_{user_id}")
            
        return jsonify(result), result['status']
    except Exception as e:
        print(f"Error in create_transaction: {str(e)}")
        return jsonify({'status': 500, 'message': str(e)}), 500

@app.route('/user_transactions/<int:user_id>', methods=['GET'])
@jwt_required
def get_user_transactions(user_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Query to get user's transactions with shop details
        query = """
            SELECT t.*, s.shop_name
            FROM transactions t
            JOIN shops s ON t.shop_id = s.id
            WHERE t.user_id = %s
            ORDER BY t.created_at DESC
        """
        cursor.execute(query, (user_id,))
        transactions = cursor.fetchall()
        
        # Convert decimal values to strings for JSON serialization
        for transaction in transactions:
            if 'total_amount' in transaction:
                transaction['total_amount'] = str(transaction['total_amount'])
            if 'created_at' in transaction:
                transaction['created_at'] = transaction['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({'status': 'success', 'data': transactions}), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

from datetime import datetime, timedelta

@app.route('/shop_transactions/<int:shop_id>', methods=['GET'])
@jwt_required
def get_shop_transactions(shop_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT t.*, u.name as customer_name, u.email as customer_email
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            WHERE t.shop_id = %s
            ORDER BY t.created_at DESC
        """
        cursor.execute(query, (shop_id,))
        transactions = cursor.fetchall()
        
        # Convert datetime, timedelta, and Decimal objects to JSON serializable format
        formatted_transactions = []
        for transaction in transactions:
            formatted_transaction = {}
            for key, value in transaction.items():
                if isinstance(value, datetime):
                    formatted_transaction[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, timedelta):
                    total_seconds = int(value.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    formatted_transaction[key] = f"{hours:02}:{minutes:02}:{seconds:02}"
                elif isinstance(value, Decimal):
                    formatted_transaction[key] = float(value)
                else:
                    formatted_transaction[key] = value
            formatted_transactions.append(formatted_transaction)

        return jsonify({"transactions": formatted_transactions}), 200
        
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/update_transaction_status/<string:transaction_id>', methods=['PUT'])
@jwt_required
def update_transaction_status(transaction_id):
    try:
        result = transaction_controller.update_transaction_status(
            transaction_id,
            request.json['status'],
            request.json.get('notes')
        )
        
        if result['status'] == 200:
            update_data = {
                'transaction_id': transaction_id,
                'status': request.json['status'],
                'notes': request.json.get('notes'),
                'total_amount': request.json.get('total_amount')
            }
            
            # Emit to both rooms
            socketio.emit('status_update', update_data, room=f"shop_{result['shop_id']}")
            socketio.emit('status_update', update_data, room=f"user_{result['user_id']}")
            
        return jsonify(result), result['status']
    except Exception as e:
        print(f"Error in update_transaction_status: {str(e)}")
        return jsonify({'status': 500, 'message': str(e)}), 500

@app.route('/cancel_transaction/<string:transaction_id>', methods=['PUT'])
@jwt_required
def cancel_transaction(transaction_id):
    try:
        result = transaction_controller.cancel_transaction(
            transaction_id,
            request.json.get('reason'),
            request.json.get('notes')
        )
        return jsonify(result), result['status']
    except Exception as e:
        return jsonify({'status': 500, 'message': str(e)}), 500

@app.route('/user/<int:user_id>/has_shop', methods=['GET'])
@jwt_required
def check_user_shop(user_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT is_shop_owner FROM users WHERE id = %s', (user_id,))
        result = cursor.fetchone()
        
        if result:
            return jsonify({
                'has_shop': result['is_shop_owner']
            }), 200
        return jsonify({'message': 'User not found'}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

#Service Routes
@app.route('/shop/<int:shop_id>/services', methods=['GET'])
@jwt_required
def get_shop_services(shop_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, service_name, color, CAST(price AS FLOAT) as price 
            FROM shop_services 
            WHERE shop_id = %s
        """, (shop_id,))
        
        services = cursor.fetchall()
        return jsonify({'services': services}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/<int:shop_id>/service', methods=['POST'])
@jwt_required
def add_shop_service(shop_id):
    connection = None
    try:
        data = request.json
        connection = create_connection()
        cursor = connection.cursor()
        
        # Convert Decimal to float for JSON serialization
        cursor.execute("""
            INSERT INTO shop_services (
                shop_id, 
                service_name, 
                color,
                price
            ) VALUES (%s, %s, %s, %s)
        """, (
            shop_id, 
            data['service_name'],
            data['color'],
            float(data.get('price', 0))  # Convert to float
        ))
        
        connection.commit()
        return jsonify({'message': 'Service added successfully'}), 201
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/service/<int:service_id>', methods=['PUT', 'DELETE'])
@jwt_required
def manage_shop_service(service_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor()
        
        if request.method == 'DELETE':
            cursor.execute("DELETE FROM shop_services WHERE id = %s", (service_id,))
            message = 'Service deleted successfully'
        else:
            data = request.json
            cursor.execute("""
                UPDATE shop_services 
                SET service_name = %s, price = %s 
                WHERE id = %s
            """, (data['name'], data['price'], service_id))
            message = 'Service updated successfully'
            
        connection.commit()
        return jsonify({'message': message}), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# Item Routes
@app.route('/shop/<int:shop_id>/household', methods=['GET', 'POST'])
@jwt_required
def manage_household_items(shop_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("""
                SELECT * FROM household_items 
                WHERE shop_id = %s
            """, (shop_id,))
            items = cursor.fetchall()
            return jsonify({'items': items}), 200
            
        else:  # POST
            data = request.json
            cursor.execute("""
                INSERT INTO household_items (shop_id, item_name, price)
                VALUES (%s, %s, %s)
            """, (shop_id, data['name'], data['price']))
            connection.commit()
            return jsonify({'message': 'Item added successfully'}), 201
            
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/<int:shop_id>/clothing', methods=['GET', 'POST'])
@jwt_required
def manage_clothing_types(shop_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("""
                SELECT * FROM clothing_types 
                WHERE shop_id = %s
            """, (shop_id,))
            types = cursor.fetchall()
            return jsonify({'types': types}), 200
            
        else:  # POST
            data = request.json
            cursor.execute("""
                INSERT INTO clothing_types (shop_id, type_name, price)
                VALUES (%s, %s, %s)
            """, (shop_id, data['name'], data['price']))
            connection.commit()
            return jsonify({'message': 'Clothing type added successfully'}), 201
            
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/<int:shop_id>/clothing', methods=['GET'])
@jwt_required
def get_clothing_types(shop_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM clothing_types 
            WHERE shop_id = %s
        """, (shop_id,))
        
        types = cursor.fetchall()
        return jsonify({'types': types}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/<int:shop_id>/household', methods=['GET'])
@jwt_required
def get_household_items(shop_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM household_items 
            WHERE shop_id = %s
        """, (shop_id,))
        
        items = cursor.fetchall()
        return jsonify({'items': items}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/<int:shop_id>/household', methods=['POST'])
@jwt_required
def add_household_item(shop_id):
    connection = None
    try:
        data = request.json
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Check if item exists
        cursor.execute("""
            SELECT id FROM household_items 
            WHERE shop_id = %s AND item_name = %s
        """, (shop_id, data['name']))
        
        existing_item = cursor.fetchone()
        
        if existing_item:
            return jsonify({
                'message': 'Item already exists',
                'item_id': existing_item['id']
            }), 409

        # Add new item
        cursor.execute("""
            INSERT INTO household_items (shop_id, item_name, price)
            VALUES (%s, %s, %s)
        """, (shop_id, data['name'], data['price']))
        
        connection.commit()
        return jsonify({'message': 'Item added successfully'}), 201
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/<int:shop_id>/clothing', methods=['POST'])
@jwt_required
def add_clothing_type(shop_id):
    connection = None
    try:
        data = request.json
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Check if type exists
        cursor.execute("""
            SELECT id FROM clothing_types 
            WHERE shop_id = %s AND type_name = %s
        """, (shop_id, data['name']))
        
        existing_type = cursor.fetchone()
        
        if existing_type:
            return jsonify({
                'message': 'Type already exists',
                'type_id': existing_type['id']
            }), 409

        # Add new type
        cursor.execute("""
            INSERT INTO clothing_types (shop_id, type_name, price)
            VALUES (%s, %s, %s)
        """, (shop_id, data['name'], data['price']))
        
        connection.commit()
        return jsonify({'message': 'Type added successfully'}), 201
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/household/<int:item_id>', methods=['PUT'])
@jwt_required
def update_household_item(item_id):
    connection = None
    try:
        data = request.json
        connection = create_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            UPDATE household_items 
            SET price = %s 
            WHERE id = %s
        """, (data['price'], item_id))
        
        connection.commit()
        return jsonify({'message': 'Item updated successfully'}), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/clothing/<int:type_id>', methods=['PUT'])
@jwt_required
def update_clothing_type(type_id):
    connection = None
    try:
        data = request.json
        connection = create_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            UPDATE clothing_types 
            SET price = %s 
            WHERE id = %s
        """, (data['price'], type_id))
        
        connection.commit()
        return jsonify({'message': 'Type updated successfully'}), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# Order System Routes
@app.route('/shop/services', methods=['GET'])
@jwt_required
def get_all_shop_services():
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get all active services with their prices and colors
        cursor.execute("""
            SELECT s.id, s.service_name, s.price, s.color, s.description
            FROM shop_services s
            WHERE s.is_active = true
            ORDER BY s.service_name
        """)
        
        services = cursor.fetchall()
        
        # Convert Decimal to float for JSON serialization
        for service in services:
            service['price'] = float(service['price'])
        
        return jsonify({'services': services}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/items', methods=['GET'])
@jwt_required
def get_all_shop_items():
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get all household items
        cursor.execute("""
            SELECT hi.id, hi.item_name, hi.price
            FROM household_items hi
            ORDER BY hi.item_name
        """)
        
        items = cursor.fetchall()
        
        # Convert Decimal to float
        for item in items:
            item['price'] = float(item['price'])
        
        return jsonify({'items': items}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# Kilo Price Routes
@app.route('/shop/<int:shop_id>/kilo-prices', methods=['GET'])
@jwt_required
def get_kilo_prices(shop_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT min_kilo, max_kilo, price_per_kilo 
            FROM kilo_prices 
            WHERE shop_id = %s
        """, (shop_id,))
        
        prices = cursor.fetchall()
        
        # Convert Decimal objects to float before JSON serialization
        formatted_prices = [
            {
                'min_kilo': float(price[0]),
                'max_kilo': float(price[1]),
                'price_per_kilo': float(price[2])
            }
            for price in prices
        ]
        
        return jsonify({'prices': formatted_prices}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/<int:shop_id>/kilo-price', methods=['POST'])
@jwt_required
def add_kilo_price(shop_id):
    connection = None
    try:
        data = request.json
        connection = create_connection()
        cursor = connection.cursor()

        # Check for overlapping ranges
        cursor.execute("""
            SELECT COUNT(*) FROM kilo_prices 
            WHERE shop_id = %s AND (
                (%s BETWEEN min_kilo AND max_kilo) OR
                (%s BETWEEN min_kilo AND max_kilo) OR
                (min_kilo BETWEEN %s AND %s)
            )
        """, (shop_id, data['min_kilo'], data['max_kilo'], 
              data['min_kilo'], data['max_kilo']))
        
        if cursor.fetchone()[0] > 0:
            return jsonify({
                'error': 'This range overlaps with an existing range'
            }), 400
            
        cursor.execute("""
            INSERT INTO kilo_prices (shop_id, min_kilo, max_kilo, price_per_kilo)
            VALUES (%s, %s, %s, %s)
        """, (shop_id, data['min_kilo'], data['max_kilo'], data['price_per_kilo']))
        
        connection.commit()
        return jsonify({'message': 'Price range added successfully'}), 201
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/shop/<int:shop_id>/kilo-price', methods=['DELETE'])
@jwt_required
def delete_kilo_price(shop_id):
    connection = None
    try:
        data = request.json
        connection = create_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            DELETE FROM kilo_prices 
            WHERE shop_id = %s AND min_kilo = %s AND max_kilo = %s
        """, (shop_id, data['min_kilo'], data['max_kilo']))
        
        connection.commit()
        return jsonify({'message': 'Price range deleted successfully'}), 200
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            
@app.route('/api/orders', methods=['GET'])
@jwt_required
def get_orders():
    connection = None
    try:
        shop_id = request.args.get('shop_id')
        status = request.args.get('status')

        if not shop_id:
            return jsonify({'error': 'shop_id is required'}), 400

        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        query = "SELECT * FROM transactions WHERE shop_id = %s"
        params = [shop_id]

        if status:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        orders = cursor.fetchall()

        # Always serialize datetime and Decimal fields
        for order in orders:
            for key, value in order.items():
                if isinstance(value, (datetime, timedelta)):
                    order[key] = str(value)
                elif isinstance(value, Decimal):
                    order[key] = float(value)

        return jsonify({'orders': orders}), 200

    except Exception as e:
        print(f"Error in /api/orders: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/orders/<int:order_id>/decline', methods=['PUT'])
@jwt_required
def decline_order(order_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor()
        # Update the transaction status to 'cancelled'
        cursor.execute(
            "UPDATE transactions SET status = %s WHERE id = %s",
            ('cancelled', order_id)
        )
        connection.commit()
        return jsonify({'message': 'Order declined successfully'}), 200
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


@app.route('/api/orders/<int:order_id>/set_price', methods=['PUT'])
@jwt_required
def set_order_price(order_id):
    connection = None
    try:
        data = request.get_json()
        price_per_kilo = data.get('price_per_kilo')
        if price_per_kilo is None:
            return jsonify({'error': 'Missing price_per_kilo'}), 400

        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        # Update price in transactions table
        cursor.execute(
            "UPDATE transactions SET price_per_kilo = %s, status = %s WHERE id = %s",
            (price_per_kilo, 'processing', order_id)
        )
        # Get user_id and shop_id for this transaction
        cursor.execute("SELECT user_id, shop_id FROM transactions WHERE id = %s", (order_id,))
        row = cursor.fetchone()
        user_id = row['user_id']
        shop_id = row['shop_id']
        # Get shop name
        cursor.execute("SELECT shop_name FROM shops WHERE id = %s", (shop_id,))
        shop_row = cursor.fetchone()
        shop_name = shop_row['shop_name'] if shop_row else 'Shop'
        # Insert notification with shop name
        message = f"The shop set the price per kilo to ₱{price_per_kilo} for your order."
        cursor.execute(
            "INSERT INTO notifications (user_id, message, is_read, created_at, from_name) VALUES (%s, %s, 0, NOW(), %s)",
            (user_id, message, shop_name)
        )
        connection.commit()
        return jsonify({'message': 'Price per kilo updated and user notified successfully'}), 200
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error in set_order_price: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            
@app.route('/api/notifications/<int:user_id>', methods=['GET'])
@jwt_required
def get_notifications(user_id):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
        notifications = cursor.fetchall()
        # Optionally format datetime
        for n in notifications:
            if 'created_at' in n and n['created_at'] is not None:
                n['created_at'] = n['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({'notifications': notifications}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == '__main__':
    try:
        print("Starting Flask-SocketIO server...")
        socketio.run(app, port=5000, allow_unsafe_werkzeug=True)
        
    except Exception as e:
        print(f"Error starting server: {e}")
