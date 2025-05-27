from database.connection import create_connection

class User:
    def __init__(self, name=None, email=None, password=None, phone=None, 
                 birthdate=None, gender=None, zone=None, street=None, 
                 barangay=None, building=None):
        self.name = name
        self.email = email
        self.password = password
        self.phone = phone
        self.birthdate = birthdate
        self.gender = gender
        self.zone = zone
        self.street = street
        self.barangay = barangay
        self.building = building

    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'birthdate': self.birthdate,
            'gender': self.gender,
            'zone': self.zone,
            'street': self.street,
            'barangay': self.barangay,
            'building': self.building,
            'is_shop_owner': False  
        }
    
    def get_user_shop(self, user_id):
        conn = create_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT s.* 
                FROM shops s
                WHERE s.user_id = %s
            """
            cursor.execute(query, (user_id,))
            return cursor.fetchone()
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def create_shop(self, user_id, shop_data):
        conn = create_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            cursor.execute('START TRANSACTION')
            
            shop_query = """
                INSERT INTO shops (
                    user_id, shop_name, contact_number, zone, 
                    street, barangay, building, opening_time, closing_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            shop_values = (
                user_id,
                shop_data['shop_name'],
                shop_data['contact_number'],
                shop_data['zone'],
                shop_data['street'],
                shop_data['barangay'],
                shop_data.get('building'),
                shop_data['opening_time'],
                shop_data['closing_time']
            )
            cursor.execute(shop_query, shop_values)
            shop_id = cursor.lastrowid
            
            cursor.execute(
                "UPDATE users SET is_shop_owner = TRUE WHERE id = %s",
                (user_id,)
            )
            
            cursor.execute('COMMIT')
            return shop_id
        except:
            cursor.execute('ROLLBACK')
            raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()