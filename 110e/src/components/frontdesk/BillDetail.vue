<template>
  <div class="bill-section">
    <!-- 账单头部 -->
    <BillHeader
      :room-id="bill.roomId"
      @print="handlePrint"
      @close="handleClose"
    />

    <div class="bill-content">
      <!-- 客户信息 -->
      <GuestInfoSection
        :guest-name="bill.guestName"
        :guest-phone="bill.guestPhone"
      />

      <!-- 入住信息 -->
      <StayInfoSection
        :room-id="bill.roomId"
        :check-in-time="bill.checkInTime"
        :check-out-time="bill.checkOutTime"
        :stay-days="bill.stayDays"
      />

      <!-- 费用明细 -->
      <ChargesBreakdown
        :room-rate="bill.roomRate || 280"
        :stay-days="stayDays"
        :room-charge="bill.roomFee || roomCharge"
        :total-service-duration="bill.totalServiceDuration"
        :ac-cost="bill.acCost"
        :detail-records-total-cost="detailRecordsTotalCost"
        :deposit="bill.deposit"
      />

      <!-- 空调使用详单 -->
      <ACUsageRecords :records="bill.detailRecords" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Bill } from '../../types/index';
import BillHeader from './bill/BillHeader.vue';
import GuestInfoSection from './bill/GuestInfoSection.vue';
import StayInfoSection from './bill/StayInfoSection.vue';
import ChargesBreakdown from './bill/ChargesBreakdown.vue';
import ACUsageRecords from './bill/ACUsageRecords.vue';

const props = defineProps<{
  bill: Bill;
}>();

const emit = defineEmits<{
  print: [bill: Bill];
  close: [];
}>();

const handlePrint = () => {
  emit('print', props.bill);
};

const handleClose = () => {
  emit('close');
};

// 计算入住天数
const stayDays = computed(() => {
  if (props.bill.stayDays) return props.bill.stayDays;
  const days = Math.ceil((props.bill.checkOutTime - props.bill.checkInTime) / (1000 * 60 * 60 * 24));
  return days > 0 ? days : 1;
});

// 计算房费（备用，优先使用后端返回的roomFee）
const roomCharge = computed(() => {
  if (props.bill.roomCharge) return props.bill.roomCharge;
  const rate = props.bill.roomRate || 280;
  return rate * stayDays.value;
});

// 计算详单记录的费用总和
const detailRecordsTotalCost = computed(() => {
  return props.bill.detailRecords.reduce((sum, record) => sum + record.cost, 0);
});
</script>

<style scoped>
.bill-section {
  margin-bottom: 24px;
  padding: 28px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.bill-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
