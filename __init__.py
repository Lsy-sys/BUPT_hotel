from flask import Flask, render_template

from .config import Config
from .database import (
    ensure_bill_detail_update_time_column,
    ensure_room_daily_rate_column,
    ensure_room_last_temp_update_column,
    seed_default_ac_config,
)
from .extensions import db
from .services import room_service


def create_app(
    config_class: type[Config] = Config, *, setup_database: bool = True
) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)
    db.init_app(app)

    if setup_database:
        with app.app_context():
            db.create_all()
            # 先确保数据库字段存在，再初始化数据
            ensure_bill_detail_update_time_column()
            ensure_room_last_temp_update_column()
            ensure_room_daily_rate_column()
            seed_default_ac_config()
            room_service.ensureRoomsInitialized(
                total_count=app.config["HOTEL_ROOM_COUNT"],
                default_temp=app.config["HOTEL_DEFAULT_TEMP"],
            )

    from .controllers.ac_controller import ac_bp
    from .controllers.admin_controller import admin_bp
    from .controllers.bill_controller import bill_bp
    from .controllers.hotel_controller import hotel_bp
    from .controllers.monitor_controller import monitor_bp
    from .controllers.report_controller import report_bp
    from .controllers.test_controller import test_bp

    app.register_blueprint(ac_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(bill_bp)
    app.register_blueprint(hotel_bp)
    app.register_blueprint(monitor_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(test_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/customer")
    def customer():
        return render_template("customer.html")

    @app.route("/reception")
    def reception():
        return render_template("reception.html")
    
    @app.route("/reception/checkin")
    def reception_checkin():
        return render_template("checkin.html")
    
    @app.route("/reception/checkout")
    def reception_checkout():
        return render_template("checkout.html")

    @app.route("/admin")
    def admin():
        return render_template("admin.html")

    @app.route("/manager")
    def manager():
        return render_template("manager.html")

    return app

