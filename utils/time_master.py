# hotel/utils/time_master.py

from datetime import datetime, timedelta
import threading


class TimeMaster:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TimeMaster, cls).__new__(cls)
                    cls._instance._init_clock()
        return cls._instance

    def _init_clock(self):
        self.speed = 1.0  # 时间流速，1.0为真实时间，6.0为6倍速
        self.paused = False
        
        # 锚点：记录上一次调整参数时的【物理时间】和对应的【逻辑时间】
        self.anchor_real_time = datetime.utcnow()
        self.anchor_logical_time = datetime.utcnow()

    def now(self) -> datetime:
        """获取当前的逻辑时间"""
        if self.paused:
            return self.anchor_logical_time
        
        real_now = datetime.utcnow()
        real_delta = real_now - self.anchor_real_time
        # 逻辑流逝时间 = 物理流逝时间 * 倍速
        logical_delta = real_delta * self.speed
        return self.anchor_logical_time + logical_delta

    def set_speed(self, speed: float):
        """动态调整流速"""
        with self._lock:
            # 1. 先结算当前时间，更新锚点，防止时间跳变
            current_logical = self.now()
            self.anchor_logical_time = current_logical
            self.anchor_real_time = datetime.utcnow()
            
            # 2. 应用新速度
            self.speed = float(speed)
            self.paused = False
            print(f"[TimeMaster] Speed set to {self.speed}x")

    def pause(self):
        """暂停时间"""
        with self._lock:
            if not self.paused:
                self.anchor_logical_time = self.now()
                self.paused = True
                print("[TimeMaster] Time Paused")

    def resume(self):
        """恢复时间"""
        with self._lock:
            if self.paused:
                self.anchor_real_time = datetime.utcnow()
                self.paused = False
                print("[TimeMaster] Time Resumed")

    def jump_to(self, target_time: datetime):
        """时间跳跃（回到过去或去往未来）"""
        with self._lock:
            self.anchor_logical_time = target_time
            self.anchor_real_time = datetime.utcnow()
            print(f"[TimeMaster] Jumped to {target_time}")


# 全局单例
clock = TimeMaster()









