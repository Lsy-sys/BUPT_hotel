<template>
  <div class="current-temp-display">
    <div class="temp-value-large">
      {{ displayTemp }}
    </div>
    <div class="temp-label-large">
      当前温度
    </div>
    <div class="status-badge" :class="'badge-' + status">
      {{ statusText }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RoomStatus } from '../../types/index';

const props = defineProps<{
  currentTemp: number;
  status: RoomStatus;
  statusText: string;
}>();

const displayTemp = computed(() => {
  if (props.currentTemp === undefined || props.currentTemp === null || isNaN(props.currentTemp)) {
    return '未知';
  }
  return `${props.currentTemp.toFixed(1)}°C`;
});
</script>

<style scoped>
.current-temp-display {
  text-align: center;
  padding: 50px 30px;
  border-radius: 16px;
  border: 2px solid #e2e8f0;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.current-temp-display:hover {
  border-color: #067ef5;
  box-shadow: 0 6px 16px rgba(6, 126, 245, 0.15);
  transform: translateY(-2px);
}

.temp-value-large {
  font-size: 72px;
  font-weight: 800;
  background: linear-gradient(135deg, #067ef5 0%, #0369a1 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 16px;
  line-height: 1.1;
  letter-spacing: -2px;
}

.temp-label-large {
  font-size: 15px;
  color: #64748b;
  margin-bottom: 16px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.status-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.badge-SERVING {
  background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
  color: #059669;
  border: 2px solid #86efac;
  box-shadow: 0 2px 6px rgba(5, 150, 105, 0.15);
}

.badge-WAITING {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
  border: 2px solid #fbbf24;
  box-shadow: 0 2px 6px rgba(217, 119, 6, 0.15);
}

.badge-STANDBY {
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  color: #6b7280;
  border: 2px solid #d1d5db;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.badge-TARGET_REACHED {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.badge-OFF {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  color: #dc2626;
  border: 2px solid #fca5a5;
  box-shadow: 0 2px 6px rgba(220, 38, 38, 0.15);
}

@media (max-width: 768px) {
  .temp-value-large {
    font-size: 56px;
  }
}
</style>

