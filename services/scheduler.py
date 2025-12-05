from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from flask import current_app
from sqlalchemy import func

from ..models import Room, RoomRequest, DetailRecord
from ..utils.time_master import clock
from .bill_detail_service import BillDetailService
from .room_service import RoomService

# =============================================================================
# 调度器 (Scheduler) - 最终完美版
# 1. 修正费率计算 (单价恒定 1.0)
# 2. PowerOn: 触发房费账单 (按次计费)
# 3. PowerOff: 增加重置风速和目标温度的逻辑
# 4. RequestState: 修正费用汇总逻辑
# =============================================================================

class Scheduler:
    def __init__(self, room_service: RoomService, bill_detail_service: BillDetailService):
        self.room_service = room_service
        self.bill_detail_service = bill_detail_service
        
        self.serving_queue: List[RoomRequest] = []
        self.waiting_queue: List[RoomRequest] = []
        self._lock = threading.Lock()

    # --- 辅助方法 ---

    def _capacity(self) -> int:
        try:
            return max(1, int(current_app.config.get("HOTEL_AC_TOTAL_COUNT", 3)))
        except: return 3

    def _time_slice(self) -> int:
        try:
            return max(1, int(current_app.config.get("HOTEL_TIME_SLICE", 120)))
        except: return 120

    def _get_simulated_duration(self, start_time: datetime, end_time: datetime) -> float:
        if not start_time or not end_time: return 0.0
        return max(0.0, (end_time - start_time).total_seconds())

    def _priority_score(self, request: RoomRequest) -> int:
        mapping = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return mapping.get((request.fanSpeed or "MEDIUM").upper(), 2)

    def _speed_val(self, speed_str: str) -> int:
        """风速数值化，HIGH=3, MEDIUM=2, LOW=1"""
        mapping = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return mapping.get((speed_str or "MEDIUM").upper(), 2)

    def _remove_request(self, queue: List[RoomRequest], room_id: int) -> None:
        for i in range(len(queue) - 1, -1, -1):
            if queue[i].roomId == room_id:
                queue.pop(i)

    def _get_rate(self, fan_speed: str) -> float:
        """获取单位温差的费率。当前逻辑下，1度温差=1元，不随风速变化。"""
        return 1.0

    # --- 核心逻辑: 温度更新 ---

    def _updateRoomTemperature(self, room: Room, force_update: bool = False) -> None:
        now = clock.now()
        
        if not room.last_temp_update:
            from ..extensions import db
            room.last_temp_update = now
            db.session.commit()
            return

        sim_minutes = self._get_simulated_duration(room.last_temp_update, now) / 60.0
        if sim_minutes <= 0 and not force_update: return

        current_temp = float(room.current_temp or 25.0)
        target_temp = float(room.target_temp or 25.0)
        default_temp = float(room.default_temp or 25.0)
        fan_speed = (room.fan_speed or "MEDIUM").upper()
        mode = (room.ac_mode or "COOLING").upper()

        is_serving = any(r.roomId == room.id for r in self.serving_queue)
        # 补救措施：如果数据库显示在服务但队列里没有(极端情况)，视为服务中
        if not is_serving and room.serving_start_time and not room.cooling_paused:
            is_serving = True

        new_temp = current_temp
        
        if is_serving:
            # 变温速率: High=1.0, Medium=0.5, Low=0.33
            rate_map = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 1.0/3.0}
            rate = rate_map.get(fan_speed, 0.5)
            delta = rate * sim_minutes

            if mode == "COOLING":
                if current_temp > target_temp:
                    new_temp = max(target_temp, current_temp - delta)
            else: # HEATING
                if current_temp < target_temp:
                    new_temp = min(target_temp, current_temp + delta)
            
            # 到达目标温度检查
            if abs(new_temp - target_temp) < 0.01:
                new_temp = target_temp
                if not force_update:
                    # 在调用 _handle_temp_reached 之前，先检查是否已经处理过
                    # 强制刷新 room 对象，确保读取最新的 cooling_paused 状态
                    from ..extensions import db
                    db.session.refresh(room)
                    if not room.cooling_paused:
                        self._handle_temp_reached(room, new_temp)
        else:
            # 回温速率
            rewarm_rate = 0.5
            delta = rewarm_rate * sim_minutes
            if current_temp < default_temp:
                new_temp = min(default_temp, current_temp + delta)
            elif current_temp > default_temp:
                new_temp = max(default_temp, current_temp - delta)
            
            # 回温唤醒检查
            if room.cooling_paused and not force_update:
                pause_base = room.pause_start_temp if room.pause_start_temp is not None else target_temp
                if abs(new_temp - pause_base) >= 1.0:
                    self._handle_rewarm_wake(room)

        # 持久化
        from ..extensions import db
        try:
            room.current_temp = new_temp
            room.last_temp_update = now
            db.session.query(Room).filter(Room.id == room.id).update({
                "current_temp": new_temp,
                "last_temp_update": now
            })
            db.session.commit()
        except Exception:
            db.session.rollback()

    # --- 核心逻辑: 计费 ---

    def _settle_current_service_period(self, room: Room, end_time: datetime, reason: str) -> None:
        if not room.serving_start_time or room.billing_start_temp is None:
            print(f"[Skip Settle] Room {room.id}, no serving_start_time or billing_start_temp, reason={reason}")
            return

        # === 防重复结算：若已存在相同 start_time 的账单，则跳过 ===
        # 必须在计算费用之前检查，避免重复计算
        from ..models import DetailRecord
        from ..extensions import db
        # 强制刷新数据库会话，确保查询到最新提交的数据
        db.session.expire_all()
        
        # 使用 SELECT FOR UPDATE 锁定，防止并发重复创建
        # 如果锁定失败（说明另一个事务正在处理），等待一小段时间后重试
        try:
            exists = db.session.query(DetailRecord.id).filter(
                DetailRecord.room_id == room.id,
                DetailRecord.detail_type == "AC",
                DetailRecord.start_time == room.serving_start_time
            ).with_for_update(nowait=True).first()
        except Exception as lock_error:
            # 如果锁定失败，等待一小段时间后再次检查
            import time
            time.sleep(0.01)  # 等待10毫秒
            db.session.expire_all()
            exists = db.session.query(DetailRecord.id).filter(
                DetailRecord.room_id == room.id,
                DetailRecord.detail_type == "AC",
                DetailRecord.start_time == room.serving_start_time
            ).first()
        
        if exists:
            print(f"[Skip Duplicate] Room {room.id}, start={room.serving_start_time}, reason={reason}, existing_id={exists}")
            return
        
        print(f"[Settle Start] Room {room.id}, start={room.serving_start_time}, reason={reason}")

        start_temp = float(room.billing_start_temp)
        end_temp = float(room.current_temp)
        mode = room.ac_mode or "COOLING"
        
        temp_diff = 0.0
        if mode == "COOLING":
            if end_temp < start_temp: temp_diff = start_temp - end_temp
        else:
            if end_temp > start_temp: temp_diff = end_temp - start_temp

        if temp_diff < 0.001: return

        rate = 1.0  # 费率：1度=1元
        cost = temp_diff * rate
        
        # 调试日志：记录结算详情
        if reason == "POWER_OFF":
            print(f"[Scheduler] PowerOff 结算 Room {room.id}: start_temp={start_temp:.2f}, end_temp={end_temp:.2f}, diff={temp_diff:.2f}, cost={cost:.2f}")
        
        customer_id = None
        if room.status == "OCCUPIED":
            from ..services import customer_service
            c = customer_service.getCustomerByRoomId(room.id)
            if c: customer_id = c.id

        # 在创建详单之前，再次检查是否已存在（双重保险）
        # 防止在检查后、创建前的短暂时间窗口内被并发调用
        db.session.expire_all()
        exists_again = db.session.query(DetailRecord.id).filter(
            DetailRecord.room_id == room.id,
            DetailRecord.detail_type == "AC",
            DetailRecord.start_time == room.serving_start_time
        ).first()
        if exists_again:
            print(f"[Skip Duplicate Before Create] Room {room.id}, start={room.serving_start_time}, reason={reason}, existing_id={exists_again}")
            return
        
        # 创建详单（内部也有防重复检查）
        # 使用 try-except 捕获可能的唯一约束冲突
        try:
            detail = self.bill_detail_service.createBillDetail(
                room_id=room.id,
                ac_mode=mode,
                fan_speed=room.fan_speed,
                start_time=room.serving_start_time,
                end_time=end_time,
                rate=rate,
                cost=cost,
                customer_id=customer_id,
                detail_type="AC"
            )
            print(f"[Scheduler] 结算 AC费 Room {room.id}: {cost:.2f}元, detail_id={detail.id}")
        except Exception as e:
            # 如果创建失败（可能是并发冲突），再次检查是否已存在
            db.session.rollback()
            db.session.expire_all()
            existing_detail = DetailRecord.query.filter(
                DetailRecord.room_id == room.id,
                DetailRecord.detail_type == "AC",
                DetailRecord.start_time == room.serving_start_time
            ).first()
            if existing_detail:
                print(f"[Settle Conflict Resolved] Room {room.id}, start={room.serving_start_time}, reason={reason}, using existing_id={existing_detail.id}")
                return
            else:
                # 如果确实不存在，重新抛出异常
                print(f"[Settle Error] Room {room.id}, start={room.serving_start_time}, reason={reason}, error={e}")
                raise

    # --- 状态迁移 ---

    def _demote_serving_room(self, request: RoomRequest, reason: str) -> None:
        room = self.room_service.getRoomById(request.roomId)
        if not room: return
        now = clock.now()
        
        # 检查是否已经有计费字段，如果没有则跳过结算
        if not room.serving_start_time or room.billing_start_temp is None:
            # 没有计费字段，直接移除队列
            self._remove_request(self.serving_queue, request.roomId)
            self._remove_request(self.waiting_queue, request.roomId)
            request.servingTime = None
            request.waitingTime = now
            self.waiting_queue.append(request)
            from ..extensions import db
            db.session.query(Room).filter(Room.id == room.id).update({
                "waiting_start_time": now
            })
            db.session.commit()
            return
        
        self._updateRoomTemperature(room, force_update=True)
        self._settle_current_service_period(room, now, reason)
        
        # 立即清除计费字段，防止重复结算
        from ..extensions import db
        db.session.query(Room).filter(Room.id == room.id).update({
            "serving_start_time": None,
            "billing_start_temp": None,
        })
        db.session.commit()
        # 同步内存
        room.serving_start_time = None
        room.billing_start_temp = None

        self._remove_request(self.serving_queue, request.roomId)
        self._remove_request(self.waiting_queue, request.roomId)
        
        request.servingTime = None
        request.waitingTime = now
        self.waiting_queue.append(request)

        db.session.query(Room).filter(Room.id == room.id).update({
            "waiting_start_time": now
        })
        db.session.commit()

    def _promote_waiting_room(self, request: RoomRequest) -> None:
        room = self.room_service.getRoomById(request.roomId)
        if not room: return
        now = clock.now()

        self._updateRoomTemperature(room, force_update=True)
        
        self._remove_request(self.waiting_queue, request.roomId)
        self._remove_request(self.serving_queue, request.roomId)
        
        request.waitingTime = None
        request.servingTime = now
        self.serving_queue.append(request)

        start_temp = float(room.current_temp or 25.0)
        from ..extensions import db
        db.session.query(Room).filter(Room.id == room.id).update({
            "serving_start_time": now,
            "waiting_start_time": None,
            "billing_start_temp": start_temp
        })
        db.session.commit()
        room.serving_start_time = now
        room.billing_start_temp = start_temp

    def _handle_temp_reached(self, room: Room, current_temp: float):
        # 使用数据库原子更新来设置 cooling_paused 标志，防止并发重复调用
        # 如果更新影响的行数为0，说明已经被其他线程设置过了，直接返回
        from ..extensions import db
        db.session.refresh(room)  # 强制刷新，读取最新状态
        
        # 检查是否已经有计费字段，如果没有则说明已经被其他操作（如 ChangeSpeed）处理过了
        if not room.serving_start_time or room.billing_start_temp is None:
            print(f"[Skip Temp Reached] Room {room.id} 没有计费字段，可能已被其他操作处理")
            # 即使没有计费字段，也要设置 cooling_paused 标志
            db.session.query(Room).filter(Room.id == room.id).update({
                "cooling_paused": True,
            })
            db.session.commit()
            room.cooling_paused = True
            return
        
        # 使用原子更新：只有当 cooling_paused 为 False 时才更新
        result = db.session.query(Room).filter(
            Room.id == room.id,
            Room.cooling_paused == False
        ).update({
            "cooling_paused": True,
        }, synchronize_session=False)
        db.session.commit()
        
        # 如果更新失败（result == 0），说明已经被其他线程处理过了
        if result == 0:
            print(f"[Skip Temp Reached] Room {room.id} 已经被处理过（cooling_paused=True）")
            return
        
        # 同步内存对象
        room.cooling_paused = True
        
        now = clock.now()
        # 再次检查计费字段（可能在设置标志的过程中被其他操作清除了）
        db.session.refresh(room)
        if room.serving_start_time and room.billing_start_temp is not None:
            # 结算当前服务周期的费用
            self._settle_current_service_period(room, now, "TEMP_REACHED")
            
            # 立即清除计费字段，防止重复结算
            db.session.query(Room).filter(Room.id == room.id).update({
                "serving_start_time": None,
                "billing_start_temp": None,
            })
            db.session.commit()
            # 同步内存对象
            room.serving_start_time = None
            room.billing_start_temp = None
        
        self._remove_request(self.serving_queue, room.id)
        self._remove_request(self.waiting_queue, room.id)
        
        # 更新其他状态
        db.session.query(Room).filter(Room.id == room.id).update({
            "pause_start_temp": current_temp,
            "waiting_start_time": None
        })
        db.session.commit()
        room.pause_start_temp = current_temp
        room.cooling_paused = True
        self._schedule_queues(force=False)

    def _handle_rewarm_wake(self, room: Room):
        from ..extensions import db
        db.session.query(Room).filter(Room.id == room.id).update({
            "cooling_paused": False,
            "pause_start_temp": None
        })
        db.session.commit()
        room.cooling_paused = False
        self._add_request_to_queue(room)

    # --- 调度策略（统一入口） ---

    def _schedule_queues(self, force: bool = False):
        """
        统一调度入口：容量填充 + 等待超时轮转。
        """
        capacity = self._capacity()
        time_slice = self._time_slice()
        now = clock.now()

        # 1) 未满载：用等待队列填充（高风速优先，等待时间靠前优先）
        while len(self.serving_queue) < capacity and self.waiting_queue:
            self.waiting_queue.sort(key=lambda r: (-self._speed_val(r.fanSpeed), r.waitingTime))
            candidate = self.waiting_queue[0]
            self._promote_waiting_room(candidate)

        # 2) 时间片轮转：等待超时的请求尝试踢掉服务时间最长且风速不高于自己的服务者
        if self.waiting_queue and len(self.serving_queue) >= capacity:
            timeout_candidates = []
            for req in self.waiting_queue:
                wait_duration = self._get_simulated_duration(req.waitingTime, now)
                if wait_duration >= time_slice:
                    timeout_candidates.append(req)

            if timeout_candidates:
                timeout_candidates.sort(key=lambda r: -self._speed_val(r.fanSpeed))
                challenger = timeout_candidates[0]

                targets = [r for r in self.serving_queue if self._speed_val(r.fanSpeed) <= self._speed_val(challenger.fanSpeed)]
                if targets:
                    targets.sort(key=lambda r: -self._get_simulated_duration(r.servingTime, now))
                    victim = targets[0]
                    print(f"[Schedule] 触发时间片轮转: Room {challenger.roomId} 替换 Room {victim.roomId}")
                    self._demote_serving_room(victim, "TIME_SLICE_ROTATION")
                    self._promote_waiting_room(challenger)

    # --- API ---

    def _add_request_to_queue(self, room: Room):
        """新增请求入口：包含优先级抢占与等待策略"""
        req = RoomRequest(roomId=room.id, fanSpeed=room.fan_speed, mode=room.ac_mode, targetTemp=room.target_temp)
        now = clock.now()
        self._remove_request(self.serving_queue, room.id)
        self._remove_request(self.waiting_queue, room.id)
        
        capacity = self._capacity()

        # 未满载：直接服务
        if len(self.serving_queue) < capacity:
            req.servingTime = now
            self.serving_queue.append(req)
            self._mark_serving_db(room.id, now, room.current_temp)
            return

        # 已满载：按风速比较
        req_speed = self._speed_val(req.fanSpeed)
        serving_speeds = [self._speed_val(r.fanSpeed) for r in self.serving_queue]
        min_serving_speed = min(serving_speeds)

        if req_speed > min_serving_speed:
            # 优先级抢占：踢掉最低风速中服务时间最长的
            candidates = [r for r in self.serving_queue if self._speed_val(r.fanSpeed) == min_serving_speed]
            candidates.sort(key=lambda r: -self._get_simulated_duration(r.servingTime, now))
            victim = candidates[0]
            print(f"[Schedule] 触发优先级抢占: Room {req.roomId} 抢占 Room {victim.roomId}")
            self._demote_serving_room(victim, "PRIORITY_PREEMPTION")
            req.servingTime = now
            self.serving_queue.append(req)
            self._mark_serving_db(room.id, now, room.current_temp)
        else:
            # 风速相等或更低：进入等待队列，后续由 _schedule_queues 处理时间片轮转
            req.waitingTime = now
            self.waiting_queue.append(req)
            self._mark_waiting_db(room.id, now)
            print(f"[Schedule] Room {req.roomId} 进入等待队列 (风速<=最小服务风速)")

    def _mark_serving_db(self, rid, time, temp):
        from ..extensions import db
        t = float(temp or 25.0)
        db.session.query(Room).filter(Room.id == rid).update({
            "serving_start_time": time, "billing_start_temp": t, "waiting_start_time": None
        })
        db.session.commit()
        r = self.room_service.getRoomById(rid)
        if r: r.billing_start_temp = t

    def _mark_waiting_db(self, rid, time):
        from ..extensions import db
        db.session.query(Room).filter(Room.id == rid).update({
            "waiting_start_time": time, "serving_start_time": None, "billing_start_temp": None
        })
        db.session.commit()

    def PowerOn(self, RoomId: int, CurrentRoomTemp: float | None) -> str:
        with self._lock:
            from ..extensions import db
            room = self.room_service.getRoomById(RoomId)
            if not room: return "错误"
            # 强制刷新，确保读取数据库中的最新数据（避免缓存问题）
            db.session.refresh(room)
            if room.ac_on: return "已开启"
            
            now = clock.now()
            temp = float(CurrentRoomTemp) if CurrentRoomTemp is not None else float(room.current_temp or 25.0)
            
            # --- 关键: 按次收取房费 ---
            enable_cycle_fee = current_app.config.get("ENABLE_AC_CYCLE_DAILY_FEE", False)
            if enable_cycle_fee:
                fee = room.daily_rate if room.daily_rate is not None else 0.0
                if fee > 0:
                    # 创建一条“房费”类型的账单
                    self.bill_detail_service.createBillDetail(
                        room_id=room.id,
                        ac_mode="NONE",
                        fan_speed="NONE",
                        start_time=now,
                        end_time=now,
                        rate=0.0,
                        cost=fee,
                        customer_id=None, 
                        detail_type="ROOM_FEE"
                    )
                    print(f"[Scheduler] Room {room.id} 开机: 收取房费 {fee} 元")

            db.session.query(Room).filter(Room.id == room.id).update({
                "ac_on": True, "current_temp": temp, "ac_session_start": now,
                "last_temp_update": now, "cooling_paused": False
            })
            db.session.commit()
            
            room.ac_on = True
            room.current_temp = temp
            room.last_temp_update = now
            
            self._add_request_to_queue(room)
            return "空调已开启"

    def PowerOff(self, RoomId: int) -> str:
        with self._lock:
            from ..extensions import db
            room = self.room_service.getRoomById(RoomId)
            if not room: return "未开启"
            # 强制刷新，确保读取数据库中的最新数据
            db.session.refresh(room)
            if not room.ac_on: return "未开启"
            now = clock.now()
            
            # 1. 结算当前未完成的空调费
            # 先更新温度到最新状态，然后使用更新后的温度进行结算
            # 注意：必须在重置温度之前完成结算，确保使用实际服务结束时的温度
            self._updateRoomTemperature(room, force_update=True)
            self._settle_current_service_period(room, now, "POWER_OFF")
            
            # 2. 立即清除计费相关字段并设置 ac_on=False，防止 RequestState 重复计算 pending 费用
            # 必须在数据库提交前清除，确保后续查询不会计算 pending 费用
            from ..extensions import db
            db.session.query(Room).filter(Room.id == room.id).update({
                "ac_on": False,  # 立即设置为 False，防止 RequestState 计算 pending 费用
                "serving_start_time": None,
                "billing_start_temp": None,
            })
            db.session.commit()
            # 同步内存对象
            room.ac_on = False
            room.serving_start_time = None
            room.billing_start_temp = None
            
            # 3. 移除队列
            self._remove_request(self.serving_queue, room.id)
            self._remove_request(self.waiting_queue, room.id)
            
            # 4. 关机重置状态：重置温度、风速到默认值
            # 决定重置的默认值
            mode = (room.ac_mode or "COOLING").upper()
            default_target = 22.0 if mode == "HEATING" else 25.0  # 目标温度默认值
            default_speed = "MEDIUM"  # 风速默认值
            # 当前温度重置为房间的默认温度（如果房间有 default_temp，使用它；否则使用 25.0）
            default_current_temp = float(room.default_temp) if room.default_temp is not None else 25.0

            db.session.query(Room).filter(Room.id == room.id).update({
                "ac_session_start": None, 
                "waiting_start_time": None, 
                "cooling_paused": False, 
                "pause_start_temp": None,
                # === 重置温度和风速到默认值 ===
                "current_temp": default_current_temp,  # 重置当前温度为默认温度
                "target_temp": default_target,         # 重置目标温度为默认值
                "fan_speed": default_speed,            # 重置风速为 MEDIUM
                "last_temp_update": None                # 清除温度更新时间，下次开机时重新初始化
            })
            db.session.commit()
            
            # 同步内存对象（ac_on 已在前面设置）
            room.current_temp = default_current_temp
            room.target_temp = default_target
            room.fan_speed = default_speed
            room.last_temp_update = None
            
            self._schedule_queues(force=True)
            return "空调已关闭"

    def ChangeTemp(self, RoomId: int, TargetTemp: float) -> str:
        with self._lock:
            from ..extensions import db
            room = self.room_service.getRoomById(RoomId)
            if not room: return "错误"
            # 强制刷新，确保读取数据库中的最新数据
            db.session.refresh(room)
            if not room.ac_on: return "错误"
            
            # 校验目标温度是否在模式对应的范围内
            if TargetTemp is None:
                return "错误"
            try:
                target_val = float(TargetTemp)
            except (TypeError, ValueError):
                return "错误"
            
            mode = (room.ac_mode or "COOLING").upper()
            if mode == "HEATING":
                min_t = current_app.config.get("HEATING_MIN_TEMP", 18.0)
                max_t = current_app.config.get("HEATING_MAX_TEMP", 25.0)
            else:
                min_t = current_app.config.get("COOLING_MIN_TEMP", 18.0)
                max_t = current_app.config.get("COOLING_MAX_TEMP", 28.0)
            
            if not (min_t <= target_val <= max_t):
                return f"温度超限 ({min_t}-{max_t})"
            
            db.session.query(Room).filter(Room.id == room.id).update({"target_temp": target_val})
            db.session.commit()
            room.target_temp = target_val
            
            if room.cooling_paused:
                db.session.query(Room).filter(Room.id == room.id).update({"cooling_paused": False, "pause_start_temp": None})
                db.session.commit()
                self._add_request_to_queue(room)
            return "温度已设定"

    def ChangeSpeed(self, RoomId: int, FanSpeed: str) -> str:
        with self._lock:
            from ..extensions import db
            room = self.room_service.getRoomById(RoomId)
            if not room: return "错误"
            # 强制刷新，确保读取数据库中的最新数据
            db.session.refresh(room)
            if not room.ac_on: return "错误"
            
            new_speed = FanSpeed.upper()
            if room.fan_speed == new_speed: return "未变"
            now = clock.now()
            
            # 保存旧的计费起点，用于结算
            old_serving_start_time = room.serving_start_time
            old_billing_start_temp = room.billing_start_temp
            
            if old_serving_start_time and old_billing_start_temp is not None:
                self._updateRoomTemperature(room, force_update=True)
                # 确保使用旧的计费起点进行结算
                room.serving_start_time = old_serving_start_time
                room.billing_start_temp = old_billing_start_temp
                self._settle_current_service_period(room, now, "CHANGE_SPEED")
                
                # 立即清除计费字段，防止重复结算
                # 同时设置 cooling_paused，防止温度达到目标时再次结算
                db.session.query(Room).filter(Room.id == room.id).update({
                    "serving_start_time": None,
                    "billing_start_temp": None,
                    "cooling_paused": True,  # 防止温度达到目标时再次结算
                })
                db.session.commit()
                # 同步内存对象
                room.serving_start_time = None
                room.billing_start_temp = None
                room.cooling_paused = True

            from ..extensions import db
            db.session.query(Room).filter(Room.id == room.id).update({"fan_speed": new_speed})
            db.session.commit()
            room.fan_speed = new_speed
            
            # 调用 _add_request_to_queue，它会重新设置计费起点（如果需要）
            # 注意：如果房间已经在 serving_queue 中，_add_request_to_queue 会重新设置 serving_start_time
            # 但此时 cooling_paused 已经是 True，所以 _updateRoomTemperature 不会触发 _handle_temp_reached
            self._add_request_to_queue(room)
            
            # 如果房间重新进入服务队列，需要清除 cooling_paused 标志
            db.session.refresh(room)
            if room.serving_start_time is not None:
                # 房间重新开始服务，清除 cooling_paused 标志
                db.session.query(Room).filter(Room.id == room.id).update({
                    "cooling_paused": False,
                })
                db.session.commit()
                room.cooling_paused = False
            
            return "风速已调整"

    def ChangeMode(self, RoomId: int, Mode: str) -> str:
        with self._lock:
            from ..extensions import db
            room = self.room_service.getRoomById(RoomId)
            if not room: return "错误"
            # 强制刷新，确保读取数据库中的最新数据
            db.session.refresh(room)
            new_mode = Mode.upper()
            if new_mode == room.ac_mode: return "未变"
            now = clock.now()
            
            if room.serving_start_time and room.billing_start_temp is not None:
                self._updateRoomTemperature(room, force_update=True)
                self._settle_current_service_period(room, now, "CHANGE_MODE")
                
                # 立即清除计费字段，防止重复结算
                db.session.query(Room).filter(Room.id == room.id).update({
                    "serving_start_time": None,
                    "billing_start_temp": None,
                })
                db.session.commit()
                # 同步内存对象
                room.serving_start_time = None
                room.billing_start_temp = None
                
                # 重新设置计费起点
                self._mark_serving_db(room.id, now, room.current_temp)

            default_target = 22.0 if new_mode == "HEATING" else 25.0
            from ..extensions import db
            db.session.query(Room).filter(Room.id == room.id).update({"ac_mode": new_mode, "target_temp": default_target})
            db.session.commit()
            room.ac_mode = new_mode
            room.target_temp = default_target
            self._add_request_to_queue(room)
            return "模式已切换"

    # --- 监控 ---
    
    def simulateTemperatureUpdate(self) -> dict:
        updated = 0
        with self._lock:
            from ..models import Room
            rooms = Room.query.filter_by(ac_on=True).all()
            for room in rooms:
                old = room.current_temp
                self._updateRoomTemperature(room)
                if abs((room.current_temp or 0) - (old or 0)) > 0.001:
                    updated += 1
            self._schedule_queues()
        return {"updated": updated}

    def RequestState(self, RoomId: int) -> dict:
        """
        状态查询: 动态计算费用，返回房费、空调费分开的数据
        """
        room = self.room_service.getRoomById(RoomId)
        if not room: return {}
        
        from ..extensions import db
        # 强制刷新 room 对象，确保读取到最新的数据库状态
        # 这很重要，特别是在 PowerOff 后立即查询时
        db.session.refresh(room)
        
        # 1. 计算房费（ROOM_FEE 类型的账单总和）
        room_fee = db.session.query(func.sum(DetailRecord.cost))\
            .filter(DetailRecord.room_id == room.id,
                   DetailRecord.detail_type == "ROOM_FEE").scalar()
        room_fee = float(room_fee) if room_fee else 0.0
        
        # 如果未开启循环计费，则需要手动加上静态房费
        enable_cycle_fee = current_app.config.get("ENABLE_AC_CYCLE_DAILY_FEE", False)
        if not enable_cycle_fee:
            room_fee = float(room.daily_rate or 0.0)
        
        # 2. 计算历史空调费（AC 类型的账单总和）
        ac_fee_history = db.session.query(func.sum(DetailRecord.cost))\
            .filter(DetailRecord.room_id == room.id,
                   DetailRecord.detail_type == "AC").scalar()
        ac_fee_history = float(ac_fee_history) if ac_fee_history else 0.0
        
        # 3. 计算当前未结算的空调费 (Pending AC Fee)
        ac_fee_pending = 0.0
        if room.ac_on and room.serving_start_time and room.billing_start_temp is not None:
            curr = float(room.current_temp or 25)
            start = float(room.billing_start_temp)
            diff = 0.0
            if (room.ac_mode or "COOLING") == "COOLING":
                if curr < start: diff = start - curr
            else:
                if curr > start: diff = curr - start

            if diff > 0:
                ac_fee_pending = diff * 1.0  # 费率恒为1
        
        ac_fee_total = ac_fee_history + ac_fee_pending
        total_cost = room_fee + ac_fee_total
        
        # 4. 计算调度次数（AC 类型的账单记录数，每次服务周期结算一次）
        schedule_count = db.session.query(func.count(DetailRecord.id))\
            .filter(DetailRecord.room_id == room.id,
                   DetailRecord.detail_type == "AC").scalar()
        schedule_count = int(schedule_count) if schedule_count else 0

        # 5. 获取客户ID
        customer_id = None
        if room.status == "OCCUPIED":
            from ..services import customer_service
            customer = customer_service.getCustomerByRoomId(room.id)
            if customer:
                customer_id = customer.id

        # 队列状态判定（增强版）
        qs = "IDLE"
        if room.cooling_paused:
            qs = "PAUSED"
        elif any(r.roomId == room.id for r in self.serving_queue):
            qs = "SERVING"
        elif any(r.roomId == room.id for r in self.waiting_queue):
            qs = "WAITING"
        else:
            # 不在任何队列，但空调开着，可能刚达目标温度未设置 cooling_paused
            # 如果当前温度已接近目标温度，则标记为 PAUSED
            try:
                if room.ac_on and abs(float(room.current_temp or 0) - float(room.target_temp or 0)) < 0.1:
                    qs = "PAUSED"
            except Exception:
                pass

        return {
            "room_id": room.id,
            "ac_on": room.ac_on,
            "current_temp": round(float(room.current_temp or 0), 2),
            "currentTemp": round(float(room.current_temp or 0), 2),
            "target_temp": float(room.target_temp or 25),
            "targetTemp": float(room.target_temp or 25),
            "mode": room.ac_mode,
            "ac_mode": room.ac_mode,
            "fan_speed": room.fan_speed,
            "fanSpeed": room.fan_speed,
            "state": qs, "queueState": qs, "queue_state": qs,
            "total_cost": round(total_cost, 2),
            "room_fee": round(room_fee, 2),
            "ac_fee": round(ac_fee_total, 2),
            "schedule_count": schedule_count,
            "customer_id": customer_id
        }
    
    def getScheduleStatus(self):
        with self._lock:
            now = clock.now()
            s_list = []
            for r in self.serving_queue:
                sec = self._get_simulated_duration(r.servingTime, now)
                s_list.append({"roomId": r.roomId, "fanSpeed": r.fanSpeed, "servingSeconds": sec, "totalSeconds": sec})
            w_list = []
            for r in self.waiting_queue:
                sec = self._get_simulated_duration(r.waitingTime, now)
                w_list.append({"roomId": r.roomId, "fanSpeed": r.fanSpeed, "waitingSeconds": sec})
            
            return {
                "capacity": self._capacity(),
                "timeSlice": self._time_slice(),
                "servingQueue": s_list,
                "waitingQueue": w_list
            }