from models.userModel import User
from database.connection import create_connection
import bcrypt
import mysql.connector
from datetime import datetime, timedelta
import jwt
from flask import current_app

class UserController:
    def __init__(self):
        self.connection = None

    def get_user_details(self, user_id):
        conn = create_connection()
        if not conn:
            return {'status': 500, 'message': 'Database connection failed'}
            
        try:
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT id, name, email, phone,
                    DATE_FORMAT(birthdate, '%Y-%m-%d') as birthdate,
                    gender, zone, street, barangay, building
                FROM users 
                WHERE id = %s
            """
            
            cursor.execute(query, (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return {'status': 404, 'message': 'User not found'}
                
            return {
                'status': 200,
                'message': 'User details retrieved successfully',
                'user': user
            }
                
        except mysql.connector.Error as err:
            return {'status': 500, 'message': f'Database error: {str(err)}'}
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def update_profile(self, user_id, data):
        conn = create_connection()
        if not conn:
            return {'status': 500, 'message': 'Database connection failed'}
            
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get existing user data
            cursor.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
            existing_user = cursor.fetchone()
            
            if not existing_user:
                return {'status': 404, 'message': 'User not found'}

            # Use existing values if new ones are not provided
            name = data.get('name') if data.get('name') is not None else existing_user['name']
            email = data.get('email') if data.get('email') is not None else existing_user['email']
            
            # Handle birthdate formatting
            birthdate = data.get('birthdate')
            if birthdate:
                try:
                    clean_date = birthdate.split('T')[0]
                    datetime.strptime(clean_date, '%Y-%m-%d')
                    formatted_date = clean_date
                except ValueError:
                    return {'status': 400, 'message': 'Invalid date format. Use YYYY-MM-DD'}
            else:
                formatted_date = None

            query = """
                UPDATE users 
                SET name = %s,
                    email = %s,
                    phone = %s,  
                    birthdate = %s,
                    gender = %s,
                    zone = %s,
                    street = %s,
                    barangay = %s,
                    building = %s
                WHERE id = %s
            """
            values = (
                name,
                email,
                data.get('phone'),
                formatted_date,
                data.get('gender'),
                data.get('zone'),
                data.get('street'), 
                data.get('barangay'),
                data.get('building'),
                user_id
            )
            
            cursor.execute(query, values)
            conn.commit()
            
            return {'status': 200, 'message': 'Profile updated successfully'}
                    
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return {'status': 500, 'message': f'Database error: {str(err)}'}
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def update_password(self, user_id, data):
        conn = create_connection()
        if not conn:
            return {'status': 500, 'message': 'Database connection failed'}
            
        try:
            cursor = conn.cursor(dictionary=True)
            
            # First verify current password
            cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return {'status': 404, 'message': 'User not found'}
                
            # Verify current password
            if not bcrypt.checkpw(data['current_password'].encode('utf-8'), 
                                user['password'].encode('utf-8')):
                return {'status': 401, 'message': 'Current password is incorrect'}
            
            # Hash new password
            hashed_password = bcrypt.hashpw(data['new_password'].encode('utf-8'), 
                                        bcrypt.gensalt())
            
            # Update password
            query = "UPDATE users SET password = %s WHERE id = %s"
            cursor.execute(query, (hashed_password, user_id))
            conn.commit()
            
            if cursor.rowcount == 0:
                return {'status': 404, 'message': 'Failed to update password'}
                
            return {'status': 200, 'message': 'Password updated successfully'}
                    
        except mysql.connector.Error as err:
            print(f"Password update error: {err}")  # Debug logging
            return {'status': 500, 'message': f'Database error: {str(err)}'}
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def update_password(self, user_id, data):
        conn = create_connection()
        if not conn:
            return {'status': 500, 'message': 'Database connection failed'}
            
        try:
            cursor = conn.cursor(dictionary=True)
            
            # First verify current password
            cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return {'status': 404, 'message': 'User not found'}
                
            if not bcrypt.checkpw(data['current_password'].encode('utf-8'), 
                                user['password'].encode('utf-8')):
                return {'status': 401, 'message': 'Current password is incorrect'}
            
            # Hash new password
            hashed_password = bcrypt.hashpw(data['new_password'].encode('utf-8'), 
                                        bcrypt.gensalt())
            
            # Update password
            query = "UPDATE users SET password = %s WHERE id = %s"
            cursor.execute(query, (hashed_password, user_id))
            conn.commit()
            
            return {'status': 200, 'message': 'Password updated successfully'}
                    
        except mysql.connector.Error as err:
            return {'status': 500, 'message': f'Database error: {str(err)}'}
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def login(self, credentials):
        conn = create_connection()
        if not conn:
            return {'status': 500, 'message': 'Database connection failed'}
            
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (credentials['email'],))
            user = cursor.fetchone()
            
            if not user:
                return {'status': 401, 'message': 'Invalid email or password'}
                
            if bcrypt.checkpw(credentials['password'].encode('utf-8'), 
                            user['password'].encode('utf-8')):
                # Generate proper JWT token
                token = jwt.encode({
                    'user_id': user['id'],
                    'email': user['email'],
                    'exp': datetime.utcnow() + timedelta(hours=24)
                }, current_app.config['SECRET_KEY'], algorithm="HS256")
                
                if isinstance(token, bytes):
                    token = token.decode('utf-8')  # Convert bytes to string if needed
                    
                return {
                    'status': 200,
                    'message': 'Login successful',
                    'token': token,  # Make sure token is a string
                    'user': {
                        'id': user['id'],
                        'email': user['email']
                    }
                }
            
            return {'status': 401, 'message': 'Invalid email or password'}
            
        except mysql.connector.Error as err:
            return {'status': 500, 'message': f'Database error: {str(err)}'}
        except Exception as e:
            return {'status': 500, 'message': f'Error: {str(e)}'}
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def signup(self, data):
        conn = create_connection()
        if not conn:
            return {'status': 500, 'message': 'Database connection failed'}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Debug print to see what data we're receiving
            print("Received signup data:", data)
            
            # Validate required fields with better error messages
            if not data.get('name'):
                return {'status': 400, 'message': 'Name field is missing'}
            
            if not data.get('name').strip():
                return {'status': 400, 'message': 'Name cannot be empty'}
                
            if not data.get('email'):
                return {'status': 400, 'message': 'Email field is missing'}
                
            if not data.get('password'):
                return {'status': 400, 'message': 'Password field is missing'}

            # Check if email already exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (data['email'],))
            if cursor.fetchone():
                return {'status': 400, 'message': 'Email already exists'}

            # Hash password with bcrypt
            hashed_password = bcrypt.hashpw(
                data['password'].encode('utf-8'), 
                bcrypt.gensalt()
            )
            
            # Clean input data
            name = data['name'].strip()
            email = data['email'].strip()
            
            print("Inserting values:", {
                'name': name,
                'email': email
            })
            
            # Insert user with required fields
            query = """
                INSERT INTO users (name, email, password) 
                VALUES (%s, %s, %s)
            """
            values = (name, email, hashed_password)
            
            cursor.execute(query, values)
            conn.commit()
            user_id = cursor.lastrowid
            
            # Generate JWT token
            token = jwt.encode({
                'user_id': user_id,
                'email': email,
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, '1025', algorithm="HS256")

            # Convert token to string if it's bytes
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            
            print("Debug - Generated token:", token)  # Debug print
            
            return {
                'status': 201,
                'message': 'User registered successfully',
                'user_id': user_id,
                'token': token
            }
                
        except mysql.connector.Error as err:
            print("Database Error:", str(err))  # Debug print
            return {'status': 500, 'message': f'Database error: {str(err)}'}
        except Exception as e:
            print("General Error:", str(e))  # Debug print
            return {'status': 500, 'message': f'Error: {str(e)}'}
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    def delete_account(self, user_id):
        conn = create_connection()
        if not conn:
            return {'status': 500, 'message': 'Database connection failed'}
            
        try:
            cursor = conn.cursor()
            
            # First check if user exists
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return {'status': 404, 'message': 'User not found'}
                
            # Delete the user
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                return {'status': 200, 'message': 'Account deleted successfully'}
            else:
                return {'status': 400, 'message': 'Failed to delete account'}
                
        except mysql.connector.Error as err:
            print(f"Delete account error: {err}")  # Debug logging
            return {'status': 500, 'message': f'Database error: {str(err)}'}
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()     
                 
    def register_shop(self, user_id, shop_data):
        conn = create_connection()
        if not conn:
            return {'status': 500, 'message': 'Database connection failed'}
            
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Check if user already has a shop
            cursor.execute('SELECT * FROM shops WHERE user_id = %s', (user_id,))
            if cursor.fetchone():
                return {'status': 400, 'message': 'User already has a shop'}
            
            cursor.execute('START TRANSACTION')
            
            # Create shop
            shop_query = """
                INSERT INTO shops (
                    user_id, shop_name, contact_number, zone, street, 
                    barangay, building, opening_time, closing_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(shop_query, (
                user_id,
                shop_data['shop_name'],
                shop_data['contact_number'],
                shop_data['zone'],
                shop_data['street'],
                shop_data['barangay'],
                shop_data.get('building', None),
                shop_data['opening_time'],
                shop_data['closing_time']
            ))
            
            shop_id = cursor.lastrowid
            
            # Add services
            for service in shop_data.get('services', []):
                cursor.execute('''
                    INSERT INTO services (shop_id, service_name, price)
                    VALUES (%s, %s, %s)
                ''', (shop_id, service['service_name'], service['price']))
            
            # Update user to shop owner
            cursor.execute(
                "UPDATE users SET is_shop_owner = TRUE WHERE id = %s",
                (user_id,)
            )
            
            conn.commit()
            return {
                'status': 201, 
                'message': 'Shop registered successfully',
                'shop_id': shop_id
            }
                
        except Exception as e:
            if conn:
                conn.rollback()
            return {'status': 500, 'message': f'Error: {str(e)}'}
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()        
