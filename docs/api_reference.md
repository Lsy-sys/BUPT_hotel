# 酒店管理系统接口文档

本文档列出了系统中所有对外暴露的接口，包括 REST API 和核心业务对象接口。

---

## 目录

- [REST API 接口](#rest-api-接口)
  - [空调调度接口](#1-空调调度接口-apiaac)
  - [管理员维护接口](#2-管理员维护接口-apiadmin)
  - [账单管理接口](#3-账单管理接口-apibills)
  - [酒店前台接口](#4-酒店前台接口-apihotel)
  - [运行监控接口](#5-运行监控接口-apimonitor)
  - [经营报表接口](#6-经营报表接口-apireports)
  - [测试调试接口](#7-测试调试接口-apitest)
- [核心业务对象接口](#核心业务对象接口)
  - [Scheduler（调度器）](#scheduler调度器)
  - [AC（空调对象）](#ac空调对象)
  - [FrontDesk（前台对象）](#frontdesk前台对象)
  - [账单与费用计算](#账单与费用计算)
  - [Room（房间对象）](#room房间对象)

---

## REST API 接口

### 1. 空调调度接口 (`/api/ac`)

#### 1.1 开启空调
- **路径**: `POST /api/ac/room/<roomId>/start`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
  - `currentTemp` (查询参数, float, 可选): 当前房间温度
- **返回**: 
  ```json
  {
    "message": "空调已开启并进入调度"
  }
  ```
- **错误**: 400 - 房间不存在或空调已开启

#### 1.2 关闭空调
- **路径**: `POST /api/ac/room/<roomId>/stop`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
- **返回**: 
  ```json
  {
    "message": "空调已关闭"
  }
  ```
- **错误**: 400 - 房间不存在或空调尚未开启

#### 1.3 调整目标温度
- **路径**: `PUT /api/ac/room/<roomId>/temp`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
  - `targetTemp` (查询参数, float, 必需): 目标温度
- **返回**: 
  ```json
  {
    "message": "目标温度已更新"
  }
  ```
- **错误**: 400 - 房间不存在、空调未开启或参数缺失

#### 1.4 调整风速
- **路径**: `PUT /api/ac/room/<roomId>/speed`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
  - `fanSpeed` (查询参数, string, 必需): 风速 ("LOW" | "MEDIUM" | "HIGH")
- **返回**: 
  ```json
  {
    "message": "风速已更新"
  }
  ```
- **错误**: 400 - 房间不存在、空调未开启、无效风速或参数缺失

#### 1.5 获取房间空调累计数据
- **路径**: `GET /api/ac/room/<roomId>/detail`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
- **返回**: 
  ```json
  {
    "totalDuration": 120,
    "totalCost": 15.5
  }
  ```
- **错误**: 400 - 房间不存在

#### 1.6 查询房间空调状态
- **路径**: `GET /api/ac/room/<roomId>/status`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
- **返回**: 
  ```json
  {
    "id": 1,
    "status": "OCCUPIED",
    "currentTemp": 25.0,
    "targetTemp": 24.0,
    "acOn": true,
    "acMode": "COOLING",
    "fanSpeed": "MEDIUM",
    "defaultTemp": 25.0,
    "queueState": "SERVING",
    "waitingSeconds": 0.0,
    "servingSeconds": 120.5,
    "queuePosition": null
  }
  ```
- **错误**: 400 - 房间不存在

#### 1.7 获取调度队列状态
- **路径**: `GET /api/ac/schedule/status`
- **参数**: 无
- **返回**: 
  ```json
  {
    "capacity": 3,
    "timeSlice": 120,
    "servingQueue": [
      {
        "roomId": 1,
        "fanSpeed": "HIGH",
        "mode": "COOLING",
        "targetTemp": 24.0,
        "waitingSeconds": 0.0,
        "servingSeconds": 60.5
      }
    ],
    "waitingQueue": [
      {
        "roomId": 2,
        "fanSpeed": "LOW",
        "mode": "COOLING",
        "targetTemp": 25.0,
        "waitingSeconds": 30.0,
        "servingSeconds": 0.0
      }
    ]
  }
  ```

---

### 2. 管理员维护接口 (`/api/admin`)

#### 2.1 标记房间为维修状态
- **路径**: `POST /api/admin/rooms/<roomId>/offline`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
- **返回**: 
  ```json
  {
    "message": "房间已标记为维修",
    "room": { ... }
  }
  ```
- **错误**: 400 - 房间不存在或状态错误

#### 2.2 恢复房间为可用状态
- **路径**: `POST /api/admin/rooms/<roomId>/online`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
- **返回**: 
  ```json
  {
    "message": "房间已重新可用",
    "room": { ... }
  }
  ```
- **错误**: 400 - 房间不存在或状态错误

#### 2.3 强制调度队列轮转
- **路径**: `POST /api/admin/maintenance/force-rotation`
- **参数**: 无
- **返回**: 
  ```json
  {
    "message": "调度队列已强制轮转",
    "schedule": { ... }
  }
  ```

#### 2.4 模拟温度更新
- **路径**: `POST /api/admin/maintenance/simulate-temperature`
- **参数**: 无
- **返回**: 
  ```json
  {
    "message": "温度已模拟更新",
    "updatedRooms": 5
  }
  ```

---

### 3. 账单管理接口 (`/api/bills`)

#### 3.1 获取所有账单列表
- **路径**: `GET /api/bills`
- **参数**: 无
- **返回**: 
  ```json
  [
    {
      "id": 1,
      "roomId": 101,
      "customerId": 1,
      "checkInTime": "2025-01-20T10:00:00",
      "checkOutTime": "2025-01-22T14:00:00",
      "stayDays": 2,
      "roomFee": 200.0,
      "acFee": 45.5,
      "totalAmount": 245.5,
      "status": "PAID",
      ...
    }
  ]
  ```

#### 3.2 获取指定账单详情
- **路径**: `GET /api/bills/<billId>`
- **参数**:
  - `billId` (路径参数, int): 账单ID
- **返回**: 账单对象（同 3.1）
- **错误**: 404 - 账单不存在

#### 3.3 获取客户的所有账单
- **路径**: `GET /api/bills/customer/<customerId>`
- **参数**:
  - `customerId` (路径参数, int): 客户ID
- **返回**: 账单列表（同 3.1）

#### 3.4 获取房间的所有账单（按房间号）
- **路径**: `GET /api/bills/room/<roomNumber>`
- **参数**:
  - `roomNumber` (路径参数, int): 房间号
- **返回**: 账单列表（同 3.1）

#### 3.5 获取房间的所有账单（按房间ID）
- **路径**: `GET /api/bills/room-id/<roomId>`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
- **返回**: 账单列表（同 3.1）

#### 3.6 获取未支付账单列表
- **路径**: `GET /api/bills/unpaid`
- **参数**: 无
- **返回**: 账单列表（同 3.1）

#### 3.7 支付账单
- **路径**: `POST /api/bills/<billId>/pay`
- **参数**:
  - `billId` (路径参数, int): 账单ID
- **返回**: 
  ```json
  {
    "message": "账单已支付",
    "bill": { ... }
  }
  ```
- **错误**: 400 - 账单不存在、已取消或已支付

#### 3.8 取消账单
- **路径**: `POST /api/bills/<billId>/cancel`
- **参数**:
  - `billId` (路径参数, int): 账单ID
- **返回**: 
  ```json
  {
    "message": "账单已取消",
    "bill": { ... }
  }
  ```
- **错误**: 400 - 账单不存在或已支付

#### 3.9 获取账单详单列表
- **路径**: `GET /api/bills/<billId>/details`
- **参数**:
  - `billId` (路径参数, int): 账单ID
- **返回**: 
  ```json
  [
    {
      "id": 1,
      "roomId": 101,
      "customerId": 1,
      "acMode": "COOLING",
      "fanSpeed": "MEDIUM",
      "requestTime": "2025-01-20T10:00:00",
      "startTime": "2025-01-20T10:00:00",
      "endTime": "2025-01-20T12:00:00",
      "duration": 120,
      "cost": 15.5,
      "rate": 0.13,
      "detailType": "AC"
    }
  ]
  ```
- **错误**: 404 - 账单不存在

#### 3.10 打印账单
- **路径**: `POST /api/bills/<billId>/print`
- **参数**:
  - `billId` (路径参数, int): 账单ID
- **返回**: 
  ```json
  {
    "bill": { ... },
    "detailItems": [ ... ],
    "totals": {
      "acDurationMinutes": 240,
      "acFee": 31.0,
      "roomFee": 200.0,
      "grandTotal": 231.0
    }
  }
  ```
- **错误**: 404 - 账单不存在

#### 3.11 导出账单详单（CSV）
- **路径**: `GET /api/bills/<billId>/export-details`
- **参数**:
  - `billId` (路径参数, int): 账单ID
- **返回**: CSV 文件下载
- **错误**: 404 - 账单不存在

---

### 4. 酒店前台接口 (`/api/hotel`)

#### 4.1 获取可用房间ID列表
- **路径**: `GET /api/hotel/available`
- **参数**: 无
- **返回**: 
  ```json
  [1, 2, 3, 5, 7]
  ```

#### 4.2 获取可用房间详情列表
- **路径**: `GET /api/hotel/rooms/available`
- **参数**: 无
- **返回**: 
  ```json
  [
    {
      "id": 1,
      "status": "AVAILABLE",
      "currentTemp": 32.0,
      "targetTemp": 25.0,
      "acOn": false,
      "acMode": "COOLING",
      "fanSpeed": "LOW",
      "defaultTemp": 25.0
    }
  ]
  ```

#### 4.3 办理入住
- **路径**: `POST /api/hotel/checkin`
- **参数** (JSON Body):
  ```json
  {
    "roomId": 101,
    "name": "张三",
    "idCard": "110101199001011234",
    "phoneNumber": "13800138000"
  }
  ```
- **返回**: 
  ```json
  {
    "message": "入住成功"
  }
  ```
- **错误**: 400 - 参数缺失、房间不存在、房间不可用或客户信息错误

#### 4.4 办理退房
- **路径**: `POST /api/hotel/checkout/<roomId>`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
- **返回**: 
  ```json
  {
    "customer": {
      "name": "张三",
      "idCard": "110101199001011234",
      "phoneNumber": "13800138000"
    },
    "detailBill": [
      {
        "roomId": 101,
        "startTime": "2025-01-20T10:00:00",
        "endTime": "2025-01-20T12:00:00",
        "duration": 120,
        "fanSpeed": "MEDIUM",
        "currentFee": 15.5,
        "fee": 15.5
      }
    ],
    "bill": {
      "roomId": 101,
      "checkinTime": "2025-01-20",
      "checkoutTime": "2025-01-22",
      "duration": "2",
      "roomFee": 200.0,
      "acFee": 45.5
    }
  }
  ```
- **错误**: 400 - 房间没有入住记录

---

### 5. 运行监控接口 (`/api/monitor`)

#### 5.1 获取所有房间状态
- **路径**: `GET /api/monitor/roomstatus`
- **参数**: 无
- **返回**: 
  ```json
  [
    {
      "roomId": 1,
      "roomStatus": "OCCUPIED",
      "currentTemp": 25.0,
      "defaultTemp": 25.0,
      "targetTemp": 24.0,
      "fanSpeed": "MEDIUM",
      "mode": "COOLING",
      "acOn": true,
      "queueState": "SERVING",
      "customerName": "张三",
      "customerIdCard": "110101199001011234",
      "customerPhone": "13800138000",
      "checkInTime": "2025-01-20T10:00:00Z"
    }
  ]
  ```

#### 5.2 获取调度队列状态
- **路径**: `GET /api/monitor/queuestatus`
- **参数**: 无
- **返回**: 
  ```json
  {
    "servingQueue": [
      {
        "roomId": 1,
        "fanSpeed": "HIGH",
        "servingTime": "2025-01-20T10:00:00",
        "servingSeconds": 120.5
      }
    ],
    "waitingQueue": [
      {
        "roomId": 2,
        "fanSpeed": "LOW",
        "waitingTime": "2025-01-20T10:05:00",
        "waitingSeconds": 30.0
      }
    ]
  }
  ```

---

### 6. 经营报表接口 (`/api/reports`)

#### 6.1 获取经营概览
- **路径**: `GET /api/reports/overview`
- **参数**:
  - `start` (查询参数, string, 可选): 开始日期 (ISO 格式)
  - `end` (查询参数, string, 可选): 结束日期 (ISO 格式)
- **返回**: 
  ```json
  {
    "totalRevenue": 5000.0,
    "totalBills": 20,
    "paidBills": 18,
    "unpaidBills": 2,
    "totalACUsage": 1200,
    "totalACFee": 150.0
  }
  ```

#### 6.2 获取空调使用汇总
- **路径**: `GET /api/reports/ac-usage`
- **参数**:
  - `start` (查询参数, string, 可选): 开始日期 (ISO 格式)
  - `end` (查询参数, string, 可选): 结束日期 (ISO 格式)
- **返回**: 
  ```json
  {
    "totalDuration": 1200,
    "totalCost": 150.0,
    "averageDuration": 60.0,
    "averageCost": 7.5
  }
  ```

#### 6.3 获取每日营收
- **路径**: `GET /api/reports/daily-revenue`
- **参数**:
  - `days` (查询参数, int, 默认 7): 查询天数
- **返回**: 
  ```json
  [
    {
      "date": "2025-01-20",
      "revenue": 500.0,
      "billCount": 5
    }
  ]
  ```
- **错误**: 400 - 天数参数无效

---

### 7. 测试调试接口 (`/api/test`)

#### 7.1 触发时间片检查
- **路径**: `POST /api/test/time-slice-check`
- **参数**: 无
- **返回**: 
  ```json
  {
    "message": "时间片检查已执行",
    "schedule": { ... }
  }
  ```

#### 7.2 触发温度更新
- **路径**: `POST /api/test/temperature-update`
- **参数**: 无
- **返回**: 
  ```json
  {
    "message": "温度已模拟更新",
    "updatedRooms": 5
  }
  ```

#### 7.3 获取所有房间状态
- **路径**: `GET /api/test/rooms/status`
- **参数**: 无
- **返回**: 房间对象列表

#### 7.4 获取指定房间状态
- **路径**: `GET /api/test/rooms/<roomId>/status`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
- **返回**: 房间对象
- **错误**: 404 - 房间不存在

#### 7.5 设置房间温度（测试用）
- **路径**: `POST /api/test/rooms/<roomId>/temperature`
- **参数**:
  - `roomId` (路径参数, int): 房间ID
  - `temperature` (查询参数, float, 必需): 温度值
- **返回**: 
  ```json
  {
    "message": "房间1温度已设置为25.0度"
  }
  ```
- **错误**: 404 - 房间不存在

#### 7.6 重置系统状态
- **路径**: `POST /api/test/reset`
- **参数**: 无
- **返回**: 
  ```json
  {
    "message": "系统状态已重置"
  }
  ```

---

## 核心业务对象接口

### Scheduler（调度器）

**职责**: 接收前端请求，管理 `waitQueue` 和 `serviceQueue`，分发任务给 AC 对象。

#### PowerOn
- **签名**: `PowerOn(RoomId: int, CurrentRoomTemp: float | None) -> str`
- **描述**: 处理开机请求
- **参数**:
  - `RoomId` (int): 房间ID
  - `CurrentRoomTemp` (float | None): 当前房间温度（可选）
- **返回**: 字符串消息（如 "空调已开启并进入调度"）
- **异常**: `ValueError` - 房间不存在或空调已开启

#### PowerOff
- **签名**: `PowerOff(RoomId: int) -> str`
- **描述**: 处理关机请求
- **参数**:
  - `RoomId` (int): 房间ID
- **返回**: 字符串消息（如 "空调已关闭"）
- **异常**: `ValueError` - 房间不存在或空调尚未开启

#### ChangeTemp
- **签名**: `ChangeTemp(RoomId: int, TargetTemp: float) -> str`
- **描述**: 处理调温请求
- **参数**:
  - `RoomId` (int): 房间ID
  - `TargetTemp` (float): 目标温度
- **返回**: 字符串消息（如 "目标温度已更新"）
- **异常**: `ValueError` - 房间不存在或空调未开启

#### ChangeSpeed
- **签名**: `ChangeSpeed(RoomId: int, FanSpeed: str) -> str`
- **描述**: 处理调风速请求
- **参数**:
  - `RoomId` (int): 房间ID
  - `FanSpeed` (str): 风速 ("LOW" | "MEDIUM" | "HIGH")
- **返回**: 字符串消息（如 "风速已更新"）
- **异常**: `ValueError` - 房间不存在、空调未开启或无效风速

#### RequestState
- **签名**: `RequestState(RoomId: int) -> dict`
- **描述**: 查询当前房间空调状态
- **参数**:
  - `RoomId` (int): 房间ID
- **返回**: 
  ```python
  {
    "id": 1,
    "status": "OCCUPIED",
    "currentTemp": 25.0,
    "targetTemp": 24.0,
    "acOn": true,
    "acMode": "COOLING",
    "fanSpeed": "MEDIUM",
    "defaultTemp": 25.0,
    "queueState": "SERVING",
    "waitingSeconds": 0.0,
    "servingSeconds": 120.5,
    "queuePosition": None
  }
  ```
- **异常**: `ValueError` - 房间不存在

#### 其他辅助方法
- `getScheduleStatus() -> dict`: 获取调度队列状态
- `forceTimeSliceCheck() -> dict`: 强制时间片检查
- `simulateTemperatureUpdate() -> dict`: 模拟温度更新
- `getServingQueue() -> List[RoomRequest]`: 获取服务队列
- `getWaitingQueue() -> List[RoomRequest]`: 获取等待队列
- `getRoomACAccumulatedData(room_id: int) -> dict`: 获取房间空调累计数据

---

### AC（空调对象）

**职责**: 执行具体的温控逻辑，维护计时器，生成详单。

#### PowerOn
- **签名**: `PowerOn(RoomId: int, CurrentRoomTemp: float | None) -> str`
- **描述**: 与 Scheduler 接口同名，作为实际执行者
- **参数**: 同 Scheduler.PowerOn
- **返回**: 同 Scheduler.PowerOn

#### PowerOff
- **签名**: `PowerOff(RoomId: int) -> str`
- **描述**: 与 Scheduler 接口同名，作为实际执行者
- **参数**: 同 Scheduler.PowerOff
- **返回**: 同 Scheduler.PowerOff

#### ChangeTemp
- **签名**: `ChangeTemp(RoomId: int, TargetTemp: float) -> str`
- **描述**: 与 Scheduler 接口同名，作为实际执行者
- **参数**: 同 Scheduler.ChangeTemp
- **返回**: 同 Scheduler.ChangeTemp

#### ChangeSpeed
- **签名**: `ChangeSpeed(RoomId: int, FanSpeed: str) -> str`
- **描述**: 与 Scheduler 接口同名，作为实际执行者
- **参数**: 同 Scheduler.ChangeSpeed
- **返回**: 同 Scheduler.ChangeSpeed

#### RequestState
- **签名**: `RequestState(RoomId: int) -> dict`
- **描述**: 与 Scheduler 接口同名，作为实际执行者
- **参数**: 同 Scheduler.RequestState
- **返回**: 同 Scheduler.RequestState

#### 其他方法
- `getACByRoomId(room_id: int) -> Optional[Room]`: 根据房间ID获取空调对象

---

### FrontDesk（前台对象）

**职责**: 处理前台营业员的操作事件，协调房间和订单状态。

#### Check_RoomState
- **签名**: `Check_RoomState(date: datetime | None) -> List[Room]`
- **描述**: 查询指定日期的房间列表及状态
- **参数**:
  - `date` (datetime | None): 查询日期（可选，当前实现未基于日期筛选）
- **返回**: 房间对象列表

#### Regist_CustomerInfo
- **签名**: `Regist_CustomerInfo(Cust_id: str, Cust_name: str, number: str, date: datetime | None = None) -> Customer`
- **描述**: 登记客户基本信息
- **参数**:
  - `Cust_id` (str): 客户证件号
  - `Cust_name` (str): 客户姓名
  - `number` (str): 联系电话
  - `date` (datetime | None, 可选): 登记日期（默认当前时间）
- **返回**: Customer 对象
- **异常**: `ValueError` - 客户姓名、证件号或联系电话为空

#### Create_Accommodation_Order
- **签名**: `Create_Accommodation_Order(Customer_id: int, Room_id: int) -> str`
- **描述**: 创建住宿订单，绑定人与房
- **参数**:
  - `Customer_id` (int): 客户ID
  - `Room_id` (int): 房间ID
- **返回**: 字符串消息（如 "入住成功"）
- **异常**: `ValueError` - 客户不存在、房间不存在或房间不可用

#### Process_CheckOut
- **签名**: `Process_CheckOut(Room_id: int) -> CheckoutResponse`
- **描述**: 触发退房流程，调用账单计算
- **参数**:
  - `Room_id` (int): 房间ID
- **返回**: CheckoutResponse 对象（包含客户信息、详单列表、账单信息）
- **异常**: `ValueError` - 房间没有入住记录

#### 其他方法
- `checkIn(payload: Dict) -> str`: 办理入住（封装 Regist_CustomerInfo 和 Create_Accommodation_Order）
- `checkOut(room_id: int) -> CheckoutResponse`: 办理退房（封装 Process_CheckOut）
- `getAvailableRooms() -> List[Room]`: 获取可用房间列表

---

### 账单与费用计算

#### AccommodationFeeBill.calculate_Accommodation_Fee
- **签名**: `calculate_Accommodation_Fee(days: int, daily_fee: float) -> float`
- **描述**: 计算住宿总费用
- **参数**:
  - `days` (int): 住宿天数
  - `daily_fee` (float): 每日费用
- **返回**: 总费用（float，保留2位小数）
- **说明**: 静态方法，如果天数 <= 0，返回 0.0

#### ACFeeBill.calculate_AC_Fee
- **签名**: `calculate_AC_Fee(overrides: Optional[List[DetailRecord]] = None) -> float`
- **描述**: 根据详单列表计算空调总费用
- **参数**:
  - `overrides` (Optional[List[DetailRecord]], 可选): 详单记录列表（如果为 None，使用实例的 detail_records）
- **返回**: 总费用（float，保留2位小数）
- **说明**: 实例方法，计算所有详单记录的费用总和

---

### Room（房间对象）

**职责**: 维护房间自身的物理状态和业务状态。

#### updateState
- **签名**: `updateState(state: str) -> None`
- **描述**: 更新房间状态（如 空闲 -> 已入住）
- **参数**:
  - `state` (str): 房间状态（如 "AVAILABLE", "OCCUPIED", "MAINTENANCE"）

#### setAccommodationDays
- **签名**: `setAccommodationDays(days: int) -> None`
- **描述**: 退房时设置实际住宿天数
- **参数**:
  - `days` (int): 住宿天数

#### associateDetailRecords
- **签名**: `associateDetailRecords(records: List[DetailRecord]) -> None`
- **描述**: 关联空调详单记录
- **参数**:
  - `records` (List[DetailRecord]): 详单记录列表

#### associateCustomer
- **签名**: `associateCustomer(customer: Customer) -> None`
- **描述**: 关联入住的客户
- **参数**:
  - `customer` (Customer): 客户对象

#### to_dict
- **签名**: `to_dict() -> dict`
- **描述**: 将房间对象转换为字典格式
- **返回**: 包含房间基本信息的字典

---

## 前端页面路由

以下路由返回 HTML 页面：

- `GET /` - 首页
- `GET /customer` - 客户界面
- `GET /reception` - 前台界面
- `GET /reception/checkin` - 入住办理页面
- `GET /reception/checkout` - 退房办理页面
- `GET /admin` - 管理员界面
- `GET /manager` - 经理界面

---

## 数据模型

### 核心类名定义

| 模块分类 | 标准类名 | 说明 |
| :--- | :--- | :--- |
| **调度核心** | **`Scheduler`** | 系统核心单例，管理空调调度逻辑 |
| **设备实体** | **`AC`** | 空调设备，每个房间一个实例 |
| **前台控制** | **`FrontDesk`** | 处理入住退房 |
| **基础实体** | **`Room`** | 客房 |
| **基础实体** | **`Customer`** | 顾客 |
| **记录实体** | **`DetailRecord`** | 详单（统一使用单数） |
| **订单实体** | **`AccommodationOrder`** | 住宿订单，入住时创建 |
| **账单实体** | **`AccommodationFeeBill`** | 住宿账单，退房时生成 |
| **账单实体** | **`ACFeeBill`** | 空调账单，退房时生成 |
| **支付实体** | **`DepositReceipt`** | 押金收据 |

---

## 注意事项

1. **参数命名规范**: 
   - REST API 使用 camelCase（如 `roomId`, `currentTemp`）
   - 核心业务对象接口使用 PascalCase（如 `RoomId`, `CurrentRoomTemp`）

2. **错误处理**: 
   - REST API 返回 HTTP 状态码 400（客户端错误）或 404（资源不存在）
   - 核心业务对象接口抛出 `ValueError` 异常

3. **时间格式**: 
   - API 返回的时间使用 ISO 8601 格式（如 "2025-01-20T10:00:00"）
   - 部分接口返回的时间带有 'Z' 后缀表示 UTC 时间

4. **队列状态**: 
   - `queueState` 可能的值: "IDLE"（空闲）、"SERVING"（服务中）、"WAITING"（等待中）

5. **房间状态**: 
   - 可能的值: "AVAILABLE"（可用）、"OCCUPIED"（已入住）、"MAINTENANCE"（维修中）

6. **账单状态**: 
   - 可能的值: "UNPAID"（未支付）、"PAID"（已支付）、"CANCELLED"（已取消）

---

**文档版本**: 1.0  
**最后更新**: 2025-01-20