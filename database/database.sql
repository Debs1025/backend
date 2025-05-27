CREATE DATABASE IF NOT EXISTS LabaRide_DB;
USE LabaRide_DB;

-- User table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    phone VARCHAR(20),    
    birthdate DATE,
    gender VARCHAR(10),
    zone VARCHAR(255),
    street VARCHAR(255),
    barangay VARCHAR(255),
    building VARCHAR(255),
    is_shop_owner BOOLEAN DEFAULT FALSE, -- 0 = False, 1 = True
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

#Transaction table
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    shop_id INT NOT NULL,
    user_name VARCHAR(255) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    user_phone VARCHAR(20),
    service_name VARCHAR(50) NOT NULL,
    kilo_amount DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    delivery_fee DECIMAL(10,2) NOT NULL,
    voucher_discount DECIMAL(10,2) DEFAULT 0.0,
    total_amount DECIMAL(10,2) NOT NULL,
    delivery_type VARCHAR(50) NOT NULL,
    zone VARCHAR(255) NOT NULL,
    street VARCHAR(255) NOT NULL,
    barangay VARCHAR(255) NOT NULL,
    building VARCHAR(255) NOT NULL,
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL,
    payment_method VARCHAR(50) NOT NULL DEFAULT 'Cash on Delivery',
    notes TEXT,
    status ENUM('Pending', 'Processing', 'Completed', 'Cancelled') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (shop_id) REFERENCES shops(id)
);

#Shop table
CREATE TABLE shops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    shop_name VARCHAR(255) NOT NULL,
    contact_number VARCHAR(20) NOT NULL,
    zone VARCHAR(255) NOT NULL,
    street VARCHAR(255) NOT NULL,
    barangay VARCHAR(255) NOT NULL,
    building VARCHAR(255),
    opening_time VARCHAR(20) NOT NULL,
    closing_time VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    latitude DOUBLE,
    longitude DOUBLE,
    address VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS shop_services (
    id INT PRIMARY KEY AUTO_INCREMENT,
    shop_id INT NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    price DECIMAL(10,2) DEFAULT 0,
    color VARCHAR(255),
    FOREIGN KEY (shop_id) REFERENCES shops(id)
);

CREATE TABLE IF NOT EXISTS kilo_prices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    shop_id INT NOT NULL,
    min_kilo DECIMAL(10,2) NOT NULL,
    max_kilo DECIMAL(10,2) NOT NULL,
    price_per_kilo DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    UNIQUE KEY unique_range (shop_id, min_kilo, max_kilo)
);


select * from users;
select * from shops;
select * from transactions;
select * from shop_services;
select * from kilo_prices;
