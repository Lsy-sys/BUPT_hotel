import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:abc123456@localhost:3306/hotel_ac_db?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "hotel-backend-secret")

    HOTEL_AC_TOTAL_COUNT = int(os.getenv("HOTEL_AC_TOTAL_COUNT", 3))
    HOTEL_ROOM_COUNT = int(os.getenv("HOTEL_ROOM_COUNT", 5))
    HOTEL_DEFAULT_TEMP = float(os.getenv("HOTEL_DEFAULT_TEMP", 25))
    HOTEL_TIME_SLICE = int(os.getenv("HOTEL_TIME_SLICE", 120))

    BILLING_ROOM_RATE = float(os.getenv("BILLING_ROOM_RATE", 100.0))
    BILLING_AC_RATE_LOW = float(os.getenv("BILLING_AC_RATE_LOW", 0.5))
    BILLING_AC_RATE_MEDIUM = float(os.getenv("BILLING_AC_RATE_MEDIUM", 1.0))
    BILLING_AC_RATE_HIGH = float(os.getenv("BILLING_AC_RATE_HIGH", 1.5))

    # 打开注释启用：每次空调完整开启+关闭记为一天房费
    ENABLE_AC_CYCLE_DAILY_FEE = bool(int(os.getenv("ENABLE_AC_CYCLE_DAILY_FEE", 0)))
    ENABLE_AC_CYCLE_DAILY_FEE = True

    # 测试用时间加速因子：现实1秒=系统TIME_ACCELERATION_FACTOR秒
    TIME_ACCELERATION_FACTOR = float(os.getenv("TIME_ACCELERATION_FACTOR", 6.0))

