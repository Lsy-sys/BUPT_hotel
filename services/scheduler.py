from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from flask import current_app

from ..models import Room, RoomRequest
from .bill_detail_service import BillDetailService
from .room_service import RoomService


class Scheduler:
    def __init__(self, room_service: RoomService, bill_detail_service: BillDetailService):
        self.room_service = room_service
        self.bill_detail_service = bill_detail_service
        self.serving_queue: List[RoomRequest] = []
        self.waiting_queue: List[RoomRequest] = []

    def _capacity(self) -> int:
        return int(current_app.config["HOTEL_AC_TOTAL_COUNT"])

    def _time_slice(self) -> int:
        return int(current_app.config["HOTEL_TIME_SLICE"])

    def _rate_by_fan_speed(self, fan_speed: str) -> float:
        fan_speed = (fan_speed or "MEDIUM").upper()
        if fan_speed == "HIGH": return 1.0
        if fan_speed == "MEDIUM": return 0.5
        return 1.0 / 3.0

    def _time_factor(self) -> float:
        return float(current_app.config.get("TIME_ACCELERATION_FACTOR", 1.0))

    # === 辅助方法 (保持不变) ===
    def _priority_score(self, request: RoomRequest) -> int:
        score_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return score_map.get((request.fanSpeed or "MEDIUM").upper(), 2)

    def _elapsed_seconds(self, source: Optional[datetime], now: datetime) -> float:
        if not source: return 0.0
        return max(0.0, (now - source).total_seconds() * self._time_factor())

    def _remove_from_queue(self, queue: List[RoomRequest], room_id: int) -> Optional[RoomRequest]:
        for idx, req in enumerate(queue):
            if req.roomId == room_id: return queue.pop(idx)
        return None

    def _mark_room_serving(self, room_id: int, started_at: datetime) -> None:
        room = self.room_service.getRoomById(room_id)
        if room:
            room.serving_start_time = started_at
            room.waiting_start_time = None
            self.room_service.updateRoom(room)

    def _mark_room_waiting(self, room_id: int, started_at: datetime) -> None:
        room = self.room_service.getRoomById(room_id)
        if room:
            room.waiting_start_time = started_at
            room.serving_start_time = None
            self.room_service.updateRoom(room)

    def _remove_request(self, room_id: int) -> None:
        self._remove_from_queue(self.serving_queue, room_id)
        self._remove_from_queue(self.waiting_queue, room_id)

    # === 核心计费与结算 ===
    def _settle_current_service_period(self, room: Room, end_time: datetime, reason: str = "CHANGE") -> None:
        if not room.serving_start_time: return
        
        start_time = room.serving_start_time
        duration_minutes = max(1, int(((end_time - start_time).total_seconds() / 60.0) * self._time_factor()))
        rate = self._rate_by_fan_speed(room.fan_speed)
        cost = rate * duration_minutes
        
        customer_id = None
        if room.status == "OCCUPIED":
            from ..services import customer_service
            customer = customer_service.getCustomerByRoomId(room.id)
            if customer: customer_id = customer.id
        
        detail_type = "POWER_OFF_CYCLE" if reason == "POWER_OFF" else "AC"
        self.bill_detail_service.createBillDetail(
            room_id=room.id, ac_mode=room.ac_mode, fan_speed=room.fan_speed,
            start_time=start_time, end_time=end_time, rate=rate, cost=cost,
            customer_id=customer_id, detail_type=detail_type,
        )

    # === 状态流转 ===
    def _pause_cooling(self, room: Room) -> None:
        now = datetime.utcnow()
        if room.serving_start_time:
            self._settle_current_service_period(room, now, "PAUSED")
        self._remove_request(room.id)
        room.serving_start_time = None
        room.waiting_start_time = None
        room.ac_session_start = now
        # 核心：设置暂停状态
        room.cooling_paused = True
        self.room_service.updateRoom(room)
        self._rebalance_queues()

    def _resume_cooling(self, room: Room) -> None:
        now = datetime.utcnow()
        request = RoomRequest(roomId=room.id, fanSpeed=room.fan_speed, mode=room.ac_mode, targetTemp=room.target_temp)
        capacity = self._capacity()
        if len(self.serving_queue) < capacity:
            request.servingTime = now
            self.serving_queue.append(request)
            self._mark_room_serving(room.id, now)
        else:
            request.waitingTime = now
            self.waiting_queue.append(request)
            self._mark_room_waiting(room.id, now)
        
        # 核心：解除暂停状态
        room.cooling_paused = False
        self.room_service.updateRoom(room)
        self._rebalance_queues()

    # === 队列管理 ===
    def _deduplicate_queues(self) -> None:
        seen = set()
        new_s = []
        for r in self.serving_queue:
            if r.roomId not in seen: seen.add(r.roomId); new_s.append(r)
        self.serving_queue = new_s
        new_w = []
        for r in self.waiting_queue:
            if r.roomId not in seen: seen.add(r.roomId); new_w.append(r)
        self.waiting_queue = new_w

    def _sort_waiting_queue(self) -> None:
        if not self.waiting_queue: return
        now = datetime.utcnow()
        self.waiting_queue.sort(key=lambda r: (-self._priority_score(r), r.waitingTime or now, r.roomId))

    def _promote_waiting_room(self) -> None:
        if not self.waiting_queue: return
        capacity = self._capacity()
        now = datetime.utcnow()
        self._sort_waiting_queue()
        
        # 1. 填补空位
        while self.waiting_queue and len(self.serving_queue) < capacity:
            p = self.waiting_queue.pop(0)
            p.servingTime = now; p.waitingTime = None
            self.serving_queue.append(p)
            self._mark_room_serving(p.roomId, now)
            
        # 2. 抢占低优先级
        if len(self.serving_queue) >= capacity and self.waiting_queue:
            high = self.waiting_queue[0]
            # 找到优先级最低且运行时间最长的
            low_s = min(self.serving_queue, key=lambda r: (self._priority_score(r), -(self._elapsed_seconds(r.servingTime, now))))
            
            if self._priority_score(high) > self._priority_score(low_s):
                d = self._remove_from_queue(self.serving_queue, low_s.roomId)
                if d:
                    self._move_to_waiting(d, now, "PREEMPTED")
                    high = self.waiting_queue.pop(0)
                    high.servingTime = now; high.waitingTime = None
                    self.serving_queue.append(high)
                    self._mark_room_serving(high.roomId, now)

    def _move_to_waiting(self, request: RoomRequest, timestamp: datetime, reason: str = "ROTATED") -> None:
        room = self.room_service.getRoomById(request.roomId)
        if room and room.serving_start_time:
            self._settle_current_service_period(room, timestamp, reason)
        request.waitingTime = timestamp
        request.servingTime = None
        self.waiting_queue.append(request)
        self._mark_room_waiting(request.roomId, timestamp)

    def _rotate_time_slice(self, *, force: bool = False) -> None:
        if not self.serving_queue: return
        now = datetime.utcnow()
        limit = self._time_slice()
        to_demote = []
        for req in self.serving_queue:
            if self._elapsed_seconds(req.servingTime, now) >= limit:
                to_demote.append(req)
        to_demote.sort(key=lambda r: self._elapsed_seconds(r.servingTime, now), reverse=True)
        
        for req in to_demote:
            demoted = self._remove_from_queue(self.serving_queue, req.roomId)
            if demoted: self._move_to_waiting(demoted, now, "ROTATED")
        self._promote_waiting_room()

    def _enforce_capacity(self) -> None:
        capacity = self._capacity()
        now = datetime.utcnow()
        while len(self.serving_queue) > capacity:
            self.serving_queue.sort(key=lambda r: (self._priority_score(r), -(self._elapsed_seconds(r.servingTime, now))))
            demoted = self.serving_queue.pop(0)
            self._move_to_waiting(demoted, now, "CAPACITY")
        self._promote_waiting_room()

    def _rebalance_queues(self, *, force_rotation: bool = False) -> None:
        self._enforce_capacity()
        self._rotate_time_slice(force=force_rotation)

    # === 用户操作接口 ===
    def PowerOn(self, RoomId: int, CurrentRoomTemp: float | None) -> str:
        room = self.room_service.getRoomById(RoomId)
        if not room: raise ValueError("房间不存在")
        if room.ac_on: return "已开启"

        now = datetime.utcnow()
        if CurrentRoomTemp is not None:
            room.current_temp = CurrentRoomTemp
        elif room.current_temp is None:
            room.current_temp = room.default_temp or current_app.config["HOTEL_DEFAULT_TEMP"]
        
        room.ac_on = True
        room.ac_session_start = now
        room.last_temp_update = now
        room.target_temp = room.target_temp or 25.0

        # === 核心修复逻辑 ===
        # 判断：如果当前温度已经达到目标温度 (误差 0.1 内)
        # 直接进入 PAUSED 状态，不占用服务队列资源
        diff = abs(room.current_temp - room.target_temp)
        if diff < 0.1:
            room.cooling_paused = True
            room.pause_start_temp = room.current_temp
            # 记录日志方便调试
            print(f"[PowerOn] Room {RoomId} 开机即达标 ({room.current_temp}°C)，直接待机")
        else:
            # 没达标，正常申请队列
            request = RoomRequest(roomId=room.id, fanSpeed=room.fan_speed, mode=room.ac_mode, targetTemp=room.target_temp)
            if len(self.serving_queue) < self._capacity():
                request.servingTime = now
                self.serving_queue.append(request)
                self._mark_room_serving(room.id, now)
            else:
                request.waitingTime = now
                self.waiting_queue.append(request)
                self._mark_room_waiting(room.id, now)
        
        self.room_service.updateRoom(room)
        # 即使是 Pause，也可以调一下平衡，虽然此时 Pause 的房间不在队列里
        self._rebalance_queues()
        
        return "空调已开启"

    def PowerOff(self, RoomId: int) -> str:
        room = self.room_service.getRoomById(RoomId)
        if not room or not room.ac_on: raise ValueError("未开启")

        now = datetime.utcnow()
        # 1. 强制生成关机账单
        if room.serving_start_time:
            self._settle_current_service_period(room, now, "POWER_OFF")
        else:
            # 待机状态关机也要记
            cid = None
            if room.status == "OCCUPIED":
                from ..services import customer_service
                cust = customer_service.getCustomerByRoomId(room.id)
                if cust: cid = cust.id
            self.bill_detail_service.createBillDetail(
                room_id=room.id, ac_mode=room.ac_mode, fan_speed=room.fan_speed,
                start_time=now, end_time=now, rate=0.0, cost=0.0,
                customer_id=cid, detail_type="POWER_OFF_CYCLE"
            )

        # 2. 关机立即恢复默认温度
        if room.default_temp is not None:
            room.current_temp = room.default_temp
        
        # 2.1 重置目标温度为默认值（25度）
        room.target_temp = 25.0

        # 3. 清理状态
        room.ac_on = False
        room.ac_session_start = None
        room.waiting_start_time = None
        room.serving_start_time = None
        room.cooling_paused = False
        room.pause_start_temp = None
        room.last_temp_update = now
        
        self.room_service.updateRoom(room)
        self._remove_request(room.id)
        self._rebalance_queues(force_rotation=True)
        return "已关机"

    def ChangeTemp(self, RoomId: int, TargetTemp: float) -> str:
        room = self.room_service.getRoomById(RoomId)
        if not room or not room.ac_on: raise ValueError("请先开机")
        room.target_temp = TargetTemp
        if room.cooling_paused:
            room.cooling_paused = False; room.pause_start_temp = None
            self._resume_cooling(room)
        self.room_service.updateRoom(room)
        for q in (self.serving_queue, self.waiting_queue):
            for r in q:
                if r.roomId == RoomId: r.targetTemp = TargetTemp
        return "调温成功"

    def ChangeSpeed(self, RoomId: int, FanSpeed: str) -> str:
        room = self.room_service.getRoomById(RoomId)
        if not room or not room.ac_on: raise ValueError("请先开机")
        
        normalized = FanSpeed.upper()
        if (room.fan_speed or "MEDIUM").upper() != normalized and room.serving_start_time:
            self._settle_current_service_period(room, datetime.utcnow(), "CHANGE")
        
        room.fan_speed = normalized
        self.room_service.updateRoom(room)
        self._remove_request(RoomId)
        
        # 重新入队
        now = datetime.utcnow()
        req = RoomRequest(roomId=room.id, fanSpeed=normalized, mode=room.ac_mode, targetTemp=room.target_temp)
        if len(self.serving_queue) < self._capacity():
            req.servingTime = now; self.serving_queue.append(req); self._mark_room_serving(room.id, now)
        else:
            req.waitingTime = now; self.waiting_queue.append(req); self._mark_room_waiting(room.id, now)
            
        self._rebalance_queues(force_rotation=True)
        return "调速成功"

    # === 核心温控算法 (重写增强版) ===
    # === 核心温控算法 (修复无限唤醒 Bug) ===
    def _updateRoomTemperature(self, room) -> None:
        now = datetime.utcnow()
        current_temp = room.current_temp or room.default_temp or 0.0
        new_temp = current_temp
        
        # 计算时间差
        if room.last_temp_update:
            elapsed = ((now - room.last_temp_update).total_seconds() / 60.0) * self._time_factor()
        else:
            elapsed = 0.0

        fan_speed = (room.fan_speed or "MEDIUM").upper()
        rate_map = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 1.0/3.0}
        change_rate = rate_map.get(fan_speed, 0.5)
        rewarming_rate = 0.5 

        # 1. 关机状态
        if not room.ac_on:
            if room.default_temp is not None:
                diff = room.default_temp - current_temp
                if abs(diff) < 0.1: new_temp = room.default_temp
                else:
                    step = max(min(diff, rewarming_rate * elapsed), -rewarming_rate * elapsed)
                    new_temp += step
        
        else:
            # 2. 开机状态
            is_serving = any(r.roomId == room.id for r in self.serving_queue)
            
            # 2.1 服务中
            if is_serving:
                diff = room.target_temp - current_temp
                if abs(diff) < 0.2:
                    # 达到目标，进入待机
                    new_temp = room.target_temp
                    print(f"[Scheduler] Room {room.id} 达标待机")
                    room.cooling_paused = True
                    room.pause_start_temp = new_temp
                    self._pause_cooling(room)
                else:
                    step = max(min(diff, change_rate * elapsed), -change_rate * elapsed)
                    new_temp += step

            # 2.2 待机 (PAUSED) 或 排队 (WAITING) -> 执行回温
            elif room.cooling_paused or not is_serving:
                if room.default_temp is not None:
                    diff_to_default = room.default_temp - current_temp
                    
                    # A. 已经回温到环境温度
                    if abs(diff_to_default) < 0.1:
                        new_temp = room.default_temp
                        # === 核心修复点 ===
                        # 原代码：直接 resume
                        # 新代码：只有当当前温度偏离目标温度超过 1度 时，才 resume
                        # 否则就让它一直保持在环境温度待机（省电）
                        if abs(new_temp - (room.target_temp or 0)) >= 1.0:
                            print(f"[Scheduler] Room {room.id} 环境温度偏离目标，唤醒")
                            room.cooling_paused = False
                            room.pause_start_temp = None
                            self._resume_cooling(room)
                        else:
                            # 保持待机，不做任何操作
                            pass
                            
                    # B. 正在回温途中
                    else:
                        step = max(min(diff_to_default, rewarming_rate * elapsed), -rewarming_rate * elapsed)
                        new_temp += step
                        
                        # 检查是否回温超过 1度 (Hysteresis)
                        # 如果没有 pause_start_temp，就用 target_temp 做基准
                        base_temp = room.pause_start_temp if room.pause_start_temp is not None else room.target_temp
                        if base_temp is not None and abs(new_temp - base_temp) >= 1.0:
                            print(f"[Scheduler] Room {room.id} 回温1度，唤醒")
                            room.cooling_paused = False
                            room.pause_start_temp = None
                            self._resume_cooling(room)

        if abs(new_temp - current_temp) >= 1e-6:
            room.current_temp = round(new_temp, 2)
            room.last_temp_update = now
            self.room_service.updateRoom(room)

    # === 获取状态 ===
    def RequestState(self, RoomId: int) -> dict:
        room = self.room_service.getRoomById(RoomId)
        if not room: raise ValueError("不存在")
        
        # 计算费用
        try:
            from ..services import bill_service
            fee = bill_service.getCurrentFeeDetail(room)
            total = fee.get("total", 0.0) # 房费+空调
            curr = fee.get("current_session_fee", 0.0)
        except: total = 0.0; curr = 0.0

        status = {
            "id": room.id, "room_id": room.id,
            "ac_on": bool(room.ac_on), "ac_mode": room.ac_mode, "fan_speed": room.fan_speed,
            "current_temp": room.current_temp, "currentTemp": room.current_temp,
            "target_temp": room.target_temp, "targetTemp": room.target_temp,
            "total_cost": total, "totalCost": total,
            "current_cost": curr, "currentCost": curr
        }
        
        now = datetime.utcnow()
        qs = "IDLE"; ws=0; ss=0
        if room.cooling_paused: qs="PAUSED"
        else:
            for r in self.serving_queue:
                if r.roomId==RoomId: qs="SERVING"; ss=self._elapsed_seconds(r.servingTime, now); break
            else:
                for i, r in enumerate(self.waiting_queue):
                    if r.roomId==RoomId: qs="WAITING"; ws=self._elapsed_seconds(r.waitingTime, now); break
        
        status.update({"queueState": qs, "waitingSeconds": ws, "servingSeconds": ss})
        return status

    def getScheduleStatus(self) -> dict:
        self._restore_queue_from_database()
        self._deduplicate_queues()
        self._rebalance_queues()
        for r in self.room_service.getAllRooms(): self._updateRoomTemperature(r)
        
        now = datetime.utcnow()
        def _to_pl(q): return [{"roomId": r.roomId, "fanSpeed": r.fanSpeed, "servingSeconds": self._elapsed_seconds(r.servingTime, now), "waitingSeconds": self._elapsed_seconds(r.waitingTime, now)} for r in q]
        
        return {
            "capacity": self._capacity(), "timeSlice": self._time_slice(),
            "servingQueue": _to_pl(self.serving_queue), "waitingQueue": _to_pl(self.waiting_queue)
        }

    def simulateTemperatureUpdate(self) -> dict:
        if not self.serving_queue and not self.waiting_queue:
            from ..models import Room
            if Room.query.filter_by(ac_on=True).count() > 0: self._restore_queue_from_database()
        for r in self.room_service.getAllRooms(): self._updateRoomTemperature(r)
        return {"message": "Updated"}

    def _restore_queue_from_database(self) -> None:
        self._deduplicate_queues()
        from ..models import Room
        active = {r.id for r in Room.query.filter_by(ac_on=True).all()}
        self.serving_queue = [r for r in self.serving_queue if r.roomId in active]
        self.waiting_queue = [r for r in self.waiting_queue if r.roomId in active]
        
        existing = {r.roomId for r in self.serving_queue} | {r.roomId for r in self.waiting_queue}
        now = datetime.utcnow()
        for rid in active:
            if rid in existing: continue
            r = self.room_service.getRoomById(rid)
            if not r or r.cooling_paused: continue
            req = RoomRequest(roomId=r.id, fanSpeed=r.fan_speed, mode=r.ac_mode, targetTemp=r.target_temp)
            if r.serving_start_time: req.servingTime = r.serving_start_time; self.serving_queue.append(req)
            elif r.waiting_start_time: req.waitingTime = r.waiting_start_time; self.waiting_queue.append(req)
            else:
                if len(self.serving_queue) < self._capacity(): req.servingTime = r.ac_session_start or now; self.serving_queue.append(req); self._mark_room_serving(r.id, now)
                else: req.waitingTime = r.ac_session_start or now; self.waiting_queue.append(req); self._mark_room_waiting(r.id, now)
        self._rebalance_queues()