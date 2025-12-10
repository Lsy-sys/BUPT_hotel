<template>
  <div class="checkout-section">
    <h2>退房结账</h2>
    <div class="room-select">
      <label>选择房间：</label>
      <select v-model="selectedRoomId" @change="handleRoomChange">
        <option value="">
          请选择已入住的房间号
        </option>
        <option v-for="roomId in occupiedRooms" :key="roomId" :value="roomId">
          房间 {{ roomId }}
        </option>
      </select>
      <button :disabled="!selectedRoomId" class="btn-checkout" @click="handleCheckout">
        退房结账
      </button>
    </div>

    <!-- 房间当前状态 -->
    <div v-if="currentRoom" class="room-current-info">
      <h3>当前使用情况</h3>

      <!-- 客户信息 -->
      <div v-if="currentCheckInRecord" class="guest-info-section">
        <div class="info-grid guest-info">
          <div v-if="currentCheckInRecord.guestName" class="info-item">
            <span class="label">客户姓名：</span>
            <span class="value">{{ currentCheckInRecord.guestName }}</span>
          </div>
          <div v-if="currentCheckInRecord.guestPhone" class="info-item">
            <span class="label">联系电话：</span>
            <span class="value">{{ currentCheckInRecord.guestPhone }}</span>
          </div>
          <div class="info-item">
            <span class="label">入住时间：</span>
            <span class="value">{{ formatDateTime(currentCheckInRecord.checkInTime) }}</span>
          </div>
          <div class="info-item">
            <span class="label">空调模式：</span>
            <span class="value">{{ getModeText(currentCheckInRecord.mode) }}</span>
          </div>
        </div>
      </div>

      <!-- 空调使用情况 -->
      <div class="info-grid">
        <div class="info-item">
          <span class="label">空调状态：</span>
          <span class="value">{{ currentRoom.isOn ? '开机' : '关机' }}</span>
        </div>
        <div class="info-item">
          <span class="label">工作模式：</span>
          <span class="value">{{ getModeText(currentRoom.mode) }}</span>
        </div>
        <div class="info-item">
          <span class="label">当前温度：</span>
          <span class="value">{{ currentRoom.currentTemp.toFixed(1) }}°C</span>
        </div>
        <div class="info-item">
          <span class="label">目标温度：</span>
          <span class="value">{{ currentRoom.targetTemp }}°C</span>
        </div>
        <div class="info-item">
          <span class="label">当前费用：</span>
          <span class="value highlight">¥{{ currentRoom.totalCost.toFixed(2) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { RoomState, CheckInRecord } from '../../types/index';
import { ACMode } from '../../types/index';

const props = defineProps<{
  occupiedRooms: string[];
  allRooms: RoomState[];
  checkInRecords: CheckInRecord[];
  onCheckout: (roomId: string) => void;
}>();

const selectedRoomId = ref('');

const currentRoom = computed(() => {
  if (!selectedRoomId.value) return null;
  return props.allRooms.find(r => r.roomId === selectedRoomId.value) || null;
});

const currentCheckInRecord = computed(() => {
  if (!selectedRoomId.value) return null;
  return props.checkInRecords.find(r => r.roomId === selectedRoomId.value) || null;
});

const handleRoomChange = () => {
  // 房间改变时的处理
};

const handleCheckout = () => {
  if (!selectedRoomId.value) return;
  props.onCheckout(selectedRoomId.value);
  selectedRoomId.value = '';
};

const getModeText = (mode: ACMode): string => {
  return mode === ACMode.COOLING ? '制冷' : '制热';
};

const formatDateTime = (timestamp: number): string => {
  return new Date(timestamp).toLocaleString('zh-CN');
};
</script>

<style scoped>
.checkout-section {
  margin-bottom: 24px;
  padding: 24px;
  background: white;
  border-radius: 12px;
  border: 2px solid #f0f4f8;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

h2 {
  margin: 0 0 20px 0;
  color: #1e293b;
  font-size: 18px;
  font-weight: 600;
}

h3 {
  margin: 0 0 16px 0;
  color: #334155;
  font-size: 16px;
  font-weight: 600;
}

.room-select {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 24px;
}

.room-select label {
  font-weight: 600;
  color: #475569;
  font-size: 15px;
}

.room-select select {
  flex: 1;
  max-width: 320px;
  padding: 11px 16px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 15px;
  outline: none;
  background: #f8fafc;
  transition: all 0.2s;
}

.room-select select:focus {
  border-color: #067ef5;
  background: white;
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.1);
}

.btn-checkout {
  padding: 11px 24px;
  background: #067ef5;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(2, 132, 199, 0.2);
}

.btn-checkout:hover:not(:disabled) {
  background: #0369a1;
  transform: translateY(-1px);
}

.btn-checkout:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
  opacity: 0.6;
}

.room-current-info {
  padding: 20px;
  background: #f8fafc;
  border-radius: 12px;
  border: 2px solid #e0f2fe;
}

.guest-info-section {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 2px solid #e5e7eb;
}

.guest-info {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  padding: 16px;
  border-radius: 8px;
  border: 2px solid #bae6fd;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  border: 2px solid #f0f4f8;
  transition: all 0.2s;
}

.info-item:hover {
  border-color: #cbd5e1;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
}

.info-item .label {
  color: #64748b;
  font-weight: 500;
  font-size: 14px;
}

.info-item .value {
  font-weight: 600;
  color: #1e293b;
  font-size: 15px;
}

.info-item .value.highlight {
  color: #067ef5;
  font-size: 18px;
  font-weight: 700;
}
</style>

