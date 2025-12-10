<template>
  <div class="billing-section">
    <div class="billing-card">
      <div class="billing-icon">
        💵
      </div>
      <div class="billing-label">
        阶段费用
      </div>
      <div class="billing-value">
        {{ displayStageCost }}
      </div>
      <div class="billing-hint">
        本次开机费用
      </div>
    </div>
    <div class="billing-card highlight">
      <div class="billing-icon">
        💰
      </div>
      <div class="billing-label">
        累计费用
      </div>
      <div class="billing-value primary">
        {{ displayTotalCost }}
      </div>
      <div class="billing-hint">
        入住至今总费用
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  totalCost: number;
  stageCost?: number;
}>();

// 阶段费用（本次开机费用）
// 如果没有传入stageCost，暂时使用totalCost作为占位
const displayStageCost = computed(() => {
  const cost = props.stageCost !== undefined ? props.stageCost : 0;
  return `¥${cost.toFixed(2)}`;
});

// 累计费用（从入住到现在的总费用）
const displayTotalCost = computed(() => {
  const cost = props.totalCost || 0;
  return `¥${cost.toFixed(2)}`;
});
</script>

<style scoped>
.billing-section {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.billing-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  padding: 24px;
  border-radius: 16px;
  border: 2px solid #e2e8f0;
  text-align: center;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.billing-card:hover {
  border-color: #067ef5;
  box-shadow: 0 6px 16px rgba(6, 126, 245, 0.15);
  transform: translateY(-2px);
}

.billing-card.highlight {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border-color: #10b981;
}

.billing-card.highlight:hover {
  border-color: #059669;
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.2);
}

.billing-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.billing-label {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.billing-card.highlight .billing-label {
  color: #047857;
}

.billing-value {
  font-size: 32px;
  font-weight: 800;
  color: #1e293b;
  margin-bottom: 8px;
  letter-spacing: -1px;
}

.billing-value.primary {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.billing-hint {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

.billing-card.highlight .billing-hint {
  color: #065f46;
}

@media (max-width: 768px) {
  .billing-section {
    grid-template-columns: 1fr;
  }
  
  .billing-value {
    font-size: 28px;
  }
}
</style>

