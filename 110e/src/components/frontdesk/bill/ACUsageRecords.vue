<template>
  <div class="detail-records">
    <div class="detail-header">
      <h3>📋 空调使用详单</h3>
      <div class="record-summary">
        <span class="record-count">共 {{ records.length }} 条请求记录</span>
        <span class="record-total">累计费用：¥{{ totalCost.toFixed(2) }}</span>
      </div>
    </div>
    <div class="records-table-wrapper">
      <table class="records-table">
        <thead>
          <tr>
            <th>序号</th>
            <th>请求时间</th>
            <th>操作类型</th>
            <th>风速</th>
            <th>目标温度</th>
            <th>当前温度</th>
            <th>服务时长</th>
            <th>当前费用</th>
            <th>累计费用</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(record, index) in records" :key="index" class="table-row">
            <td class="index">
              {{ index + 1 }}
            </td>
            <td class="time">
              {{ formatDateTime(record.timestamp) }}
            </td>
            <td class="action">
              <span :class="['action-badge', getActionClass(record.action)]">
                {{ record.action }}
              </span>
            </td>
            <td class="fan-speed">
              <span v-if="record.fanSpeed" :class="['speed-badge', getFanSpeedClass(record.fanSpeed)]">
                {{ getFanSpeedText(record.fanSpeed) }}
              </span>
              <span v-else class="no-data">-</span>
            </td>
            <td class="temp">
              {{ record.targetTemp ? record.targetTemp.toFixed(1) + '°C' : '-' }}
            </td>
            <td class="temp">
              {{ record.currentTemp.toFixed(1) }}°C
            </td>
            <td class="duration">
              {{ formatDurationSeconds(record.duration) }}
            </td>
            <td class="cost current">
              ¥{{ record.cost.toFixed(2) }}
            </td>
            <td class="cost accumulated">
              ¥{{ getAccumulatedCost(index).toFixed(2) }}
            </td>
          </tr>
          <tr v-if="records.length === 0">
            <td colspan="9" class="empty-records">
              <div class="empty-content">
                <div class="empty-icon">
                  📭
                </div>
                <div class="empty-text">
                  暂无使用记录
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface DetailRecord {
  timestamp: number | string; // 后端可能返回字符串格式 "2025-12-09 01:04:57"
  action: string;
  fanSpeed?: string;
  targetTemp?: number;
  currentTemp: number;
  duration: number;
  cost: number;
  accumulatedCost: number; // 累计费用（后端计算）
}

const props = defineProps<{
  records: DetailRecord[];
}>();

// 获取最终累计费用（使用后端返回的 accumulatedCost）
const totalCost = computed(() => {
  if (props.records.length === 0) return 0;
  // 使用最后一条记录的累计费用
  const lastRecord = props.records[props.records.length - 1];
  return lastRecord?.accumulatedCost ?? 0;
});

// 获取到某条记录为止的累计费用（直接使用后端返回的值）
const getAccumulatedCost = (index: number): number => {
  const record = props.records[index];
  return record?.accumulatedCost ?? 0;
};

// 格式化日期时间（支持字符串和数字格式）
const formatDateTime = (timestamp: number | string): string => {
  // 如果是字符串格式 "2025-12-09 01:04:57"，直接提取 MM-DD HH:MM:SS
  if (typeof timestamp === 'string') {
    const match = timestamp.match(/\d{4}-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
    if (match) {
      return `${match[1]}-${match[2]} ${match[3]}:${match[4]}:${match[5]}`;
    }
    // 尝试解析为 Date
    const date = new Date(timestamp);
    if (!isNaN(date.getTime())) {
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      return `${month}-${day} ${hours}:${minutes}:${seconds}`;
    }
    return timestamp; // 无法解析，直接返回原字符串
  }
  // 数字时间戳
  const date = new Date(timestamp);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  return `${month}-${day} ${hours}:${minutes}:${seconds}`;
};

// 格式化时长（秒）
const formatDurationSeconds = (seconds: number): string => {
  if (seconds === 0) return '0秒';
  return `${seconds}秒`;
};

// 获取风速文本
const getFanSpeedText = (fanSpeed: string): string => {
  const speedMap: Record<string, string> = {
    'LOW': '低风',
    'MEDIUM': '中风',
    'HIGH': '高风'
  };
  return speedMap[fanSpeed] || fanSpeed;
};

// 获取风速样式类
const getFanSpeedClass = (fanSpeed: string): string => {
  const classMap: Record<string, string> = {
    'LOW': 'speed-low',
    'MEDIUM': 'speed-medium',
    'HIGH': 'speed-high'
  };
  return classMap[fanSpeed] || '';
};

// 获取操作类型样式类
const getActionClass = (action: string): string => {
  if (action.includes('开机')) return 'action-on';
  if (action.includes('关机')) return 'action-off';
  if (action.includes('调温') || action.includes('温度')) return 'action-temp';
  if (action.includes('调风') || action.includes('风速')) return 'action-fan';
  if (action.includes('送风')) return 'action-serving';
  return 'action-default';
};
</script>

<style scoped>
.detail-records {
  padding: 20px 24px;
  background: white;
  border-radius: 12px;
  border: 2px solid #e2e8f0;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e2e8f0;
}

.detail-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.record-summary {
  display: flex;
  gap: 20px;
  font-size: 14px;
}

.record-count {
  color: #64748b;
  font-weight: 500;
}

.record-total {
  color: #10b981;
  font-weight: 700;
  font-size: 15px;
}

.records-table-wrapper {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.records-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.records-table thead {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.records-table th {
  padding: 14px 12px;
  text-align: center;
  font-weight: 600;
  color: #475569;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.records-table tbody tr {
  transition: all 0.2s;
}

.records-table tbody tr:hover {
  background: #f8fafc;
}

.records-table tbody tr:not(:last-child) {
  border-bottom: 1px solid #f1f5f9;
}

.records-table td {
  padding: 12px;
  text-align: center;
  color: #1e293b;
}

.index {
  font-weight: 600;
  color: #64748b;
  font-size: 12px;
}

.time {
  font-family: 'Courier New', monospace;
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
}

.action {
  text-align: center;
}

.action-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 12px;
  white-space: nowrap;
}

.action-on {
  background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
  color: #15803d;
  border: 1px solid #86efac;
}

.action-off {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  color: #991b1b;
  border: 1px solid #fca5a5;
}

.action-temp {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1e40af;
  border: 1px solid #93c5fd;
}

.action-fan {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
  border: 1px solid #fbbf24;
}

.action-serving {
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
  color: #4338ca;
  border: 1px solid #a5b4fc;
}

.action-default {
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.fan-speed {
  text-align: center;
}

.speed-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 12px;
}

.speed-low {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #93c5fd;
}

.speed-medium {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fbbf24;
}

.speed-high {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}

.no-data {
  color: #cbd5e1;
  font-weight: 500;
}

.temp {
  color: #1e293b;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

.duration {
  color: #64748b;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

.cost {
  font-weight: 700;
  font-family: 'Courier New', monospace;
}

.cost.current {
  color: #dc2626;
}

.cost.accumulated {
  color: #10b981;
  font-size: 14px;
}

.empty-records {
  padding: 60px 20px;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.5;
}

.empty-text {
  color: #94a3b8;
  font-size: 14px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .records-table {
    font-size: 12px;
  }

  .records-table th,
  .records-table td {
    padding: 10px 8px;
  }
}
</style>
