from database.connection import create_connection

class ShopModel:
    def __init__(self):
        pass

    def get_shop_by_user(self, user_id):
        conn = create_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT s.*, ss.service_name, ss.price
                FROM shops s
                LEFT JOIN shop_services ss ON s.id = ss.shop_id
                WHERE s.user_id = %s
            """, (user_id,))
            return cursor.fetchall()
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def update_shop_details(self, shop_id, data):
        conn = create_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            query = """
                UPDATE shops 
                SET shop_name = %s,
                    contact_number = %s,
                    zone = %s,
                    street = %s,
                    barangay = %s,
                    building = %s,
                    opening_time = %s,
                    closing_time = %s
                WHERE id = %s
            """
            values = (
                data['shop_name'],
                data['contact_number'],
                data['zone'],
                data['street'],
                data['barangay'],
                data.get('building'),
                data['opening_time'],
                data['closing_time'],
                shop_id
            )
            cursor.execute(query, values)
            conn.commit()
            return True
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()