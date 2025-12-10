# CREATE DATABASE hotel_ac_db DEFAULT CHARACTER SET utf8mb4;
USE hotel_ac_db;
DROP TABLE IF EXISTS bill_details;
DROP TABLE IF EXISTS bills;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS ac_config;

CREATE TABLE rooms (
    id INT PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',
    current_temp DOUBLE DEFAULT 32.0,
    target_temp DOUBLE,
    ac_on TINYINT(1) DEFAULT 0,
    ac_mode VARCHAR(20) DEFAULT 'COOLING',
    fan_speed VARCHAR(20) DEFAULT 'MEDIUM',
    default_temp DOUBLE DEFAULT 25.0,
    check_in_time DATETIME,
    ac_session_start DATETIME,
    last_temp_update DATETIME,
    assigned_ac_number INT,
    customer_name VARCHAR(50),
    waiting_start_time DATETIME,
    serving_start_time DATETIME,
    cooling_paused TINYINT(1) DEFAULT 0,
    pause_start_temp DOUBLE,
    daily_rate DOUBLE DEFAULT 100.0 COMMENT '房间日房费（元/天）',
    billing_start_temp DOUBLE COMMENT '计费开始时的温度（用于基于温度变化的计费）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    id_card VARCHAR(20),
    phone_number VARCHAR(20),
    current_room_id INT,
    check_in_time DATETIME,
    check_out_time DATETIME,
    check_in_days INT,
    status VARCHAR(20) DEFAULT 'CHECKED_IN',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_room (current_room_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id INT NOT NULL,
    customer_id INT,
    check_in_time DATETIME NOT NULL,
    check_out_time DATETIME NOT NULL,
    stay_days INT NOT NULL,
    room_fee DOUBLE DEFAULT 0,
    ac_total_fee DOUBLE DEFAULT 0,
    total_amount DOUBLE DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'UNPAID',
    paid_time DATETIME,
    cancelled_time DATETIME,
    print_status VARCHAR(20) NOT NULL DEFAULT 'NOT_PRINTED',
    print_time DATETIME,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_room_id (room_id),
    INDEX idx_customer_id (customer_id),
    INDEX idx_bill_status (status),
    INDEX idx_print_status (print_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE bill_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id INT NOT NULL,
    customer_id INT,
    ac_mode VARCHAR(20),
    fan_speed VARCHAR(20),
    request_time DATETIME NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    duration INT NOT NULL,
    cost DOUBLE NOT NULL,
    rate DOUBLE NOT NULL,
    detail_type VARCHAR(50) DEFAULT 'AC',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_bill_detail_room_type_start (room_id, detail_type, start_time),
    INDEX idx_room_detail (room_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ac_config (
    id INT PRIMARY KEY,
    mode VARCHAR(20) NOT NULL,
    min_temp DOUBLE NOT NULL,
    max_temp DOUBLE NOT NULL,
    default_temp DOUBLE NOT NULL,
    rate DOUBLE NOT NULL,
    low_speed_rate DOUBLE NOT NULL,
    mid_speed_rate DOUBLE NOT NULL,
    high_speed_rate DOUBLE NOT NULL,
    default_speed ENUM('L','M','H') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

