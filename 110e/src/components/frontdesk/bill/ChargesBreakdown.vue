<template>
  <div class="bill-charges">
    <h3>💰 费用明细</h3>

    <!-- 房费 -->
    <div class="charge-section">
      <div class="charge-row">
        <span>房费</span>
        <span>¥{{ roomRate }}/天 × {{ stayDays }}天</span>
        <span class="amount">¥{{ roomCharge.toFixed(2) }}</span>
      </div>
    </div>

    <!-- 空调使用费 -->
    <div class="charge-section">
      <div class="charge-row">
        <span>空调使用费</span>
        <span>¥1/度（调温计费）</span>
        <span class="amount">¥{{ acCost.toFixed(2) }}</span>
      </div>
      <!-- 计费说明 -->
      <div class="charge-note info">
        <span>💡 实际费用以系统计算为准</span>
      </div>
    </div>

    <!-- 小计 -->
    <div class="charge-subtotal">
      <span>小计</span>
      <span class="amount">¥{{ subtotal.toFixed(2) }}</span>
    </div>

    <!-- 押金说明 -->
    <div class="deposit-section">
      <div class="deposit-info">
        <div class="deposit-icon">
          💳
        </div>
        <div class="deposit-content">
          <div class="deposit-title">
            押金信息
          </div>
          <div class="deposit-details">
            <div class="deposit-row">
              <span class="deposit-label">✓ 已交押金：</span>
              <span class="deposit-value paid">¥{{ deposit.toFixed(2) }}</span>
            </div>
            <div class="deposit-row">
              <span class="deposit-label">✓ 押金退还：</span>
              <span class="deposit-value refunded">¥{{ deposit.toFixed(2) }}（原路退回）</span>
            </div>
          </div>
          <div class="deposit-note">
            💡 押金与住宿费用分离计算，不包含在应付金额中
          </div>
        </div>
      </div>
    </div>

    <!-- 最终应付金额（不含押金） -->
    <div class="charge-final">
      <div class="final-label">
        <span>应付金额</span>
        <span class="final-note">（不含押金，押金单独退还）</span>
      </div>
      <span class="final-amount">
        ¥{{ subtotal.toFixed(2) }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  roomRate: number;
  stayDays: number;
  roomCharge: number;
  totalServiceDuration: number;
  acCost: number; // 空调费用（不是总费用）
  detailRecordsTotalCost: number;
  deposit?: number;
}>();

const deposit = computed(() => props.deposit || 200);
// 小计 = 房费 + 空调费
const subtotal = computed(() => props.roomCharge + props.acCost);

const formatDuration = (seconds: number): string => {
  if (seconds === 0) return '-';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const parts = [];
  if (hours > 0) parts.push(`${hours}小时`);
  if (minutes > 0) parts.push(`${minutes}分钟`);
  if (secs > 0) parts.push(`${secs}秒`);

  return parts.join('') || '-';
};
</script>

<style scoped>
.bill-charges {
  padding: 20px 24px;
  background: white;
  border-radius: 12px;
  border: 2px solid #e2e8f0;
  margin-bottom: 20px;
}

.bill-charges h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 2px solid #f1f5f9;
}

.charge-section {
  margin-bottom: 16px;
}

.charge-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 14px;
}

.charge-row span:first-child {
  font-weight: 600;
  color: #475569;
  flex: 0 0 100px;
}

.charge-row span:nth-child(2) {
  color: #64748b;
  font-size: 13px;
  flex: 1;
  text-align: center;
}

.charge-row .amount {
  font-weight: 700;
  color: #1e293b;
  font-size: 15px;
  flex: 0 0 100px;
  text-align: right;
}

.charge-note {
  margin-top: 8px;
  padding: 8px 12px;
  background: #fef3c7;
  border-left: 3px solid #f59e0b;
  border-radius: 4px;
  font-size: 12px;
  color: #92400e;
}

.charge-note.info {
  background: #dbeafe;
  border-left: 3px solid #3b82f6;
  color: #1e40af;
}

.charge-subtotal {
  display: flex;
  justify-content: space-between;
  padding: 16px 12px;
  border-top: 2px solid #e2e8f0;
  border-bottom: 2px solid #e2e8f0;
  margin: 16px 0;
  font-size: 16px;
  font-weight: 600;
}

.charge-subtotal .amount {
  color: #ef4444;
  font-size: 18px;
}

.deposit-section {
  margin: 20px 0;
}

.deposit-info {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border: 2px solid #86efac;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  gap: 12px;
}

.deposit-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.deposit-content {
  flex: 1;
}

.deposit-title {
  font-size: 16px;
  font-weight: 600;
  color: #15803d;
  margin-bottom: 12px;
}

.deposit-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.deposit-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.deposit-label {
  color: #166534;
  font-weight: 500;
}

.deposit-value {
  font-weight: 700;
  font-size: 15px;
}

.deposit-value.paid {
  color: #dc2626;
}

.deposit-value.refunded {
  color: #16a34a;
}

.deposit-note {
  margin-top: 12px;
  padding: 8px 12px;
  background: rgba(134, 239, 172, 0.3);
  border-radius: 6px;
  font-size: 13px;
  color: #15803d;
  font-weight: 500;
}

.charge-final {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  border-radius: 12px;
  border: 2px solid #fca5a5;
  margin-top: 20px;
}

.final-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.final-label span:first-child {
  font-size: 18px;
  font-weight: 700;
  color: #991b1b;
}

.final-note {
  font-size: 12px;
  color: #b91c1c;
  font-weight: 500;
}

.final-amount {
  font-size: 32px;
  font-weight: 900;
  color: #dc2626;
  letter-spacing: -1px;
}
</style>
