<template>
  <div class="overview-stats">
    <div class="stat-card">
      <div class="stat-label">
        使用房间数
      </div>
      <div class="stat-value">
        {{ totalRooms }}
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-label">
        服务请求次数
      </div>
      <div class="stat-value">
        {{ totalRequests }}
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-label">
        总服务时长
      </div>
      <div class="stat-value">
        {{ formatDuration(totalDuration) }}
      </div>
    </div>
    <div class="stat-card highlight">
      <div class="stat-label">
        总费用
      </div>
      <div class="stat-value">
        ¥{{ totalCost.toFixed(2) }}
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-label">
        平均费用/房间
      </div>
      <div class="stat-value">
        ¥{{ calculatedAvgCost.toFixed(2) }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  totalRooms: number;
  totalRequests: number;
  totalDuration: number; // 总服务时长（秒）
  totalCost: number;
}>();

// 计算平均费用/房间（避免除以0）
const calculatedAvgCost = computed(() => {
  if (props.totalRooms === 0) return 0;
  return props.totalCost / props.totalRooms;
});

// 格式化时长
const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${seconds}秒`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}时${mins}分`;
};
</script>

<style scoped>
.overview-stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 30px;
}

@media (max-width: 1200px) {
  .overview-stats {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .overview-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 20px;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
  border-radius: 12px;
  border: 2px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  text-align: center;
}

.stat-card:hover {
  border-color: #067ef5;
  box-shadow: 0 4px 12px rgba(6, 126, 245, 0.15);
  transform: translateY(-2px);
}

.stat-card.highlight {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #93c5fd;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.stat-card.highlight:hover {
  border-color: #3b82f6;
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.25);
  transform: translateY(-3px);
}

.stat-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.2;
}

.stat-card.highlight .stat-value {
  color: #067ef5;
}

.stat-card.highlight .stat-label {
  color: #0369a1;
}
</style>

