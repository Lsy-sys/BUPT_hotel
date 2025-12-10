# 🏨 酒店中央温控系统

[![Vue 3](https://img.shields.io/badge/Vue-3.5-brightgreen.svg)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue.svg)](https://www.typescriptlang.org/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.2.0-brightgreen.svg)](https://spring.io/projects/spring-boot)
[![Java](https://img.shields.io/badge/Java-17-orange.svg)](https://www.oracle.com/java/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 项目简介

一个完整的酒店中央空调温控系统，实现了智能管理、实时监控、自动计费和数据统计。采用前后端分离架构，基于优先级调度和时间片轮转算法，提供高效的资源管理和出色的用户体验。

**技术栈**：Vue 3 + TypeScript + Vite + Axios

**当前版本**：v2.1.0 (2024-12-09) - [查看更新日志](docs/CHANGELOG.md)

---

## ✨ 核心功能

### 四大功能模块

#### 🛏️ 客房控制面板

- 温度和风速实时调节
- 实时状态和费用显示
- 自动温控（达标停风、偏离重启）

#### 👨‍💼 管理员监控中心

- 实时监控所有房间状态
- 服务队列和等待队列可视化
- 批量操作（一键开关机、清空队列）

#### 💰 前台结账系统

- 四步式入住流程（选房 → 客户信息 → 空调设置 → 确认支付）
- 自动生成详细账单和详单
- 历史账单查询和导出

#### 📊 经理统计报表

- 多维度数据统计分析
- 多时间范围报表生成
- 风速使用分布和费用统计

### 主要特性

- ⚡ **智能调度** - 优先级调度 + 时间片轮转，公平高效分配资源
- 🌡️ **自动温控** - 实时温度监测，达到目标自动停止，偏离自动重启
- 💵 **精准计费** - 按风速分级计费，详细记录每次操作
- 📡 **实时监控** - 每秒更新，全方位监控系统运行状态
- 🛡️ **防抖控制** - 智能指令合并，避免频繁操作
- 🎨 **自定义弹窗** - 美观的渐变背景 + 毛玻璃效果，替代原生弹窗

---

## 🚀 快速开始

### 环境要求

**后端开发环境：**

- JDK 17+
- Maven 3.8+
- MySQL 9.3.0+

**前端开发环境：**

- Node.js 18+
- npm 9+

### 快速启动

```bash
# 1. 克隆项目
git clone <repository-url>
cd central-temperature-control-system

# 2. 初始化数据库
mysql -u root -p < back-end/src/main/resources/sql/schema.sql

# 3. 配置后端数据库连接
# 编辑 back-end/src/main/resources/application-dev.yml
# 修改 spring.datasource.password 为你的数据库密码

# 4. 启动后端（端口 8080）
cd back-end
mvn spring-boot:run

# 5. 安装前端依赖并启动（端口 5173）
cd ../front-end
npm install
npm run dev

# 6. 访问系统
# 前端：http://localhost:5173
# 后端API：http://localhost:8080/api
```

> **🎯 重要提示**：前端默认使用 **真实后端 API 模式**，所有接口已完整对接。如需切换到本地模拟模式进行前端独立开发，请参考：[📖 API 使用指南](docs/API_GUIDE.md)

详细的启动指南请查看：[📖 快速启动文档](docs/QUICKSTART.md)

---

## 🌐 API 模式说明

### 默认配置

**前端已完全对接真实后端 API**，默认配置：

```typescript
// src/config/index.ts
export const API_MODE: "mock" | "api" = "api"; // ✅ API 模式
export const API_BASE_URL = "/api";
```

### 运行模式

#### API 模式（默认，推荐）✅

- ✅ 使用真实后端数据库
- ✅ 数据持久化
- ✅ 完整的前后端集成测试
- ✅ 18/18 个接口全部对接（部分接口时间格式待修复）
- ✅ 自动刷新（每秒同步）

#### Mock 模式（可选）

- ✅ 前端独立开发，无需后端
- ✅ 响应速度快
- ❌ 数据不持久化

**切换方式**：修改 `src/config/index.ts` 中的 `API_MODE` 配置即可。详见：[API 使用指南](docs/API_GUIDE.md)

---

## 🏗️ 技术架构

### 前端技术栈

```
前端框架：Vue 3 (Composition API)
编程语言：TypeScript
构建工具：Vite
样式方案：原生 CSS (Scoped)
状态管理：响应式数据
API 模式：真实后端 API（默认）/ 本地 Mock（可选）
```

### 后端技术栈

```
框架：Spring Boot 3.2.0
持久化：MyBatis Plus 3.5.5
数据库：MySQL 9.3.0
编程语言：Java 17
```

### 项目结构

```
central-temperature-control-system/
├── front-end/               # 前端项目 (Vue 3 + TypeScript)
│   ├── src/
│   │   ├── components/      # Vue 组件（模块化拆分）
│   │   │   ├── admin/       # 管理员模块组件
│   │   │   ├── frontdesk/   # 前台模块组件
│   │   │   ├── manager/     # 经理模块组件
│   │   │   ├── room/        # 房间控制模块组件
│   │   │   └── common/      # 公共组件（Modal、Message等）
│   │   ├── services/        # 核心业务逻辑
│   │   │   ├── ACService.ts            # 空调服务
│   │   │   ├── Scheduler.ts            # 调度服务
│   │   │   ├── BillingService.ts       # 计费服务
│   │   │   └── CentralController.ts    # 中央控制器
│   │   ├── composables/     # Vue组合式函数
│   │   │   └── useDialog.ts # 自定义弹窗系统
│   │   ├── types/           # TypeScript 类型定义
│   │   └── constants/       # 系统常量配置
│   └── docs/                # 项目文档
│
├── back-end/                # 后端项目 (Spring Boot)
│   ├── src/main/java/com/bupt/hotel/hvac/
│   │   ├── controller/      # 控制器层（4个）
│   │   ├── service/         # 服务层（4个核心服务）
│   │   ├── mapper/          # 数据访问层（4个）
│   │   ├── model/           # 数据模型
│   │   └── common/          # 公共类
│   └── src/main/resources/
│       ├── sql/             # 数据库脚本
│       └── application.yml  # 配置文件
│
└── README.md                # 本文档
```

详细的架构说明请查看：[📖 项目结构文档](docs/PROJECT_STRUCTURE.md)

---

## 💡 核心业务规则

### 调度策略

系统采用**优先级调度 + 时间片调度**混合策略：

- **优先级规则**：高风速 > 中风速 > 低风速，高优先级可抢占低优先级
- **时间片规则**：相同风速等待 120 秒后轮转，服务时长最长的被替换
- **服务限制**：同时最多 5 个房间送风（可配置）

### 温度控制规则

| 风速 | 变化率     | 计费标准     |
| ---- | ---------- | ------------ |
| 高风 | 0.6°C/分钟 | 1 元/分钟    |
| 中风 | 0.5°C/分钟 | 0.5 元/分钟  |
| 低风 | 0.4°C/分钟 | 0.33 元/分钟 |

- **制冷模式**：18-25°C
- **制热模式**：25-30°C
- **自动停止**：达到目标温度
- **自动重启**：温度偏离 1°C

### 防抖机制

- 连续操作间隔 < 1 秒：只发送最后一次指令
- 连续操作间隔 ≥ 1 秒：发送所有指令

---

## 📡 API 接口

### 接口列表

系统提供 **18 个 RESTful API 接口**，分为四大模块：

#### 前台接口 (`/api/frontdesk`)

- `POST /checkin` - 办理入住
- `POST /checkout/{roomId}` - 办理退房
- `GET /occupied-rooms` - 获取已入住房间
- `GET /checkin-records` - 获取入住记录
- `GET /bills` - 获取所有账单
- `GET /bill/{roomId}` - 获取房间账单

#### 房间接口 (`/api/room`)

- `POST /{roomId}/turnon` - 开机
- `POST /{roomId}/turnoff` - 关机
- `POST /{roomId}/request` - 发送温控请求
- `GET /{roomId}/state` - 获取房间状态
- `GET /states` - 获取所有房间状态

#### 管理员接口 (`/api/admin`)

- `GET /service-queue` - 获取服务队列
- `GET /waiting-queue` - 获取等待队列
- `POST /turnoff-all` - 一键关机
- `POST /turnon-all` - 一键开机
- `POST /clear-waiting-queue` - 清空等待队列

#### 经理接口 (`/api/manager`)

- `POST /statistics` - 生成统计报表
- `GET /bills` - 获取历史账单

**Base URL**: `http://localhost:8080/api`

详细接口文档请查看：[📖 API 文档](back-end/API_DOCUMENT.md)

---

## 🎯 功能亮点

### 1. 四步式入住流程

```
步骤1: 选择房间 → 步骤2: 客户信息 → 步骤3: 空调设置 → 步骤4: 确认支付
```

- ✅ 可视化房间卡片展示
- ✅ 完整客户信息采集（姓名、电话、证件、入住天数）
- ✅ 押金与费用明细透明展示
- ✅ 多步骤进度指示器

### 2. 自定义弹窗系统

替代原生 `alert()` 和 `confirm()`，提供：

- 🎨 4 种消息类型（成功/错误/警告/信息）
- 💬 确认对话框（返回 Promise，支持 async/await）
- ✨ 美观的渐变背景 + 毛玻璃效果
- 📱 移动端完美适配

```typescript
// 使用示例
import { showSuccess, showConfirm } from "@/composables/useDialog";

showSuccess("入住办理成功！");

const confirmed = await showConfirm("确认操作", "确定要删除吗？");
if (confirmed) {
  // 执行删除
}
```

### 3. 组件模块化

将大型组件拆分为小型、可复用的子组件：

- `FrontDeskBilling` (1054 行) → **拆分为 5 个子组件** (平均 150 行)
- `RoomClient` (816 行) → **拆分为 6 个子组件** (平均 100 行)
- `ManagerStatistics` (741 行) → **拆分为 5 个子组件** (平均 150 行)
- `AdminMonitor` (668 行) → **拆分为 4 个子组件** (平均 120 行)

**代码减少 70-86%**，可维护性大幅提升。

---

## 🧪 测试场景

### 优先级调度测试

1. 开启 5 个低风速房间（填满服务队列）
2. 新增 1 个高风速房间
3. 观察高风速抢占服务时长最长的低风速房间

### 时间片调度测试

1. 开启 8 个相同风速房间
2. 等待 120 秒观察队列轮转
3. 服务时长最长的房间被等待时长最久的房间替换

### 自动温控测试

1. 设置目标温度并开启空调
2. 观察温度逐渐变化
3. 达到目标温度后自动停止送风
4. 温度偏离 1°C 后自动重启送风

### 防抖机制测试

1. 快速连续调节温度（间隔 < 1 秒）
2. 观察只有最后一次设置生效
3. 间隔 > 1 秒后，每次调节都会生效

---

## 📚 文档导航

### 核心文档（必读）

| 📄 文档 | 📝 说明 | 🎯 适用人群 | ⏱️ 阅读时间 |
|----|---------|------------|-----------|
| [📘 快速启动指南](docs/QUICKSTART.md) | 环境配置、项目启动、功能测试 | 新手必读 | 10分钟 |
| [📗 项目结构文档](docs/PROJECT_STRUCTURE.md) | 代码组织、分层架构、组件详解 | 开发人员 | 20分钟 |
| [📙 API 使用指南](docs/API_GUIDE.md) | 接口对接、调用示例、测试验证 | 前后端对接 | 15分钟 |
| [🏨 入住流程文档](docs/CHECKIN_PROCESS.md) | 四步式入住流程详细说明 | 业务理解 | 15分钟 |
| [🚀 前端优化综合文档](docs/FRONTEND_OPTIMIZATION.md) | 架构优化、性能优化、UI升级 | 开发人员、代码优化 | 30分钟 |
| [📝 更新日志](docs/CHANGELOG.md) | 版本更新记录、新功能说明 | 所有用户 | 10分钟 |

### 参考文档

| 📄 文档 | 目录 | 说明 | 适用场景 |
|----|---------|-----------|  
| [💼 后端文档](../back-end/docs) | 后端API详情、数据库设计 | 后端开发、接口对接 |
| [📊 后端API文档](../back-end/docs/APIFOX_GUIDE.md) | 完整的API接口文档 | API测试、接口调试 |

### 🎉 最新更新 (v2.1.0)

1. **前台入住优化**
   - ✅ 对接真实房间数据API，显示实时价格
   - ✅ 移除房型和价格筛选，简化选房流程

2. **客房控制面板优化**
   - ✅ 温度显示放大至72px，更醒目
   - ✅ 新增"阶段费用"显示（本次开机花费）
   - ✅ 保留"累计费用"显示（总花费）

3. **账单系统优化**
   - ✅ 修复累计费用计算错误（使用后端返回值）
   - ✅ 空调使用费改为"¥1/度（调温计费）"
   - ✅ 详单表格新增操作类型、当前温度、累计费用列
   - ✅ 打印账单优化为纸质打印友好样式

4. **统计报表优化**
   - ✅ 修复时间格式接口错误
   - ✅ 移除总耗电量，新增总服务时长
   - ✅ 修复平均费用/房间计算
   - ✅ 打印报表改进为黑白灰配色

[查看完整更新日志 →](docs/CHANGELOG.md)

### ⚠️ 已知问题

1. **阶段费用计算**
   - 页面刷新后阶段费用会重置
   - 建议后端提供阶段费用字段

2. **未实现的接口**
   - `GET /frontdesk/detail/{roomId}` 在 `hvac.ts` 中定义但后端未提供
   - 解决方案：使用 `BillVO.detailRecords` 获取详单

### 快速导航

**我想...**

| 需求 | 推荐文档 | 章节 |
|------|---------|------|
| 🆕 首次启动项目 | [快速启动指南](docs/QUICKSTART.md) | 全部 |
| 🔧 配置环境 | [快速启动指南](docs/QUICKSTART.md) | 环境要求、项目安装 |
| 📂 了解代码结构 | [项目结构文档](docs/PROJECT_STRUCTURE.md) | 整体结构、分层架构 |
| 🏗️ 理解前端架构 | [项目结构文档](docs/PROJECT_STRUCTURE.md) | 前端架构设计 |
| 🔌 对接API | [API使用指南](docs/API_GUIDE.md) | 接口详情、调用示例 |
| 🏨 了解入住流程 | [入住流程文档](docs/CHECKIN_PROCESS.md) | 四步流程详解 |
| 🚀 了解前端优化 | [前端优化综合文档](docs/FRONTEND_OPTIMIZATION.md) | 架构、性能、UI优化 |
| 🐛 解决问题 | [快速启动指南](docs/QUICKSTART.md) + [API使用指南](docs/API_GUIDE.md) | 常见问题、故障排查 |

---

## 📝 代码统计

### 前端代码

| 模块     | 代码量        | 说明                     |
| -------- | ------------- | ------------------------ |
| 核心服务 | ~1,770 行     | 调度、空调、计费、控制器 |
| Vue 组件 | ~2,850 行     | 4 个功能模块（含 CSS）   |
| 类型配置 | ~190 行       | TypeScript 类型和常量    |
| 主应用   | ~530 行       | App.vue + 入口文件       |
| **总计** | **~6,000+ 行** | 前端完整实现（含模块化组件） |

### 后端代码

| 模块     | 代码量          | 说明                    |
| -------- | --------------- | ----------------------- |
| Java 类  | ~40 个          | 控制器、服务、Mapper 等 |
| API 数   | 18 个           | RESTful API 接口（部分存在兼容问题） |
| 数据表   | 4 张            | MySQL 数据库表          |
| 代码行数 | ~5,000 行       | 后端完整实现            |
| **总计** | **~10,000+ 行** | 前后端完整项目          |

---

## 🎓 项目特色

### 业务逻辑完整

- ✅ 严格按照酒店空调管理需求实现
- ✅ 涵盖入住、使用、退房、统计全流程
- ⚠️ **注意**：统计报表接口存在时间格式不一致问题（前端发送毫秒，后端期望LocalDateTime）

### 算法设计合理

- ✅ 优先级调度 + 时间片轮转，公平高效
- ✅ 自动温控算法，节能环保

### 代码质量优秀

- ✅ 清晰的架构、完善的注释、规范的命名
- ✅ 前后端分离，RESTful API 设计

### 用户体验出色

- ✅ 简洁的界面、流畅的交互、实时的反馈
- ✅ 自定义弹窗系统，美观专业

### 可扩展性强

- ✅ 模块化设计，易于功能扩展
- ✅ 支持后端集成、WebSocket、移动端等

---

## 📦 扩展建议

系统采用模块化设计，易于扩展：

- **实时通信** - 集成 WebSocket，支持多用户实时同步
- **用户认证** - 添加身份验证和权限管理
- **移动端优化** - 响应式适配或开发独立移动应用
- **数据分析** - 更丰富的统计维度和可视化图表
- **性能优化** - 虚拟滚动、懒加载、缓存策略
- **云部署** - 部署到阿里云、腾讯云等云平台

---

## 📄 许可证

MIT License

---

## 🔗 相关链接

- **Vue 3**: https://vuejs.org/
- **TypeScript**: https://www.typescriptlang.org/
- **Spring Boot**: https://spring.io/projects/spring-boot
- **MyBatis Plus**: https://baomidou.com/
- **Vite**: https://vitejs.dev/

---

**如有问题，请参考项目文档或联系开发团队。** 🚀
