<template>
  <div class="view-container">
    <FrontDeskBilling
      :available-rooms="availableRooms"
      :occupied-rooms="occupiedRooms"
      :check-in-records="checkInRecords"
      :all-rooms="allRooms"
      :all-bills="allBills"
      :on-check-in="handleCheckIn"
      :on-checkout="handleCheckout"
      @switch-to-room="handleSwitchToRoom"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import FrontDeskBilling from '../frontdesk/FrontDeskBilling.vue';
import type { IHvacService } from '../../services/ApiAdapter';
import type { Bill, CheckInRecord, RoomState } from '../../types/index';
import { ACMode, FanSpeed } from '../../types/index';
import type { AvailableRoom } from '../../composables/useHvacService';

const props = defineProps<{
  hvacService: IHvacService;
  availableRooms: AvailableRoom[];
  occupiedRooms: string[];
  checkInRecords: CheckInRecord[];
  allRooms: RoomState[];
  allBills: Bill[];
}>();

const emit = defineEmits<{
  refresh: [];
  switchView: [view: 'room'];
}>();

// 页面加载时请求一次数据
onMounted(async () => {
  if (props.hvacService.refreshCheckInRecords && props.hvacService.refreshRoomStates) {
    await Promise.all([
      props.hvacService.refreshCheckInRecords(),
      props.hvacService.refreshRoomStates()
    ]);
    emit('refresh');
  }
});

// 前台操作 - 办理入住（支持空调初始化参数）
const handleCheckIn = async (
  roomId: string,
  mode: ACMode,
  guestName?: string,
  guestPhone?: string,
  idCard?: string,
  stayDays?: number,
  roomTemp?: number,
  targetTemp?: number,
  fanSpeed?: FanSpeed
): Promise<{ success: boolean; message: string }> => {
  const result = await props.hvacService.checkIn(roomId, mode, guestName, guestPhone, idCard, stayDays, roomTemp, targetTemp, fanSpeed);

  if (result.success) {
    // 入住成功，手动刷新房间状态和入住记录
    if (props.hvacService.refreshCheckInRecords && props.hvacService.refreshRoomStates) {
      await Promise.all([
        props.hvacService.refreshCheckInRecords(),
        props.hvacService.refreshRoomStates()
      ]);
    }
    emit('refresh');
  }

  return result;
};

// 前台操作 - 办理退房结账
const handleCheckout = async (roomId: string): Promise<Bill | null> => {
  try {
    const bill = await props.hvacService.checkOut(roomId);

    if (bill) {
      // 退房成功，手动刷新房间状态和入住记录
      if (props.hvacService.refreshCheckInRecords && props.hvacService.refreshRoomStates) {
        await Promise.all([
          props.hvacService.refreshCheckInRecords(),
          props.hvacService.refreshRoomStates()
        ]);
      }
      emit('refresh');
    }

    return bill;
  } catch (error) {
    console.error('退房失败:', error);
    return null;
  }
};

// 处理切换到客房控制页面
const handleSwitchToRoom = () => {
  emit('switchView', 'room');
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

