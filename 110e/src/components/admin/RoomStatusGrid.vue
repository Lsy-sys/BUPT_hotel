<template>
  <div class="rooms-section">
    <h2>所有房间状态</h2>
    <div class="rooms-grid">
      <div
        v-for="room in allRooms"
        :key="room.roomId"
        class="room-card"
        :class="'status-' + room.status"
      >
        <div class="room-card-header">
          <span class="room-number">{{ room.roomId }}</span>
          <span class="room-status">{{ getStatusText(room.status) }}</span>
        </div>
        <div v-if="room.isOn" class="room-card-body">
          <div class="temp-info">
            <div class="current">
              {{ room.currentTemp.toFixed(1) }}°C
            </div>
            <div class="arrow">
              →
            </div>
            <div class="target">
              {{ room.targetTemp }}°C
            </div>
          </div>
          <div class="room-meta">
            <span>{{ getModeText(room.mode) }}</span>
            <span>{{ getFanSpeedText(room.fanSpeed) }}</span>
          </div>
          <div class="room-cost">
            <span>¥{{ room.totalCost.toFixed(2) }}</span>
          </div>
        </div>
        <div v-else class="room-card-body off">
          <p>空调已关机</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RoomState } from '../../types/index';
import { ACMode, FanSpeed, RoomStatus } from '../../types/index';

const props = defineProps<{
  allRooms: RoomState[];
}>();

const getStatusText = (status: RoomStatus): string => {
  const statusMap = {
    [RoomStatus.OFF]: '关机',
    [RoomStatus.STANDBY]: '待机',
    [RoomStatus.SERVING]: '送风中',
    [RoomStatus.WAITING]: '等待中',
    [RoomStatus.TARGET_REACHED]: '已达目标'
  };
  return statusMap[status] || '未知';
};

const getModeText = (mode: ACMode): string => {
  return mode === ACMode.COOLING ? '制冷' : '制热';
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
.rooms-section {
  margin-bottom: 24px;
  background: white;
  padding: 20px 24px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

h2 {
  margin: 0 0 16px 0;
  color: #111827;
  font-size: 16px;
  font-weight: 600;
}

.rooms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
}

.room-card {
  padding: 15px;
  border-radius: 8px;
  background: #f9fafb;
  border: 2px solid #e5e7eb;
  transition: all 0.3s;
}

.room-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.room-card.status-SERVING {
  border-color: #4ade80;
  background: #ecfdf5;
}

.room-card.status-WAITING {
  border-color: #fbbf24;
  background: #fef3c7;
}

.room-card.status-TARGET_REACHED {
  border-color: #60a5fa;
  background: #eff6ff;
}

.room-card.status-STANDBY {
  border-color: #94a3b8;
  background: #f8fafc;
}

.room-card.status-OFF {
  border-color: #cbd5e1;
  background: #f1f5f9;
}

.room-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e5e7eb;
}

.room-number {
  font-weight: bold;
  font-size: 16px;
  color: #333;
}

.room-status {
  font-size: 12px;
  color: #666;
}

.room-card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.room-card-body.off {
  text-align: center;
  color: #999;
  padding: 20px 0;
}

.temp-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 20px;
  font-weight: bold;
  color: #333;
}

.temp-info .arrow {
  font-size: 14px;
  color: #999;
}

.temp-info .target {
  color: #667eea;
}

.room-meta {
  display: flex;
  justify-content: space-around;
  font-size: 12px;
  color: #666;
}

.room-cost {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  font-weight: bold;
  color: #333;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
}
</style>

