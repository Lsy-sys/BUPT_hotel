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
            return current_app.config["BILLING_AC_RATE_HIGH"]
        if fan_speed == "MEDIUM":
            return current_app.config["BILLING_AC_RATE_MEDIUM"]
        return current_app.config["BILLING_AC_RATE_LOW"]

    def _time_factor(self) -> float:
        factor = current_app.config.get("TIME_ACCELERATION_FACTOR", 1.0)
        try:
            factor = float(factor)
        except (TypeError, ValueError):
            factor = 1.0
        return factor if factor > 0 else 1.0

    def _priority_score(self, request: RoomRequest) -> int:
        score_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return score_map.get((request.fanSpeed or "MEDIUM").upper(), 2)

    def _elapsed_seconds(self, source: Optional[datetime], now: datetime) -> float:
        if not source:
            return 0.0
        return max(0.0, (now - source).total_seconds() * self._time_factor())

    def _remove_from_queue(
        self, queue: List[RoomRequest], room_id: int
    ) -> Optional[RoomRequest]:
        for idx, req in enumerate(queue):
            if req.roomId == room_id:
                return queue.pop(idx)
        return None

    def _mark_room_serving(self, room_id: int, started_at: datetime) -> None:
        room = self.room_service.getRoomById(room_id)
        if not room:
            return
        room.serving_start_time = started_at
        room.waiting_start_time = None
        self.room_service.updateRoom(room)

    def _mark_room_waiting(self, room_id: int, started_at: datetime) -> None:
        room = self.room_service.getRoomById(room_id)
        if not room:
            return
        room.waiting_start_time = started_at
        room.serving_start_time = None
        self.room_service.updateRoom(room)

    def _remove_request(self, room_id: int) -> None:
        self._remove_from_queue(self.serving_queue, room_id)
        self._remove_from_queue(self.waiting_queue, room_id)
    
    def _pause_cooling(self, room: Room) -> None:
        """暂停服务：从队列移除，但保持ac_on状态"""
        self._remove_request(room.id)
        room.serving_start_time = None
        room.waiting_start_time = None
        self.room_service.updateRoom(room)
        # 移除后重新平衡队列，让等待队列中的房间补充
        self._rebalance_queues()
    
    def _resume_cooling(self, room: Room) -> None:
        """恢复服务：重新加入队列（保持原有参数）"""
        now = datetime.utcnow()
        request = RoomRequest(
            roomId=room.id,
            fanSpeed=room.fan_speed,
            mode=room.ac_mode,
            targetTemp=room.target_temp,
        )
        
        # 根据容量决定加入哪个队列
        capacity = self._capacity()
        if len(self.serving_queue) < capacity:
            request.servingTime = now
            self.serving_queue.append(request)
            self._mark_room_serving(room.id, now)
        else:
            request.waitingTime = now
            self.waiting_queue.append(request)
            self._mark_room_waiting(room.id, now)
        
        # 重新平衡队列
        self._rebalance_queues()
    
    def _deduplicate_queues(self) -> None:
        """清理队列中的重复房间，每个房间只保留一个实例（保留第一个）"""
        seen_room_ids = set()
        # 清理服务队列
        new_serving = []
        for req in self.serving_queue:
            if req.roomId not in seen_room_ids:
                seen_room_ids.add(req.roomId)
                new_serving.append(req)
        self.serving_queue = new_serving
        
        # 清理等待队列
        new_waiting = []
        for req in self.waiting_queue:
            if req.roomId not in seen_room_ids:
                seen_room_ids.add(req.roomId)
                new_waiting.append(req)
        self.waiting_queue = new_waiting

    def _sort_waiting_queue(self) -> None:
        if not self.waiting_queue:
            return
        now = datetime.utcnow()
        self.waiting_queue.sort(
            key=lambda r: (
                -self._priority_score(r),
                r.waitingTime or now,
                r.roomId,
            )
        )

    def _promote_waiting_room(self) -> None:
        if not self.waiting_queue:
            return
        capacity = self._capacity()
        if len(self.serving_queue) >= capacity:
            return
        self._sort_waiting_queue()
        now = datetime.utcnow()
        while self.waiting_queue and len(self.serving_queue) < capacity:
            promoted = self.waiting_queue.pop(0)
            promoted.servingTime = now
            promoted.waitingTime = None
            self.serving_queue.append(promoted)
            self._mark_room_serving(promoted.roomId, now)

    def _move_to_waiting(self, request: RoomRequest, timestamp: datetime) -> None:
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
        """时间片调度：服务队列中服务时长最长的（达到2分钟）移到等待队列"""
        if not self.waiting_queue or not self.serving_queue:
            return
        capacity = self._capacity()
        if len(self.serving_queue) < capacity:
            return
        now = datetime.utcnow()
        time_slice_seconds = self._time_slice()
        
        # 检查服务队列中是否有服务时长达到2分钟的房间，移到等待队列
        serving_to_demote = []
        for req in self.serving_queue:
            serving_elapsed = self._elapsed_seconds(req.servingTime, now)
            if serving_elapsed >= time_slice_seconds:
                serving_to_demote.append((serving_elapsed, req))
        
        # 按服务时长从长到短排序，优先移出服务时间最长的
        serving_to_demote.sort(key=lambda x: x[0], reverse=True)
        
        # 将服务时长达到2分钟的房间移到等待队列
        for _, req in serving_to_demote:
            demoted = self._remove_from_queue(self.serving_queue, req.roomId)
            if demoted:
                self._move_to_waiting(demoted, now)
        
        # 然后从等待队列中按优先级补充到服务队列
        self._sort_waiting_queue()
        while self.waiting_queue and len(self.serving_queue) < capacity:
            promoted = self.waiting_queue.pop(0)
            self._move_to_serving(promoted, now)

    def _enforce_capacity(self) -> None:
        """强制限制服务队列不超过容量，超出部分移到等待队列"""
        capacity = self._capacity()
        now = datetime.utcnow()
        
        # 如果服务队列超过容量，将超出部分移到等待队列
        while len(self.serving_queue) > capacity:
            # 按优先级（低优先）和服务时间（长优先）排序，优先移除优先级低、服务时间长的
            # 优先级分数越小，优先级越低，应该优先移除
            self.serving_queue.sort(
                key=lambda req: (
                    self._priority_score(req),  # 优先级分数小的先移除
                    req.servingTime or now,     # 服务时间长的先移除
                    req.roomId,
                )
            )
            # 移除优先级最低的（或服务时间最长的）
            demoted = self.serving_queue.pop(0)
            self._move_to_waiting(demoted, now)
        
        # 如果服务队列未满，从等待队列补充
        self._promote_waiting_room()

    def _rebalance_queues(self, *, force_rotation: bool = False) -> None:
        # 先强制限制容量
        self._enforce_capacity()
        # 然后执行轮转
        self._rotate_time_slice(force=force_rotation)

    def PowerOn(self, RoomId: int, CurrentRoomTemp: float | None) -> str:
        room_id = RoomId
        current_temp = CurrentRoomTemp
        room = self.room_service.getRoomById(room_id)
        if room is None:
            raise ValueError("房间不存在")
        if room.ac_on:
            return "房间空调已开启"

        now = datetime.utcnow()
        # 只有在明确提供了当前温度时才更新，否则保持房间的现有温度
        if current_temp is not None:
            room.current_temp = current_temp
        # 如果房间当前温度为None，使用默认温度
        elif room.current_temp is None:
            room.current_temp = room.default_temp or current_app.config["HOTEL_DEFAULT_TEMP"]
        room.ac_on = True
        room.ac_session_start = now
        # 初始化温度更新时间
        room.last_temp_update = now
        room.target_temp = room.target_temp or current_app.config["HOTEL_DEFAULT_TEMP"]
        # 不要自动改变房间状态，只有办理入住时才改为OCCUPIED
        # room.status = "OCCUPIED" if room.status == "AVAILABLE" else room.status

        request = RoomRequest(
            roomId=room.id,
            fanSpeed=room.fan_speed,
            mode=room.ac_mode,
            targetTemp=room.target_temp,
        )

        # 检查服务队列容量
        capacity = self._capacity()
        if len(self.serving_queue) < capacity:
            request.servingTime = now
            self.serving_queue.append(request)
            self._mark_room_serving(room.id, now)
        else:
            request.waitingTime = now
            self.waiting_queue.append(request)
            self._mark_room_waiting(room.id, now)
        
        # 强制重新平衡队列，确保不超过容量
        self._rebalance_queues()

        self.room_service.updateRoom(room)
        return "空调已开启并进入调度"

    def PowerOff(self, RoomId: int) -> str:
        room_id = RoomId
        room = self.room_service.getRoomById(room_id)
        if room is None:
            raise ValueError("房间不存在")
        if not room.ac_on:
            raise ValueError("房间空调尚未开启")

        now = datetime.utcnow()
        start_time = room.ac_session_start or now
        duration_minutes = max(
            1,
            int(((now - start_time).total_seconds() / 60.0) * self._time_factor()),
        )
        rate = self._rate_by_fan_speed(room.fan_speed)
        cost = rate * duration_minutes

        # 如果房间已入住，获取customer_id；否则为None（管理员开启的空调）
        customer_id = None
        if room.status == "OCCUPIED":
            from ..services import customer_service
            customer = customer_service.getCustomerByRoomId(room_id)
            if customer:
                customer_id = customer.id

        self.bill_detail_service.createBillDetail(
            room_id=room.id,
            ac_mode=room.ac_mode,
            fan_speed=room.fan_speed,
            start_time=start_time,
            end_time=now,
            rate=rate,
            cost=cost,
            customer_id=customer_id,
        )

        room.ac_on = False
        room.ac_session_start = None
        room.waiting_start_time = None
        room.serving_start_time = None
        room.cooling_paused = False
        room.pause_start_temp = None
        # 更新温度更新时间，以便温度回归逻辑正常工作
        room.last_temp_update = now
        self.room_service.updateRoom(room)

        self._remove_request(room.id)
        # 关机后强制重新平衡队列，确保等待队列中的房间能补充到服务队列
        self._rebalance_queues(force_rotation=True)
        return "空调已关闭"

    def ChangeTemp(self, RoomId: int, TargetTemp: float) -> str:
        room_id = RoomId
        target_temp = TargetTemp
        room = self.room_service.getRoomById(room_id)
        if room is None:
            raise ValueError("房间不存在")
        if not room.ac_on:
            raise ValueError("请先开启空调")
        room.target_temp = target_temp
        if room.cooling_paused:
            room.cooling_paused = False
            room.pause_start_temp = None
            self._resume_cooling(room)
        self.room_service.updateRoom(room)
        for queue in (self.serving_queue, self.waiting_queue):
            for req in queue:
                if req.roomId == room_id:
                    req.targetTemp = target_temp
        return "目标温度已更新"

    def ChangeSpeed(self, RoomId: int, FanSpeed: str) -> str:
        room_id = RoomId
        fan_speed = FanSpeed
        room = self.room_service.getRoomById(room_id)
        if room is None:
            raise ValueError("房间不存在")
        if not room.ac_on:
            raise ValueError("请先开启空调")
        normalized = fan_speed.upper()
        if normalized not in {"LOW", "MEDIUM", "HIGH"}:
            raise ValueError("无效风速")
        room.fan_speed = normalized
        self.room_service.updateRoom(room)

        # 先移除队列中该房间的所有实例（防止重复）
        self._remove_request(room_id)
        
        # 如果空调是开启的，重新加入队列
        now = datetime.utcnow()
        request = RoomRequest(
            roomId=room.id,
            fanSpeed=normalized,
            mode=room.ac_mode,
            targetTemp=room.target_temp,
        )
        
        # 根据房间的serving_start_time和waiting_start_time判断应该加入哪个队列
        capacity = self._capacity()
        if room.serving_start_time:
            # 如果房间有serving_start_time，说明应该在服务队列
            request.servingTime = room.serving_start_time
            self.serving_queue.append(request)
        elif room.waiting_start_time:
            # 如果房间有waiting_start_time，说明应该在等待队列
            request.waitingTime = room.waiting_start_time
            self.waiting_queue.append(request)
        else:
            # 如果都没有，根据当前容量决定
            if len(self.serving_queue) < capacity:
                request.servingTime = room.ac_session_start or now
                self.serving_queue.append(request)
                self._mark_room_serving(room.id, request.servingTime)
            else:
                request.waitingTime = room.ac_session_start or now
                self.waiting_queue.append(request)
                self._mark_room_waiting(room.id, request.waitingTime)
        
        # 重新平衡队列（会重新排序，确保优先级正确）
        self._rebalance_queues(force_rotation=True)
        return "风速已更新"

    def getRoomACAccumulatedData(self, room_id: int) -> dict:
        from ..models import DetailRecord

        details = DetailRecord.query.filter_by(room_id=room_id).all()
        total_duration = sum(detail.duration for detail in details)
        total_cost = sum(detail.cost for detail in details)
        return {"totalDuration": total_duration, "totalCost": total_cost}

    def _updateRoomTemperature(self, room) -> None:
        """更新单个房间的当前温度，根据风速和时间间隔调整变化速度
        高风: 1度/1分钟
        中风: 1度/2分钟  
        低风: 1度/3分钟
        
        达到目标温度后暂停服务，启动回温程序（每分钟回温0.5℃）
        回温1℃后重新加入队列
        """
        now = datetime.utcnow()
        current_temp = room.current_temp or room.default_temp or 0.0
        new_temp = current_temp
        
        # 计算从上次更新到现在的时间差（分钟）
        if room.last_temp_update:
            elapsed_minutes = (
                (now - room.last_temp_update).total_seconds() / 60.0 * self._time_factor()
            )
        else:
            # 如果是第一次更新，假设间隔为3秒（前端刷新间隔）
            elapsed_minutes = (3.0 / 60.0) * self._time_factor()
        
        # 根据风速确定温度变化速度（度/分钟）
        fan_speed = (room.fan_speed or "MEDIUM").upper()
        if fan_speed == "HIGH":
            change_rate = 1.0  # 1度/分钟
        elif fan_speed == "MEDIUM":
            change_rate = 0.5  # 1度/2分钟 = 0.5度/分钟
        else:  # LOW
            change_rate = 1.0 / 3.0  # 1度/3分钟 ≈ 0.333度/分钟
        
        if room.ac_on and room.target_temp is not None:
            # 检查房间是否在服务队列中
            is_serving = any(req.roomId == room.id for req in self.serving_queue)
            
            # 如果房间在等待队列中（不在服务队列中），应该回温
            # 因为虽然空调开着，但实际上没有在服务
            if not is_serving and not room.cooling_paused:
                # 等待队列中的房间应该回温，设置暂停状态
                room.cooling_paused = True
                if room.pause_start_temp is None:
                    # 记录开始等待时的温度
                    room.pause_start_temp = current_temp
            
            # 如果正在回温（cooling_paused=True），执行回温逻辑
            if room.cooling_paused:
                # 回温速度：每分钟回温0.5℃
                rewarming_rate = 0.5  # 度/分钟
                max_change = rewarming_rate * elapsed_minutes
                
                # 回温方向：从目标温度向 default_temp（环境温度）回温
                if room.default_temp is None:
                    # 如果没有默认温度，无法回温，保持当前温度
                    new_temp = current_temp
                else:
                    # 计算向 default_temp 回温的方向和步长
                    # 回温总是从 target_temp 向 default_temp 方向回温
                    diff_to_default = room.default_temp - current_temp
                    
                    if abs(diff_to_default) < 0.1:
                        # 已经到达 default_temp（环境温度），停止回温
                        new_temp = room.default_temp
                        # 如果房间在服务队列中，恢复服务；如果在等待队列中，保持等待状态
                        if is_serving:
                            room.cooling_paused = False
                            room.pause_start_temp = None
                            self._resume_cooling(room)
                        else:
                            # 等待队列中的房间到达环境温度后，保持暂停状态
                            room.cooling_paused = True
                            room.pause_start_temp = None
                    else:
                        # 向 default_temp 回温（每分钟0.5℃）
                        step = max(min(diff_to_default, max_change), -max_change)
                        new_temp = current_temp + step
                        
                        # 检查是否回温1℃（从暂停时的温度）
                        # 注意：如果房间在等待队列中，回温1℃后不应该自动恢复服务
                        # 只有在服务队列中且回温1℃后才恢复服务
                        if room.pause_start_temp is not None and is_serving:
                            temp_diff = abs(new_temp - room.pause_start_temp)
                            if temp_diff >= 1.0:
                                # 回温1℃，重新加入队列（保持原有参数）
                                room.cooling_paused = False
                                room.pause_start_temp = None
                                self._resume_cooling(room)
            else:
                # 正常制冷/制热逻辑（仅在服务队列中执行）
                if not is_serving:
                    # 如果不在服务队列中，不应该执行制冷/制热逻辑
                    # 这种情况理论上不应该发生，因为上面已经处理了
                    new_temp = current_temp
                else:
                    diff = room.target_temp - current_temp
                    if abs(diff) < 0.1:
                        # 达到目标温度
                        new_temp = room.target_temp
                        
                        # 如果目标温度等于默认温度（环境温度），不需要暂停服务
                        # 因为已经到达环境温度，不会回温，保持服务状态即可
                        if room.default_temp is not None and abs(room.target_temp - room.default_temp) < 0.1:
                            # target_temp == default_temp，保持服务状态，不暂停
                            # 温度已经稳定在环境温度，不需要回温
                            pass
                        else:
                            # target_temp != default_temp，暂停服务，启动回温程序
                            # 回温将从 target_temp 向 default_temp 方向回温
                            room.cooling_paused = True
                            room.pause_start_temp = new_temp  # 记录暂停时的温度（即 target_temp）
                            # 从服务队列移除，但保持ac_on状态
                            self._pause_cooling(room)
                    else:
                        # 根据时间间隔和变化速度计算应该变化的温度
                        max_change = change_rate * elapsed_minutes
                        step = max(min(diff, max_change), -max_change)
                        new_temp = current_temp + step
        else:
            # 空调关闭时，温度每分钟回温0.5℃，直至回到房间的默认温度
            if room.default_temp is None:
                return
            diff = room.default_temp - current_temp
            if abs(diff) < 0.1:
                room.cooling_paused = False
                room.pause_start_temp = None
                new_temp = room.default_temp
            else:
                rewarming_rate = 0.5  # 0.5℃ / 分钟
                max_change = rewarming_rate * elapsed_minutes
                step = max(min(diff, max_change), -max_change)
                new_temp = current_temp + step
        
        if abs(new_temp - current_temp) >= 1e-6:
            room.current_temp = round(new_temp, 2)
            room.last_temp_update = now
            self.room_service.updateRoom(room)

    def RequestState(self, RoomId: int) -> dict:
        room_id = RoomId
        # 先从数据库恢复队列状态（如果服务重启后队列丢失）
        self._restore_queue_from_database()
        # 在获取状态前，确保队列状态正确
        self._enforce_capacity()
        
        room = self.room_service.getRoomById(room_id)
        if room is None:
            raise ValueError("房间不存在")
        
        # 自动更新当前温度
        self._updateRoomTemperature(room)
        # 刷新room对象以获取最新状态
        room = self.room_service.getRoomById(room_id)
        
        status = room.to_dict()
        now = datetime.utcnow()
        queue_state = "IDLE"
        waiting_seconds = 0.0
        serving_seconds = 0.0
        queue_position = None
        
        # 如果房间处于暂停状态，显示为PAUSED
        if room.cooling_paused:
            queue_state = "PAUSED"
        else:
            for req in self.serving_queue:
                if req.roomId == room_id:
                    queue_state = "SERVING"
                    serving_seconds = self._elapsed_seconds(req.servingTime, now)
                    break
            else:
                for idx, req in enumerate(self.waiting_queue):
                    if req.roomId == room_id:
                        queue_state = "WAITING"
                        waiting_seconds = self._elapsed_seconds(req.waitingTime, now)
                        queue_position = idx + 1
                        break
        status.update(
            {
                "queueState": queue_state,
                "waitingSeconds": waiting_seconds,
                "servingSeconds": serving_seconds,
                "queuePosition": queue_position,
            }
        )
        return status

    def _restore_queue_from_database(self) -> None:
        """从数据库恢复队列状态，用于服务重启后恢复队列"""
        # 先清理重复的房间
        self._deduplicate_queues()
        
        # 获取所有正在使用空调的房间ID
        ac_on_room_ids = {room.id for room in Room.query.filter_by(ac_on=True).all()}
        now = datetime.utcnow()
        
        # 清理队列中已关闭空调的房间
        self.serving_queue = [req for req in self.serving_queue if req.roomId in ac_on_room_ids]
        self.waiting_queue = [req for req in self.waiting_queue if req.roomId in ac_on_room_ids]
        
        # 获取当前队列中已有的房间ID
        existing_room_ids = set()
        for req in self.serving_queue:
            existing_room_ids.add(req.roomId)
        for req in self.waiting_queue:
            existing_room_ids.add(req.roomId)
        
        # 对于每个ac_on=True的房间，如果不在队列中，则恢复
        for room_id in ac_on_room_ids:
            if room_id in existing_room_ids:
                continue  # 已经在队列中，跳过
            
            room = self.room_service.getRoomById(room_id)
            if not room:
                continue
            
            # 如果房间处于暂停状态（cooling_paused=True），不恢复队列
            if room.cooling_paused:
                continue
            
            # 创建RoomRequest
            request = RoomRequest(
                roomId=room.id,
                fanSpeed=room.fan_speed or "MEDIUM",
                mode=room.ac_mode or "COOLING",
                targetTemp=room.target_temp,
            )
            
            # 根据房间的serving_start_time和waiting_start_time判断应该加入哪个队列
            if room.serving_start_time:
                # 如果房间有serving_start_time，说明应该在服务队列
                request.servingTime = room.serving_start_time
                self.serving_queue.append(request)
            elif room.waiting_start_time:
                # 如果房间有waiting_start_time，说明应该在等待队列
                request.waitingTime = room.waiting_start_time
                self.waiting_queue.append(request)
            else:
                # 如果都没有，根据当前容量决定
                capacity = self._capacity()
                if len(self.serving_queue) < capacity:
                    request.servingTime = room.ac_session_start or now
                    self.serving_queue.append(request)
                    self._mark_room_serving(room.id, request.servingTime)
                else:
                    request.waitingTime = room.ac_session_start or now
                    self.waiting_queue.append(request)
                    self._mark_room_waiting(room.id, request.waitingTime)
        
        # 恢复后重新排序和平衡队列
        self._sort_waiting_queue()
        self._rebalance_queues()

    def getScheduleStatus(self) -> dict:
        # 先从数据库恢复队列状态（如果服务重启后队列丢失）
        self._restore_queue_from_database()
        # 清理重复的房间
        self._deduplicate_queues()
        # 执行时间片检查和温度更新
        self._rebalance_queues()
        # 更新所有房间的温度
        rooms = self.room_service.getAllRooms()
        for room in rooms:
            self._updateRoomTemperature(room)
        # 在返回状态前，强制限制服务队列不超过容量
        self._enforce_capacity()
        now = datetime.utcnow()

        def _to_payload(queue: List[RoomRequest]) -> List[Dict[str, object]]:
            payload = []
            for req in queue:
                payload.append(
                    {
                        "roomId": req.roomId,
                        "fanSpeed": req.fanSpeed,
                        "mode": req.mode,
                        "targetTemp": req.targetTemp,
                        "waitingSeconds": self._elapsed_seconds(req.waitingTime, now),
                        "servingSeconds": self._elapsed_seconds(req.servingTime, now),
                    }
                )
            return payload

        return {
            "capacity": self._capacity(),
            "timeSlice": self._time_slice(),
            "servingQueue": _to_payload(self.serving_queue),
            "waitingQueue": _to_payload(self.waiting_queue),
        }

    def forceTimeSliceCheck(self) -> dict:
        self._rebalance_queues(force_rotation=True)
        return self.getScheduleStatus()

    def simulateTemperatureUpdate(self) -> dict:
        """批量更新所有房间的温度，使用与_updateRoomTemperature相同的逻辑"""
        now = datetime.utcnow()
        rooms = self.room_service.getAllRooms()
        updated = 0
        for room in rooms:
            # 使用相同的温度更新逻辑
            old_temp = room.current_temp
            self._updateRoomTemperature(room)
            # 刷新room对象以获取最新温度
            room = self.room_service.getRoomById(room.id)
            if room and abs((room.current_temp or 0) - (old_temp or 0)) >= 1e-6:
                updated += 1
        return {"message": "温度已模拟更新", "updatedRooms": updated}

    def getServingQueue(self) -> List[RoomRequest]:
        return list(self.serving_queue)

    def getWaitingQueue(self) -> List[RoomRequest]:
        return list(self.waiting_queue)

