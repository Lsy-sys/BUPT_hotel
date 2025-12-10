<template>
  <div class="view-container">
    <ManagerStatistics
      :on-generate-report="handleGenerateReport"
    />
  </div>
</template>

<script setup lang="ts">
import ManagerStatistics from '../manager/ManagerStatistics.vue';
import type { IHvacService } from '../../services/ApiAdapter';
import type { StatisticsReport } from '../../types/index';

const props = defineProps<{
  hvacService: IHvacService;
}>();

// 经理操作 - 生成报表
const handleGenerateReport = async (startTime: number, endTime: number): Promise<StatisticsReport> => {
  // 使用当前运行数据和历史账单一起生成报表
  const historicalReport = await props.hvacService.generateStatistics(startTime, endTime);
  const currentRooms = props.hvacService.getAllRoomStates();

  // 合并当前运行数据
  let totalCost = historicalReport.totalCost;
  const activeRooms = new Set<string>();

  // 添加当前正在运行的房间数据
  currentRooms.forEach(room => {
    if (room.isOn && room.totalCost > 0) {
      activeRooms.add(room.roomId);
      // 如果这个房间不在历史数据中，添加它
      const existingRoom = historicalReport.roomStatistics.find(r => r.roomId === room.roomId);
      if (!existingRoom) {
        totalCost += room.totalCost;
      }
    }
  });

  return {
    ...historicalReport,
    totalRooms: Math.max(historicalReport.totalRooms, activeRooms.size),
    totalCost,
    averageCostPerRoom: activeRooms.size > 0 ? totalCost / activeRooms.size : 0
  };
};
</script>

<style scoped>
.view-container {
  width: 100%;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>

