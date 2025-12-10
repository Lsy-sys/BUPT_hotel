<template>
  <div class="room-client">
    <div class="room-header">
      <h2>房间 {{ roomId }}</h2>
      <button
        :class="['btn-power', { 'active': roomState?.isOn, 'loading': isLoading }]"
        :disabled="isLoading"
        @click="togglePower"
      >
        <span v-if="isLoading">处理中...</span>
        <span v-else>{{ roomState?.isOn ? '关机' : '开机' }}</span>
      </button>
    </div>

    <div v-if="roomState?.isOn" class="control-panel">
      <!-- 当前温度显示 -->
      <TemperatureDisplay
        :current-temp="roomState.currentTemp"
        :status="roomState.status"
        :status-text="getStatusText(roomState.status)"
      />

      <!-- 主控制区域 -->
      <div class="main-controls">
        <!-- 模式控制 -->
        <ModeControl
          :current-mode="roomState.mode"
          @switch="handleModeSwitch"
        />

        <!-- 温度控制 -->
        <TemperatureControl
          :temperature="targetTemp"
          :min-temp="tempRange.min"
          :max-temp="tempRange.max"
          :step="TEMP_STEP"
          @update="handleTempUpdate"
        />
      </div>

      <!-- 风速控制 -->
      <FanSpeedControl
        :current-speed="fanSpeed"
        @change="handleFanSpeedChange"
      />

      <!-- 费用显示 -->
      <BillingDisplay
        :total-cost="roomState.totalCost"
        :stage-cost="stageCost"
      />
    </div>

    <!-- 空调关闭状态 -->
    <div v-else class="empty-state">
      <div class="empty-icon">
        <div class="ac-icon">
          <div class="ac-body"></div>
          <div class="ac-lines">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
      <div class="empty-title">
        空调已关闭
      </div>
      <div class="empty-description">
        点击上方"开机"按钮启动空调服务
      </div>
      <div class="empty-features">
        <div class="feature-item">
          <div class="feature-dot"></div>
          <span>智能温度控制</span>
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>
          <span>三档风速调节</span>
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>
          <span>实时费用显示</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import type { RoomState } from '../../types/index';
import { ACMode, FanSpeed, RoomStatus } from '../../types/index';
import { TEMP_RANGE, TEMP_STEP } from '../../constants/index';
import TemperatureDisplay from './TemperatureDisplay.vue';
import ModeControl from './ModeControl.vue';
import TemperatureControl from './TemperatureControl.vue';
import FanSpeedControl from './FanSpeedControl.vue';
import BillingDisplay from './BillingDisplay.vue';

const props = defineProps<{
  roomId: string;
  roomState: RoomState | null;
  isLoading?: boolean;
  onTurnOn: () => void;
  onTurnOff: () => void;
  onUpdateSettings: (targetTemp: number, fanSpeed: FanSpeed) => void;
  onSetMode: (mode: ACMode) => void;
}>();

const targetTemp = ref(25);
const fanSpeed = ref<FanSpeed>(FanSpeed.MEDIUM);
const lastTotalCost = ref(0); // 记录上次关机时的累计费用

// 防抖定时器：用于温度和风速调节
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
const DEBOUNCE_DELAY = 1000; // 1秒防抖延迟

const tempRange = computed(() => {
  if (!props.roomState) return { min: 18, max: 30 };
  return TEMP_RANGE[props.roomState.mode];
});

// 计算阶段费用（本次开机费用）
const stageCost = computed(() => {
  if (!props.roomState || !props.roomState.isOn) {
    return 0;
  }
  // 阶段费用 = 当前累计费用 - 上次关机时的累计费用
  return Math.max(0, props.roomState.totalCost - lastTotalCost.value);
});

watch(() => props.roomState, (newState, oldState) => {
  if (newState) {
    targetTemp.value = newState.targetTemp;
    fanSpeed.value = newState.fanSpeed;

    // 检测开关机状态变化
    if (oldState && !oldState.isOn && newState.isOn) {
      // 刚开机：记录开机前的累计费用
      lastTotalCost.value = oldState.totalCost || 0;
    } else if (oldState && oldState.isOn && !newState.isOn) {
      // 刚关机：更新最后的累计费用
      lastTotalCost.value = newState.totalCost || 0;
    }
  }
}, { immediate: true, deep: true });


const togglePower = () => {
  if (props.roomState?.isOn) {
    props.onTurnOff();
  } else {
    props.onTurnOn();
  }
};

const handleModeSwitch = (mode: ACMode) => {
  props.onSetMode(mode);
};

const handleTempUpdate = (temp: number) => {
  targetTemp.value = temp;
  
  // 清除之前的定时器
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  
  // 设置新的定时器，1秒后发送请求
  debounceTimer = setTimeout(() => {
    props.onUpdateSettings(targetTemp.value, fanSpeed.value);
    debounceTimer = null;
  }, DEBOUNCE_DELAY);
};

const handleFanSpeedChange = (speed: FanSpeed) => {
  fanSpeed.value = speed;
  
  // 清除之前的定时器
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  
  // 设置新的定时器，1秒后发送请求
  debounceTimer = setTimeout(() => {
    props.onUpdateSettings(targetTemp.value, fanSpeed.value);
    debounceTimer = null;
  }, DEBOUNCE_DELAY);
};

const getStatusText = (status: RoomStatus): string => {
  const statusMap = {
    [RoomStatus.OFF]: '关机',
    [RoomStatus.STANDBY]: '待机',
    [RoomStatus.SERVING]: '送风中',
    [RoomStatus.WAITING]: '等待中',
    [RoomStatus.TARGET_REACHED]: '达到目标'
  };
  return statusMap[status] || '未知';
};
</script>

<style scoped>
.room-client {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 16px;
  border: 2px solid #e2e8f0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  animation: slideInUp 0.5s ease-out;
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.room-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 3px solid #067ef5;
  background: linear-gradient(135deg, transparent 0%, rgba(6, 126, 245, 0.03) 100%);
  padding: 20px;
  border-radius: 12px;
}

.room-header h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: 0.5px;
}

.btn-power {
  padding: 12px 36px;
  font-size: 16px;
  font-weight: 600;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
  color: #64748b;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 120px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.btn-power:hover {
  background: linear-gradient(135deg, #e2e8f0 0%, #f1f5f9 100%);
  border-color: #cbd5e1;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

.btn-power.active {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  border-color: #059669;
  color: white;
  box-shadow: 0 4px 12px rgba(5, 150, 105, 0.25);
}

.btn-power.active:hover {
  background: linear-gradient(135deg, #047857 0%, #065f46 100%);
  border-color: #047857;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(5, 150, 105, 0.3);
}

.btn-power:disabled,
.btn-power.loading {
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none;
}

.btn-power.loading {
  position: relative;
}

.btn-power.loading span {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.control-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.main-controls {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 40px;
  min-height: 500px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 16px;
  border: 2px solid #e2e8f0;
}

.empty-icon {
  margin-bottom: 32px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.ac-icon {
  position: relative;
  width: 120px;
  height: 80px;
}

.ac-body {
  width: 100%;
  height: 60px;
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
  border-radius: 12px;
  border: 3px solid #067ef5;
  position: relative;
  box-shadow: 0 4px 20px rgba(2, 132, 199, 0.2);
}

.ac-body::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  background: #067ef5;
  border-radius: 50%;
  opacity: 0.3;
}

.ac-lines {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 8px;
}

.ac-lines span {
  display: block;
  width: 3px;
  height: 16px;
  background: #cbd5e1;
  border-radius: 2px;
}

.ac-lines span:nth-child(1),
.ac-lines span:nth-child(3) {
  height: 12px;
}

.empty-title {
  font-size: 24px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
}

.empty-description {
  font-size: 15px;
  color: #64748b;
  margin-bottom: 40px;
  text-align: center;
}

.empty-features {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  justify-content: center;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  background: white;
  border-radius: 24px;
  border: 2px solid #e0f2fe;
  font-size: 14px;
  color: #475569;
  font-weight: 500;
  transition: all 0.3s;
}

.feature-item:hover {
  border-color: #067ef5;
  background: #f0f9ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.15);
}

.feature-dot {
  width: 8px;
  height: 8px;
  background: #067ef5;
  border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.2);
}

@media (max-width: 768px) {
  .main-controls {
    grid-template-columns: 1fr;
  }
}
</style>
