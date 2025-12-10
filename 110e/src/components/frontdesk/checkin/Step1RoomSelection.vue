<template>
  <div class="step-content">
    <div class="step-header">
      <h3>第一步：选择房间</h3>
      <p class="step-description">
        请选择一个可用房间办理入住
      </p>
    </div>

    <!-- 房间列表 -->
    <div class="available-rooms-grid">
      <div
        v-for="room in availableRooms"
        :key="room.roomId"
        :class="['room-option', { selected: selectedRoomId === room.roomId }]"
        @click="selectRoom(room.roomId)"
      >
        <div class="room-icon">
          🏠
        </div>
        <div class="room-number">
          房间 {{ room.roomId }}
        </div>
        <div class="room-details">
          <span class="room-price">¥{{ room.pricePerNight.toFixed(2) }}/晚</span>
        </div>
        <div v-if="selectedRoomId === room.roomId" class="selected-badge">
          ✓
        </div>
      </div>
    </div>

    <div v-if="availableRooms.length === 0" class="empty-state">
      <p>暂无可用房间</p>
    </div>
  </div>
</template>

<script setup lang="ts">
// 房间信息接口（与API返回数据结构一致）
interface AvailableRoom {
  roomId: string;
  pricePerNight: number;
  isOccupied: boolean;
}

defineProps<{
  availableRooms: AvailableRoom[];
  checkInRecords: unknown[];
  selectedRoomId?: string;
}>();

const emit = defineEmits<{
  'update:selectedRoomId': [value: string];
  'next': [];
}>();

// 选择房间
const selectRoom = (roomId: string) => {
  emit('update:selectedRoomId', roomId);
  emit('next');
};
</script>

<style scoped>
.step-content {
  padding: 20px;
}

.step-header {
  margin-bottom: 32px;
  text-align: center;
}

.step-header h3 {
  font-size: 22px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}

.step-description {
  font-size: 14px;
  color: #64748b;
}

.available-rooms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
  max-width: 1000px;
  margin-left: auto;
  margin-right: auto;
}

.room-option {
  position: relative;
  padding: 20px;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  min-height: 160px;
}

.room-option:hover {
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.room-option.selected {
  border-color: #10b981;
  border-width: 3px;
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3);
  transform: translateY(-2px);
}

.room-icon {
  font-size: 36px;
  margin-bottom: 4px;
}

.room-number {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.room-details {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.room-price {
  color: #ef4444;
  font-weight: 600;
  font-size: 14px;
}

.selected-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: #10b981;
  color: white;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: bold;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
  animation: checkmark-appear 0.3s ease;
}

@keyframes checkmark-appear {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  50% {
    transform: scale(1.2);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
  font-size: 15px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .available-rooms-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
  }

  .room-option {
    padding: 16px;
    min-height: 140px;
  }

  .room-icon {
    font-size: 32px;
  }

  .room-number {
    font-size: 16px;
  }
}
</style>
