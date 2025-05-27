import os
import mysql.connector
from mysql.connector import Error

def create_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('MYSQLHOST', 'localhost'),
            user=os.getenv('MYSQLUSER', 'root'),
            password=os.getenv('MYSQLPASSWORD', '1025'),
            database=os.getenv('MYSQLDATABASE', 'LabaRide_DB'),
            port=os.getenv('MYSQLPORT', '8080'),
        )
        if connection.is_connected():
            print("Successfully connected to MySQL database")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None
