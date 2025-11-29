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
        if fan_speed == "HIGH":
            return 1.0
        if fan_speed == "MEDIUM":
            return 0.5
        return 1.0 / 3.0

    def _time_factor(self) -> float:
        factor = current_app.config.get("TIME_ACCELERATION_FACTOR", 1.0)
        try:
            factor = float(factor)
        except (TypeError, ValueError):
            factor = 1.0
        return factor if factor > 0 else 1.0
    
    def _settle_current_service_period(
        self, room: Room, end_time: datetime, reason: str = "CHANGE"
    ) -> None:
        if not room.serving_start_time:
            return
        
        start_time = room.serving_start_time
        
        # 1. 计算原始分钟数 (含小数)
        # 例如: 物理10秒 + 延迟2秒 = 12秒 -> 乘以6.0 = 72秒 = 1.2分钟
        raw_minutes = ((end_time - start_time).total_seconds() / 60.0) * self._time_factor()
        
        # 2. 使用 round() 进行四舍五入
        duration_minutes = round(raw_minutes)
        
        # 特殊处理：如果是 POWER_OFF 且时长为0，为了记录周期，允许为0
        # 如果是正常运行但不足30秒（系统时间），算作0费用是合理的（这是防抖动）
        # 如果你非常在意"不足1分钟按1分钟算"，可以只对 POWER_OFF 且总时长极短的情况做特殊处理
        # 但对于"中间状态切换"，算0是最好的。
        
        # 使用当前风速的费率
        rate = self._rate_by_fan_speed(room.fan_speed)
        cost = rate * duration_minutes
        
        customer_id = None
        if room.status == "OCCUPIED":
            from ..services import customer_service
            customer = customer_service.getCustomerByRoomId(room.id)
            if customer:
                customer_id = customer.id
        
        is_cycle_end = (reason == "POWER_OFF")
        detail_type = "POWER_OFF_CYCLE" if is_cycle_end else "AC"
        
        self.bill_detail_service.createBillDetail(
            room_id=room.id,
            ac_mode=room.ac_mode,
            fan_speed=room.fan_speed,
            start_time=start_time,
            end_time=end_time,
            rate=rate,
            cost=cost,
            customer_id=customer_id,
            detail_type=detail_type,
        )

    def _priority_score(self, request: RoomRequest) -> int:
        score_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return score_map.get((request.fanSpeed or "MEDIUM").upper(), 2)

    def _elapsed_seconds(self, source: Optional[datetime], now: datetime) -> float:
        if not source:
            return 0.0
        return max(0.0, (now - source).total_seconds() * self._time_factor())

    def _remove_from_queue(self, queue: List[RoomRequest], room_id: int) -> Optional[RoomRequest]:
        for idx, req in enumerate(queue):
            if req.roomId == room_id:
                return queue.pop(idx)
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

    def _pause_cooling(self, room: Room) -> None:
        now = datetime.utcnow()
        if room.serving_start_time:
            self._settle_current_service_period(room, now, "PAUSED")
        self._remove_request(room.id)
        room.serving_start_time = None
        room.waiting_start_time = None
        room.ac_session_start = now
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
        self._rebalance_queues()

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
        while self.waiting_queue and len(self.serving_queue) < capacity:
            p = self.waiting_queue.pop(0)
            p.servingTime = now; p.waitingTime = None
            self.serving_queue.append(p)
            self._mark_room_serving(p.roomId, now)
        if len(self.serving_queue) >= capacity and self.waiting_queue:
            high = self.waiting_queue[0]
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

    def _move_to_serving(self, request: RoomRequest, timestamp: datetime) -> None:
        request.servingTime = timestamp
        request.waitingTime = None
        self.serving_queue.append(request)
        self._mark_room_serving(request.roomId, timestamp)

    def _rotate_time_slice(self, *, force: bool = False) -> None:
        if not self.serving_queue: return
        capacity = self._capacity()
        if len(self.serving_queue) < capacity: return
        now = datetime.utcnow()
        limit = self._time_slice()
        to_demote = []
        for req in self.serving_queue:
            if self._elapsed_seconds(req.servingTime, now) >= limit:
                to_demote.append(req)
        to_demote.sort(key=lambda r: self._elapsed_seconds(r.servingTime, now), reverse=True)
        
        for req in to_demote:
            demoted = self._remove_from_queue(self.serving_queue, req.roomId)
            if demoted:
                self._move_to_waiting(demoted, now, "ROTATED")
        
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

    def PowerOn(self, RoomId: int, CurrentRoomTemp: float | None) -> str:
        room_id = RoomId
        current_temp = CurrentRoomTemp
        room = self.room_service.getRoomById(room_id)
        if room is None: raise ValueError("房间不存在")
        if room.ac_on: return "房间空调已开启"

        now = datetime.utcnow()
        if current_temp is not None:
            room.current_temp = current_temp
        elif room.current_temp is None:
            room.current_temp = room.default_temp or current_app.config["HOTEL_DEFAULT_TEMP"]
        
        room.ac_on = True
        room.ac_session_start = now
        room.last_temp_update = now
        room.target_temp = room.target_temp or current_app.config["HOTEL_DEFAULT_TEMP"]

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
        
        self._rebalance_queues()
        self.room_service.updateRoom(room)
        return "空调已开启并进入调度"

    def PowerOff(self, RoomId: int) -> str:
        room_id = RoomId
        room = self.room_service.getRoomById(room_id)
        if room is None: raise ValueError("房间不存在")
        if not room.ac_on: raise ValueError("房间空调尚未开启")

        now = datetime.utcnow()
        if room.serving_start_time:
            self._settle_current_service_period(room, now, "POWER_OFF")
        else:
            customer_id = None
            if room.status == "OCCUPIED":
                from ..services import customer_service
                cust = customer_service.getCustomerByRoomId(room.id)
                if cust: customer_id = cust.id
            self.bill_detail_service.createBillDetail(
                room_id=room.id, ac_mode=room.ac_mode, fan_speed=room.fan_speed,
                start_time=now, end_time=now, rate=0.0, cost=0.0,
                customer_id=customer_id, detail_type="POWER_OFF_CYCLE"
            )

        if room.default_temp is not None:
            room.current_temp = room.default_temp

        # === 新增：关机恢复默认风速 (中风) ===
        room.fan_speed = "MEDIUM"
        # ==================================
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
        return "空调已关闭"

    def ChangeTemp(self, RoomId: int, TargetTemp: float) -> str:
        room_id = RoomId
        room = self.room_service.getRoomById(room_id)
        if not room or not room.ac_on: raise ValueError("请先开启空调")
        room.target_temp = TargetTemp
        if room.cooling_paused:
            room.cooling_paused = False; room.pause_start_temp = None
            self._resume_cooling(room)
        self.room_service.updateRoom(room)
        for q in (self.serving_queue, self.waiting_queue):
            for r in q:
                if r.roomId == room_id: r.targetTemp = TargetTemp
        return "温度已更新"

    def ChangeSpeed(self, RoomId: int, FanSpeed: str) -> str:
        room_id = RoomId
        room = self.room_service.getRoomById(room_id)
        if not room or not room.ac_on: raise ValueError("请先开启空调")
        normalized = FanSpeed.upper()
        old_speed = (room.fan_speed or "MEDIUM").upper()
        if old_speed != normalized and room.serving_start_time:
            now = datetime.utcnow()
            self._settle_current_service_period(room, now, "CHANGE")
            room.ac_session_start = now
        
        room.fan_speed = normalized
        self.room_service.updateRoom(room)
        self._remove_request(room_id)
        now = datetime.utcnow()
        req = RoomRequest(roomId=room.id, fanSpeed=normalized, mode=room.ac_mode, targetTemp=room.target_temp)
        if room.serving_start_time:
            req.servingTime = room.serving_start_time
            self.serving_queue.append(req)
        elif room.waiting_start_time:
            req.waitingTime = room.waiting_start_time
            self.waiting_queue.append(req)
        else:
            if len(self.serving_queue) < self._capacity():
                req.servingTime = now; self.serving_queue.append(req); self._mark_room_serving(room.id, now)
            else:
                req.waitingTime = now; self.waiting_queue.append(req); self._mark_room_waiting(room.id, now)
        self._rebalance_queues(force_rotation=True)
        return "风速已更新"

    def ChangeMode(self, RoomId: int, Mode: str) -> str:
        """切换空调模式（制冷/制热）"""
        room_id = RoomId
        room = self.room_service.getRoomById(room_id)
        if not room:
            raise ValueError("房间不存在")
        
        normalized_mode = Mode.upper()
        if normalized_mode not in ['COOLING', 'HEATING']:
            raise ValueError("无效模式，必须是 COOLING 或 HEATING")
        
        # 如果模式没变，直接返回
        if room.ac_mode == normalized_mode:
            return "模式未改变"
        
        # 切换模式时，重置目标温度为默认值
        if normalized_mode == 'COOLING':
            default_target = current_app.config.get("COOLING_DEFAULT_TARGET", 25.0)
        else:  # HEATING
            default_target = current_app.config.get("HEATING_DEFAULT_TARGET", 22.0)
        
        room.ac_mode = normalized_mode
        room.target_temp = default_target
        room.last_temp_update = datetime.utcnow()
        
        # 如果正在运行，需要更新队列里的请求参数
        for q in (self.serving_queue, self.waiting_queue):
            for r in q:
                if r.roomId == room_id:
                    r.mode = normalized_mode
                    r.targetTemp = default_target
        
        self.room_service.updateRoom(room)
        return f"已切换至 {normalized_mode} 模式，目标温度重置为 {default_target}°C"

    def _updateRoomTemperature(self, room) -> None:
        now = datetime.utcnow()
        current_temp = room.current_temp or room.default_temp or 0.0
        new_temp = current_temp
        
        if room.last_temp_update:
            elapsed = ((now - room.last_temp_update).total_seconds() / 60.0) * self._time_factor()
        else:
            elapsed = (3.0/60.0) * self._time_factor()

        fan_speed = (room.fan_speed or "MEDIUM").upper()
        rate_map = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 1.0/3.0}
        change_rate = rate_map.get(fan_speed, 0.5)
        rewarming_rate = 0.5

        if not room.ac_on:
            if room.default_temp is not None:
                diff = room.default_temp - current_temp
                if abs(diff) < 0.1: new_temp = room.default_temp
                else:
                    step = max(min(diff, rewarming_rate * elapsed), -rewarming_rate * elapsed)
                    new_temp += step
        else:
            is_serving = any(r.roomId == room.id for r in self.serving_queue)
            if is_serving:
                if room.cooling_paused:
                    if room.default_temp is not None:
                        diff = room.default_temp - current_temp
                        if abs(diff) < 0.1:
                            new_temp = room.default_temp
                            room.cooling_paused = False; room.pause_start_temp = None
                        else:
                            step = max(min(diff, rewarming_rate * elapsed), -rewarming_rate * elapsed)
                            new_temp += step
                            if room.pause_start_temp and abs(new_temp - room.pause_start_temp) >= 1.0:
                                room.cooling_paused = False; room.pause_start_temp = None
                else:
                    diff = room.target_temp - current_temp
                    if abs(diff) < 0.2:
                        new_temp = room.target_temp
                        if room.default_temp and abs(room.target_temp - room.default_temp) > 0.2:
                            room.cooling_paused = True; room.pause_start_temp = new_temp
                            self._pause_cooling(room)
                    else:
                        step = max(min(diff, change_rate * elapsed), -change_rate * elapsed)
                        new_temp += step
            elif room.cooling_paused:
                if room.default_temp is not None:
                    diff = room.default_temp - current_temp
                    if abs(diff) < 0.1:
                        new_temp = room.default_temp
                        room.cooling_paused = False; room.pause_start_temp = None
                        self._resume_cooling(room)
                    else:
                        step = max(min(diff, rewarming_rate * elapsed), -rewarming_rate * elapsed)
                        new_temp += step
                        if room.pause_start_temp and abs(new_temp - room.pause_start_temp) >= 1.0:
                            room.cooling_paused = False; room.pause_start_temp = None
                            self._resume_cooling(room)
            else:
                # 排队回温
                if room.default_temp is not None:
                    diff = room.default_temp - current_temp
                    if abs(diff) < 0.1: new_temp = room.default_temp
                    else:
                        step = max(min(diff, rewarming_rate * elapsed), -rewarming_rate * elapsed)
                        new_temp += step

        if abs(new_temp - current_temp) >= 1e-6:
            room.current_temp = round(new_temp, 2)
            room.last_temp_update = now
            self.room_service.updateRoom(room)

    def RequestState(self, RoomId: int) -> dict:
        room = self.room_service.getRoomById(RoomId)
        if not room: raise ValueError("房间不存在")
        
        current_val = 0.0
        total_val = 0.0
        try:
            from ..services import bill_service
            fee_data = bill_service.getCurrentFeeDetail(room)
            current_val = fee_data.get("current_session_fee", 0.0)
            
            # === 核心修改：这里一定要取 'total' 而不是 'total_fee' ===
            # 'total' 包含了 roomFee + acFee
            total_val = fee_data.get("total", 0.0)
        except Exception: 
            pass

        status = {
            "id": room.id, "room_id": room.id,
            "ac_on": bool(room.ac_on), "ac_mode": room.ac_mode, "fan_speed": room.fan_speed,
            "current_temp": room.current_temp if room.current_temp is not None else 0.0,
            "currentTemp": room.current_temp if room.current_temp is not None else 0.0,
            "target_temp": room.target_temp if room.target_temp is not None else 25.0,
            "targetTemp": room.target_temp if room.target_temp is not None else 25.0,
            
            "current_cost": current_val, "currentCost": current_val,
            
            # 这里传给前端的 total_cost 将包含房费
            "total_cost": total_val, "totalCost": total_val
        }
        
        now = datetime.utcnow()
        qs = "IDLE"; ws = 0.0; ss = 0.0; qp = None
        if room.cooling_paused: qs = "PAUSED"
        else:
            for r in self.serving_queue:
                if r.roomId == RoomId: qs = "SERVING"; ss = self._elapsed_seconds(r.servingTime, now); break
            else:
                for i, r in enumerate(self.waiting_queue):
                    if r.roomId == RoomId: qs = "WAITING"; ws = self._elapsed_seconds(r.waitingTime, now); qp = i+1; break
        
        status.update({"queueState": qs, "waitingSeconds": ws, "servingSeconds": ss, "queuePosition": qp})
        return status

    def simulateTemperatureUpdate(self) -> dict:
        if not self.serving_queue and not self.waiting_queue:
            from ..models import Room
            if Room.query.filter_by(ac_on=True).count() > 0:
                self._restore_queue_from_database()
        
        rooms = self.room_service.getAllRooms()
        u = 0
        for r in rooms:
            o = r.current_temp
            self._updateRoomTemperature(r)
            r = self.room_service.getRoomById(r.id)
            if r.current_temp is not None and o is not None and abs(r.current_temp - o) >= 1e-6: u += 1
        return {"message": "Updated", "updatedRooms": u}

    def getScheduleStatus(self) -> dict:
        self._restore_queue_from_database()
        self._deduplicate_queues()
        self._rebalance_queues()
        rooms = self.room_service.getAllRooms()
        for room in rooms: self._updateRoomTemperature(room)
        self._enforce_capacity()
        now = datetime.utcnow()
        def _to_payload(queue: List[RoomRequest]) -> List[Dict[str, object]]:
            payload = []
            for req in queue:
                payload.append({
                    "roomId": req.roomId, "fanSpeed": req.fanSpeed, "mode": req.mode,
                    "targetTemp": req.targetTemp,
                    "waitingSeconds": self._elapsed_seconds(req.waitingTime, now),
                    "servingSeconds": self._elapsed_seconds(req.servingTime, now),
                })
            return payload
        return {
            "capacity": self._capacity(), "timeSlice": self._time_slice(),
            "servingQueue": _to_payload(self.serving_queue), "waitingQueue": _to_payload(self.waiting_queue),
        }

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
            req = RoomRequest(roomId=r.id, fanSpeed=r.fan_speed or "MEDIUM", mode=r.ac_mode, targetTemp=r.target_temp)
            if r.serving_start_time: req.servingTime = r.serving_start_time; self.serving_queue.append(req)
            elif r.waiting_start_time: req.waitingTime = r.waiting_start_time; self.waiting_queue.append(req)
            else:
                if len(self.serving_queue) < self._capacity(): req.servingTime = r.ac_session_start or now; self.serving_queue.append(req); self._mark_room_serving(r.id, req.servingTime)
                else: req.waitingTime = r.ac_session_start or now; self.waiting_queue.append(req); self._mark_room_waiting(r.id, req.waitingTime)
        self._rebalance_queues()