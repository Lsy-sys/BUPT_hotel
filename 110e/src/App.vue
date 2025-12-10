<script setup lang="ts">
import { useAuth } from './composables/useAuth';
import { useHvacService } from './composables/useHvacService';
import { ROOM_IDS, MAX_SERVICE_OBJECTS, WAIT_TIME } from './constants/index';

// 使用认证管理
const {
  currentUser,
  userName,
  currentView,
  handleLogin,
  handleLogout,
  hasPermission,
  switchView
} = useAuth();

// 使用服务管理
const {
  hvacService,
  refreshKey,
  allRooms,
  serviceQueue,
  waitingQueue,
  allBills,
  occupiedRooms,
  checkInRecords,
  availableRooms
} = useHvacService();

// 刷新处理
const handleRefresh = () => {
  refreshKey.value++;
};
</script>

<template>
  <router-view
    :on-login="handleLogin"
    :user-name="userName"
    :current-view="currentView"
    :total-rooms="ROOM_IDS.length"
    :max-service-objects="MAX_SERVICE_OBJECTS"
    :wait-time="WAIT_TIME"
    :serving-count="serviceQueue.length"
    :waiting-count="waitingQueue.length"
    :has-permission="hasPermission"
    :switch-view="switchView"
    :on-logout="handleLogout"
    :hvac-service="hvacService"
    :occupied-rooms="occupiedRooms"
    :all-rooms="allRooms"
    :refresh-key="refreshKey"
    :service-queue="serviceQueue"
    :waiting-queue="waitingQueue"
    :available-rooms="availableRooms"
    :check-in-records="checkInRecords"
    :all-bills="allBills"
    @refresh="handleRefresh"
  />
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
  background: #f8f9fb;
}

#app {
  width: 100%;
  min-height: 100vh;
}
</style>
