from database.connection import create_connection
import json

class TransactionController:
    def __init__(self):
        self.connection = None

    def create_transaction(self, user_id, data):
        conn = create_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get user details
            user_query = "SELECT name, email, phone FROM users WHERE id = %s"
            cursor.execute(user_query, (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                return {'status': 404, 'message': 'User not found'}

            # Validate kilo amount if present
            if 'kilo_amount' in data:
                price_query = """
                    SELECT price_per_kilo 
                    FROM kilo_prices 
                    WHERE shop_id = %s AND 
                    min_kilo <= %s AND 
                    max_kilo >= %s
                    LIMIT 1
                """
                cursor.execute(price_query, (
                    data['shop_id'], 
                    data['kilo_amount'],
                    data['kilo_amount']
                ))
                price_data = cursor.fetchone()
                
                if not price_data:
                    return {'status': 400, 'message': 'Invalid kilo range'}

            # Insert transaction
            query = """
                INSERT INTO transactions (
                    user_id, shop_id, user_name, user_email, user_phone,
                    service_name, kilo_amount, subtotal, delivery_fee,
                    voucher_discount, total_amount, delivery_type,
                    zone, street, barangay, building,
                    scheduled_date, scheduled_time, payment_method,
                    notes, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    'Pending'
                )
            """
            
            values = (
                user_id,
                data['shop_id'],
                user_data['name'],
                user_data['email'],
                user_data.get('phone', ''),
                data['service_name'],
                data.get('kilo_amount', 0),
                data['subtotal'],
                data['delivery_fee'],
                data['voucher_discount'],
                data['total_amount'],
                data['delivery_type'],
                data['zone'],
                data['street'],
                data['barangay'],
                data['building'],
                data['scheduled_date'],
                data['scheduled_time'],
                data.get('payment_method', 'Cash on Delivery'),
                data.get('notes', '')
            )
            
            cursor.execute(query, values)
            transaction_id = cursor.lastrowid
            
            # Handle items insertion
            if 'items' in data:
                items_data = json.loads(data['items']) if isinstance(data['items'], str) else data['items']
                items_query = """
                    INSERT INTO transaction_items (
                        transaction_id, item_name, quantity
                    ) VALUES (%s, %s, %s)
                """
                for item in items_data:
                    cursor.execute(items_query, (
                        transaction_id,
                        item['name'],
                        item['quantity']
                    ))
            
            conn.commit()
            return {
                'status': 201,
                'message': 'Transaction created successfully',
                'transaction_id': transaction_id
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error creating transaction: {e}")
            return {'status': 500, 'message': str(e)}
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def get_transaction(self, transaction_id):
        conn = create_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get transaction with items and kilo price
            query = """
                SELECT t.*, k.price_per_kilo,
                    (SELECT JSON_ARRAYAGG(
                        JSON_OBJECT(
                            'name', ti.item_name,
                            'quantity', ti.quantity
                        )
                    )
                    FROM transaction_items ti
                    WHERE ti.transaction_id = t.id
                    ) as items
                FROM transactions t
                LEFT JOIN kilo_prices k ON 
                    k.shop_id = t.shop_id AND
                    k.min_kilo <= t.kilo_amount AND
                    k.max_kilo >= t.kilo_amount
                WHERE t.id = %s
            """
            cursor.execute(query, (transaction_id,))
            transaction = cursor.fetchone()
            
            if not transaction:
                return {'status': 404, 'message': 'Transaction not found'}

            return {'status': 200, 'data': transaction}

        except Exception as e:
            print(f"Error getting transaction: {e}")
            return {'status': 500, 'message': str(e)}
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def cancel_transaction(self, transaction_id, reason=None, notes=None):
        conn = None
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            # Check if transaction exists
            cursor.execute("SELECT id, status FROM transactions WHERE id = %s", (transaction_id,))
            transaction = cursor.fetchone()
            
            if not transaction:
                return {'status': 404, 'message': 'Transaction not found'}
            
            # Update transaction status to Cancelled
            cursor.execute("""
                UPDATE transactions 
                SET status = 'Cancelled', 
                    notes = %s
                WHERE id = %s
            """, (
                f"Cancelled - {reason}: {notes}" if notes else f"Cancelled - {reason}",
                transaction_id
            ))
            
            conn.commit()
            return {
                'status': 200,
                'message': 'Transaction cancelled successfully'
            }
                
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error cancelling transaction: {e}")
            return {'status': 500, 'message': str(e)}
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()