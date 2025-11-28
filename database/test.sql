
USE hotel_ac_db;


-- ============================================
-- 设置每个房间的默认温度
-- ============================================

UPDATE rooms
SET default_temp = 32.0,
    current_temp = 32.0
WHERE id = 1;

UPDATE rooms
SET default_temp = 28.0,
    current_temp = 28.0
WHERE id = 2;

UPDATE rooms
SET default_temp = 30.0,
    current_temp = 30.0
WHERE id = 3;

UPDATE rooms
SET default_temp = 29.0,
    current_temp = 29.0
WHERE id = 4;

UPDATE rooms
SET default_temp = 35.0,
    current_temp = 35.0
WHERE id = 5;


-- 设置每个房间的日房费

UPDATE rooms SET daily_rate = 100.0 WHERE id = 1;


UPDATE rooms SET daily_rate = 125.0 WHERE id = 2;


UPDATE rooms SET daily_rate = 150.0 WHERE id = 3;


UPDATE rooms SET daily_rate = 200.0 WHERE id = 4;


UPDATE rooms SET daily_rate = 100.0 WHERE id = 5;


