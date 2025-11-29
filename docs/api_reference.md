# 酒店管理系统接口文档

本文档列出了系统中所有对外暴露的接口。

---

## REST API 接口

### 1. 空调调度接口 (`/ac`)

#### 1.1 获取空调状态
- **路径**: `GET /ac/state`
- **参数**: `roomId` (查询参数, int, 必需)
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

#### 1.2 开启空调
- **路径**: `POST /ac/power`
- **参数** (JSON Body): `{ "roomId": int }`
- **返回**: `{ "message": "空调已开启并进入调度" }`

#### 1.3 关闭空调
- **路径**: `POST /ac/power/off`
- **参数** (JSON Body): `{ "roomId": int }`
- **返回**: `{ "message": "空调已关闭" }`

#### 1.4 调整目标温度
- **路径**: `POST /ac/temp`
- **参数** (JSON Body): `{ "roomId": int, "targetTemp": float }`
- **返回**: `{ "message": "目标温度已更新" }`

#### 1.5 调整风速
- **路径**: `POST /ac/speed`
- **参数** (JSON Body): `{ "roomId": int, "fanSpeed": string }` (风速: "LOW" | "MEDIUM" | "HIGH")
- **返回**: `{ "message": "风速已更新" }`

#### 1.6 调整模式
- **路径**: `POST /ac/mode`
- **参数** (JSON Body): `{ "roomId": int, "mode": string }` (模式: "COOLING" | "HEATING")
- **返回**: `{ "message": "模式已更新" }`

---

### 2. 管理员维护接口 (`/admin`)

#### 2.1 获取所有房间状态
- **路径**: `GET /admin/rooms/status`
- **参数**: 无
- **返回**: 房间状态对象数组

#### 2.2 控制空调开关
- **路径**: `POST /admin/control/power`
- **参数** (JSON Body): `{ "roomId": int, "action": string }` (action: "on" | "off")
- **返回**: `{ "message": string }`

#### 2.3 控制温度
- **路径**: `POST /admin/control/temp`
- **参数** (JSON Body): `{ "roomId": int, "targetTemp": float }`
- **返回**: `{ "message": string }`

#### 2.4 控制风速
- **路径**: `POST /admin/control/speed`
- **参数** (JSON Body): `{ "roomId": int, "fanSpeed": string }`
- **返回**: `{ "message": string }`

#### 2.5 控制模式
- **路径**: `POST /admin/control/mode`
- **参数** (JSON Body): `{ "roomId": int, "mode": string }`
- **返回**: `{ "message": string }`

#### 2.6 重置数据库
- **路径**: `POST /admin/reset-database`
- **参数**: 无
- **返回**: `{ "message": "数据库已重置并重新初始化" }`

---

### 3. 账单管理接口 (`/bill`)

#### 3.1 导出账单详单（CSV）
- **路径**: `GET /bill/export/csv`
- **参数**: `roomId` (查询参数, int, 可选)
- **返回**: CSV 文件下载

---

### 4. 酒店前台接口 (`/hotel`)

#### 4.1 获取所有房间
- **路径**: `GET /hotel/rooms`
- **参数**: 无
- **返回**: 房间对象数组（每个房间包含 id, status, currentTemp, targetTemp, acOn, acMode, fanSpeed, defaultTemp 等字段）

#### 4.2 获取可用房间ID列表
- **路径**: `GET /hotel/available`
- **参数**: 无
- **返回**: `[1, 2, 3, 5]` (可用房间ID数组)

#### 4.3 获取可用房间详情列表
- **路径**: `GET /hotel/rooms/available`
- **参数**: 无
- **返回**: 可用房间对象数组（每个房间包含完整房间信息）

#### 4.4 办理入住
- **路径**: `POST /hotel/checkin`
- **参数** (JSON Body): 
```json
{
  "roomId": 1,
  "name": "张三",
  "idCard": "110101199001011234",
  "phoneNumber": "13800138000"
}
```
- **返回**: `{ "message": "入住成功" }`
- **错误**: `{ "error": "错误信息" }` (400状态码)

#### 4.5 办理退房
- **路径**: `POST /hotel/checkout/<roomId>`
- **参数**: `roomId` (路径参数, int)
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
      "roomId": 1,
      "startTime": "2024-01-01T10:00:00",
      "endTime": "2024-01-01T12:00:00",
      "duration": 120,
      "fanSpeed": "MEDIUM",
      "currentFee": 60.0,
      "fee": 60.0
    }
  ],
  "bill": {
    "roomId": 1,
    "checkinTime": "2024-01-01",
    "checkoutTime": "2024-01-02",
    "duration": "1",
    "roomFee": 100.0,
    "acFee": 60.0
  }
}
```
- **错误**: `{ "error": "错误信息" }` (400状态码)

---

### 5. 运行监控接口 (`/monitor`)

#### 5.1 获取调度队列状态
- **路径**: `GET /monitor/status`
- **参数**: 无
- **返回**: 
```json
{
  "capacity": 3,
  "timeSlice": 120,
  "servingQueue": [ ... ],
  "waitingQueue": [ ... ]
}
```

---

### 6. 经营报表接口 (`/report`)

#### 6.1 获取房间报表
- **路径**: `GET /report/room`
- **参数**: `roomId` (查询参数, int, 可选)
- **返回**: 房间报表数据

#### 6.2 获取日报表
- **路径**: `GET /report/daily`
- **参数**: `date` (查询参数, string, 可选) - 日期格式: YYYY-MM-DD
- **返回**: 日报表数据

#### 6.3 获取周报表
- **路径**: `GET /report/weekly`
- **参数**: `startDate` (查询参数, string, 可选) - 开始日期格式: YYYY-MM-DD
- **返回**: 周报表数据

---

### 7. 测试调试接口 (`/test`)

#### 7.1 初始化房间状态
- **路径**: `POST /test/initRoom`
- **参数** (JSON Body): `{ "roomId": int, "temperature": float, "dailyRate": float }`
- **返回**: 
```json
{
  "message": "Room {roomId} reset",
  "temp": 25.0,
  "rate": 100.0
}
```

---

## 前端页面路由

以下路由返回 HTML 页面：

- `GET /` - 首页
- `GET /customer` - 客户界面
- `GET /reception` - 前台界面
- `GET /reception/checkin` - 入住办理页面
- `GET /reception/checkout` - 退房办理页面
- `GET /manager` - 经理界面
- `GET /manager/report` - 经理报表页面

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


