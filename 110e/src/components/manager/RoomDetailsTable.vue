<template>
  <div class="room-details-section">
    <h3>房间明细统计</h3>
    <div class="details-table">
      <div class="details-header">
        <span>房间号</span>
        <span>服务次数</span>
        <span>服务时长</span>
        <span>总费用(元)</span>
        <span>平均温度</span>
        <span>常用风速</span>
      </div>
      <div v-for="stat in sortedStats" :key="stat.roomId" class="details-row">
        <span class="room-id">{{ stat.roomId }}</span>
        <span>{{ stat.serviceCount }}</span>
        <span>{{ formatDuration(stat.totalServiceDuration) }}</span>
        <span class="cost">¥{{ stat.totalCost.toFixed(2) }}</span>
        <span>{{ stat.averageTemp.toFixed(1) }}°C</span>
        <span>{{ getFanSpeedText(stat.mostUsedFanSpeed) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { RoomStatistics } from '../../types/index';
import { FanSpeed } from '../../types/index';

const props = defineProps<{
  roomStats: RoomStatistics[];
}>();

const sortedStats = computed(() => {
  return [...props.roomStats].sort((a, b) => b.totalCost - a.totalCost);
});

// 格式化时长
const formatDuration = (seconds: number): string => {
  if (!seconds || seconds === 0) return '0秒';
  if (seconds < 60) return `${seconds}秒`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}时${mins}分`;
};

const getFanSpeedText = (speed: FanSpeed): string => {
  const speedMap = {
    [FanSpeed.LOW]: '低风',
    [FanSpeed.MEDIUM]: '中风',
    [FanSpeed.HIGH]: '高风'
  };
  return speedMap[speed] || '未知';
};
</script>

<style scoped>
.room-details-section {
  padding: 0;
  background: white;
  border-radius: 12px;
  border: 2px solid #e2e8f0;
  margin-bottom: 24px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

h3 {
  margin: 0;
  padding: 20px 24px;
  background: linear-gradient(135deg, #067ef5 0%, #0369a1 100%);
  color: white;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 3px solid #0284c7;
}

.details-table {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.details-header,
.details-row {
  display: grid;
  grid-template-columns: 100px repeat(5, 1fr);
  gap: 10px;
  padding: 16px 24px;
  background: white;
  align-items: center;
  text-align: center;
}

.details-header {
  font-weight: 600;
  background: #f8fafc;
  color: #475569;
  border-bottom: 2px solid #e2e8f0;
  text-transform: uppercase;
  font-size: 13px;
  letter-spacing: 0.5px;
}

.details-row {
  border-bottom: 1px solid #f1f5f9;
  transition: all 0.2s ease;
}

.details-row:last-child {
  border-bottom: none;
}

.details-row:hover {
  background: #f8fafc;
  box-shadow: inset 0 0 0 2px #e0f2fe;
}

.room-id {
  font-weight: 700;
  color: #067ef5;
  font-size: 15px;
}

.cost {
  font-weight: 700;
  color: #059669;
  font-size: 15px;
}
</style>

