#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式温控系统测试脚本
按照时间轴执行房间操作，测试10秒 = 系统1分钟
"""

import time
import requests
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# API基础URL
API_BASE = "http://localhost:8080/api"

# 房间初始配置
ROOM_CONFIG = {
    1: {"default_temp": 32.0, "daily_rate": 100.0, "name": "高温房间"},
    2: {"default_temp": 28.0, "daily_rate": 125.0, "name": "接近目标温度"},
    3: {"default_temp": 30.0, "daily_rate": 150.0, "name": "标准测试环境"},
    4: {"default_temp": 29.0, "daily_rate": 200.0, "name": "高费率房间"},
    5: {"default_temp": 35.0, "daily_rate": 100.0, "name": "极端高温房间"},
}

# 测试用例时间轴（分钟）
TEST_CASES = [
    # 房间1
    {"minute": 0, "room": 1, "action": "start"},  # 系统启动即开机
    {"minute": 1, "room": 1, "action": "temp", "target_temp": 18.0},
    {"minute": 5, "room": 1, "action": "speed", "fan_speed": "HIGH"},
    {"minute": 9, "room": 1, "action": "temp", "target_temp": 22.0},
    {"minute": 14, "room": 1, "action": "stop"},
    {"minute": 18, "room": 1, "action": "start"},  # 默认参数
    {"minute": 24, "room": 1, "action": "stop"},
    
    # 房间2
    {"minute": 1, "room": 2, "action": "start"},  # 与房间1调温同时
    {"minute": 3, "room": 2, "action": "temp", "target_temp": 19.0},
    {"minute": 6, "room": 2, "action": "stop"},
    {"minute": 7, "room": 2, "action": "start"},
    {"minute": 11, "room": 2, "action": "temp", "target_temp": 22.0},
    {"minute": 16, "room": 2, "action": "stop"},
    {"minute": 19, "room": 2, "action": "start"},
    {"minute": 25, "room": 2, "action": "stop"},
    
    # 房间3
    {"minute": 2, "room": 3, "action": "start"},
    {"minute": 14, "room": 3, "action": "temp", "target_temp": 24.0},
    {"minute": 14, "room": 3, "action": "speed", "fan_speed": "LOW"},
    {"minute": 17, "room": 3, "action": "speed", "fan_speed": "HIGH"},
    {"minute": 22, "room": 3, "action": "stop"},
    
    # 房间4
    {"minute": 3, "room": 4, "action": "start"},
    {"minute": 7, "room": 4, "action": "speed", "fan_speed": "HIGH"},
    {"minute": 9, "room": 4, "action": "temp", "target_temp": 18.0},
    {"minute": 9, "room": 4, "action": "speed", "fan_speed": "HIGH"},
    {"minute": 18, "room": 4, "action": "temp", "target_temp": 20.0},
    {"minute": 18, "room": 4, "action": "speed", "fan_speed": "MEDIUM"},
    {"minute": 25, "room": 4, "action": "stop"},
    
    # 房间5
    {"minute": 1, "room": 5, "action": "start"},  # 与房间1调温、房间2开机同时
    {"minute": 4, "room": 5, "action": "temp", "target_temp": 22.0},
    {"minute": 12, "room": 5, "action": "speed", "fan_speed": "LOW"},
    {"minute": 15, "room": 5, "action": "temp", "target_temp": 20.0},
    {"minute": 15, "room": 5, "action": "speed", "fan_speed": "HIGH"},
    {"minute": 20, "room": 5, "action": "temp", "target_temp": 25.0},
    {"minute": 23, "room": 5, "action": "stop"},
]

# 时间转换：测试10秒 = 系统1分钟
TIME_FACTOR = 10  # 10秒 = 1分钟


def init_rooms():
    """初始化房间配置（温度、住宿费）"""
    print("\n=== 初始化房间配置 ===")
    
    for room_id, config in ROOM_CONFIG.items():
        # 同时设置default_temp和current_temp，确保温度不会自动变化
        url = f"{API_BASE}/test/rooms/{room_id}/init-temp"
        params = {"temperature": config["default_temp"]}
        try:
            response = requests.post(url, params=params)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 房间{room_id} ({config['name']}): 温度初始化为{config['default_temp']}℃ (default_temp和current_temp已同步)")
            else:
                print(f"✗ 房间{room_id}: 初始化温度失败 - {response.text}")
        except Exception as e:
            print(f"✗ 房间{room_id}: 初始化温度异常 - {e}")
        
        # 设置房间住宿费（需要通过数据库直接更新，这里先跳过，后续可以通过SQL或API实现）
        # 注意：住宿费设置可能需要通过数据库直接更新，暂时跳过
    
    print("房间配置初始化完成\n")


def get_room_current_temp(room_id: int) -> Optional[float]:
    """获取房间当前温度"""
    try:
        url = f"{API_BASE}/test/rooms/{room_id}/status"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("currentTemp")
    except Exception as e:
        print(f"获取房间{room_id}温度失败: {e}")
    return None


def execute_action(room_id: int, action: str, **kwargs):
    """执行单个操作（线程安全）"""
    try:
        if action == "start":
            # 开机
            url = f"{API_BASE}/ac/room/{room_id}/start"
            # 获取当前温度
            current_temp = get_room_current_temp(room_id)
            params = {}
            if current_temp is not None:
                params["currentTemp"] = current_temp
            
            # 先开机
            response = requests.post(url, params=params)
            if response.status_code != 200:
                return False, f"开机失败: {response.text}"
            
            # 如果指定了目标温度，设置目标温度
            if "target_temp" in kwargs:
                time.sleep(0.5)  # 短暂等待，确保开机完成
                temp_url = f"{API_BASE}/ac/room/{room_id}/temp"
                temp_params = {"targetTemp": kwargs["target_temp"]}
                temp_response = requests.put(temp_url, params=temp_params)
                if temp_response.status_code == 200:
                    return True, f"开机并设置目标温度为{kwargs['target_temp']}℃"
                else:
                    return False, f"设置温度失败: {temp_response.text}"
            else:
                # 默认开机（目标温度25℃，中风）
                return True, "开机（默认参数：25℃，中风）"
        
        elif action == "stop":
            # 关机
            url = f"{API_BASE}/ac/room/{room_id}/stop"
            response = requests.post(url)
            if response.status_code == 200:
                return True, "关机"
            else:
                return False, f"关机失败: {response.text}"
        
        elif action == "temp":
            # 改温度
            if "target_temp" not in kwargs:
                return False, "缺少target_temp参数"
            url = f"{API_BASE}/ac/room/{room_id}/temp"
            params = {"targetTemp": kwargs["target_temp"]}
            response = requests.put(url, params=params)
            if response.status_code == 200:
                return True, f"设置目标温度为{kwargs['target_temp']}℃"
            else:
                return False, f"设置温度失败: {response.text}"
        
        elif action == "speed":
            # 改风速
            if "fan_speed" not in kwargs:
                return False, "缺少fan_speed参数"
            url = f"{API_BASE}/ac/room/{room_id}/speed"
            params = {"fanSpeed": kwargs["fan_speed"]}
            response = requests.put(url, params=params)
            if response.status_code == 200:
                return True, f"设置风速为{kwargs['fan_speed']}"
            else:
                return False, f"设置风速失败: {response.text}"
        
        else:
            return False, f"未知操作: {action}"
    
    except Exception as e:
        return False, f"执行操作异常: {e}"


def get_room_status(room_id: int) -> Optional[Dict]:
    """获取房间状态（用于验证操作是否生效）"""
    try:
        url = f"{API_BASE}/monitor/roomstatus"
        response = requests.get(url)
        if response.status_code == 200:
            rooms = response.json()
            for room in rooms:
                if room.get("roomId") == room_id:
                    return room
    except Exception as e:
        print(f"获取房间{room_id}状态失败: {e}")
    return None


def print_room_status(room_id: int):
    """打印房间当前状态（用于管理员查看）"""
    status = get_room_status(room_id)
    if status:
        ac_on = "开启" if status.get("acOn") else "关闭"
        current_temp = status.get("currentTemp", 0)
        target_temp = status.get("targetTemp", 0)
        fan_speed = status.get("fanSpeed", "N/A")
        queue_state = status.get("queueState", "IDLE")
        print(f"    [状态] 空调:{ac_on} | 当前温度:{current_temp:.1f}℃ | 目标温度:{target_temp}℃ | 风速:{fan_speed} | 队列:{queue_state}")


def run_test():
    """运行测试用例"""
    print("\n" + "="*60)
    print("分布式温控系统测试 - 开始执行")
    print("="*60)
    print(f"时间转换: 测试10秒 = 系统1分钟")
    print(f"总测试时长: {max(tc['minute'] for tc in TEST_CASES)} 分钟")
    print("="*60 + "\n")
    
    # 检查API连接
    try:
        response = requests.get(f"{API_BASE}/monitor/roomstatus", timeout=5)
        if response.status_code != 200:
            print("⚠ 警告: API服务可能未正常运行")
    except Exception as e:
        print(f"✗ 错误: 无法连接到API服务 ({API_BASE})")
        print(f"   请确保Flask服务正在运行")
        return
    
    # 初始化房间
    init_rooms()
    
    # 等待系统稳定
    print("等待系统稳定...")
    time.sleep(2)
    
    # 按时间排序测试用例
    sorted_cases = sorted(TEST_CASES, key=lambda x: x["minute"])
    
    # 按分钟分组，同一分钟的操作需要并发执行
    cases_by_minute = {}
    for case in sorted_cases:
        minute = case["minute"]
        if minute not in cases_by_minute:
            cases_by_minute[minute] = []
        cases_by_minute[minute].append(case)
    
    current_minute = -1  # 从-1开始，因为第0分钟的操作需要立即执行
    
    for target_minute in sorted(cases_by_minute.keys()):
        # 等待到目标时间
        if target_minute > current_minute:
            wait_seconds = (target_minute - current_minute) * TIME_FACTOR
            if wait_seconds > 0:
                print(f"\n[等待 {wait_seconds}秒 (系统{target_minute - current_minute}分钟)]")
                time.sleep(wait_seconds)
            current_minute = target_minute
        
        # 获取该分钟的所有操作
        cases_at_minute = cases_by_minute[target_minute]
        
        if len(cases_at_minute) == 1:
            # 只有一个操作，顺序执行
            case = cases_at_minute[0]
            room_id = case["room"]
            action = case["action"]
            room_name = ROOM_CONFIG[room_id]["name"]
            
            print(f"\n[第{target_minute}分钟] 房间{room_id} ({room_name}): {action}", end="")
            
            # 准备参数
            kwargs = {}
            if "target_temp" in case:
                kwargs["target_temp"] = case["target_temp"]
            if "fan_speed" in case:
                kwargs["fan_speed"] = case["fan_speed"]
            
            # 执行操作
            success, message = execute_action(room_id, action, **kwargs)
            
            if success:
                print(f" ✓ {message}")
                time.sleep(0.3)  # 短暂等待，让系统更新状态
                print_room_status(room_id)
            else:
                print(f" ✗ {message}")
        else:
            # 多个操作，并发执行以确保同时完成
            print(f"\n[第{target_minute}分钟] 并发执行 {len(cases_at_minute)} 个操作:")
            
            def execute_case_with_result(case):
                """执行单个用例并返回结果"""
                room_id = case["room"]
                action = case["action"]
                room_name = ROOM_CONFIG[room_id]["name"]
                
                # 准备参数
                kwargs = {}
                if "target_temp" in case:
                    kwargs["target_temp"] = case["target_temp"]
                if "fan_speed" in case:
                    kwargs["fan_speed"] = case["fan_speed"]
                
                # 执行操作
                success, message = execute_action(room_id, action, **kwargs)
                return {
                    "case": case,
                    "room_id": room_id,
                    "room_name": room_name,
                    "action": action,
                    "success": success,
                    "message": message
                }
            
            # 使用线程池并发执行
            results = []
            with ThreadPoolExecutor(max_workers=len(cases_at_minute)) as executor:
                # 提交所有任务
                future_to_case = {
                    executor.submit(execute_case_with_result, case): case 
                    for case in cases_at_minute
                }
                
                # 收集结果（按完成顺序）
                for future in as_completed(future_to_case):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        case = future_to_case[future]
                        results.append({
                            "case": case,
                            "room_id": case["room"],
                            "room_name": ROOM_CONFIG[case["room"]]["name"],
                            "action": case["action"],
                            "success": False,
                            "message": f"执行异常: {e}"
                        })
            
            # 显示结果（按房间ID排序，便于查看）
            results.sort(key=lambda x: x["room_id"])
            for result in results:
                room_id = result["room_id"]
                room_name = result["room_name"]
                action = result["action"]
                success = result["success"]
                message = result["message"]
                
                print(f"  房间{room_id} ({room_name}): {action}", end="")
                if success:
                    print(f" ✓ {message}")
                else:
                    print(f" ✗ {message}")
            
            # 等待一小段时间，让所有操作完成并更新状态
            time.sleep(0.5)
            
            # 显示所有房间的状态
            for result in results:
                if result["success"]:
                    print_room_status(result["room_id"])
    
    print("\n" + "="*60)
    print("测试执行完成！")
    print("="*60)
    print("\n提示: 可以在管理员界面 (http://localhost:8080/admin) 查看所有房间的实时状态")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        run_test()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试执行出错: {e}")
        import traceback
        traceback.print_exc()

