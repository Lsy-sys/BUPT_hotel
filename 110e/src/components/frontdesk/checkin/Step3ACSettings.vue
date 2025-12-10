<template>
  <div class="step-content">
    <div class="step-header">
      <h3>第三步：空调设置</h3>
      <p class="step-description">
        选择空调初始工作模式和温度设置
      </p>
    </div>

    <div class="ac-settings">
      <!-- 模式选择 -->
      <div class="mode-selection">
        <label class="mode-label">选择工作模式：</label>
        <div class="mode-buttons">
          <button
            v-for="mode in modes"
            :key="mode.value"
            :class="['mode-btn', { active: selectedMode === mode.value }]"
            type="button"
            @click="selectMode(mode.value)"
          >
            <span class="mode-icon">{{ mode.icon }}</span>
            <span class="mode-name">{{ mode.name }}</span>
          </button>
        </div>
      </div>

      <!-- 温度设置 -->
      <div class="temp-settings">
        <div class="temp-input-group">
          <label class="temp-label">房间当前温度：</label>
          <div class="temp-input-wrapper">
            <input
              v-model.number="roomTemp"
              type="number"
              class="temp-input"
              :min="15"
              :max="35"
              step="0.5"
            />
            <span class="temp-unit">°C</span>
          </div>
          <span class="temp-hint">实际房间温度（15-35°C）</span>
        </div>

        <div class="temp-input-group">
          <label class="temp-label">目标温度：</label>
          <div class="temp-input-wrapper">
            <input
              v-model.number="targetTemp"
              type="number"
              class="temp-input"
              :min="tempRange.min"
              :max="tempRange.max"
              step="0.5"
            />
            <span class="temp-unit">°C</span>
          </div>
          <span class="temp-hint">
            {{ selectedMode === 'COOLING' ? '制冷模式：18-25°C' : '制热模式：25-30°C' }}
          </span>
        </div>
      </div>

      <!-- 风速选择 -->
      <div class="fan-speed-selection">
        <label class="fan-label">选择风速：</label>
        <div class="fan-buttons">
          <button
            v-for="speed in fanSpeeds"
            :key="speed.value"
            :class="['fan-btn', { active: selectedFanSpeed === speed.value }]"
            type="button"
            @click="selectFanSpeed(speed.value)"
          >
            <span class="fan-icon">{{ speed.icon }}</span>
            <span class="fan-name">{{ speed.name }}</span>
            <span class="fan-rate">{{ speed.rate }}</span>
          </button>
        </div>
      </div>

      <!-- 设置信息卡片 -->
      <div class="setting-info">
        <div class="info-card">
          <div class="info-icon">
            🌡️
          </div>
          <div class="info-content">
            <div class="info-label">
              房间温度
            </div>
            <div class="info-value">
              {{ roomTemp }}°C
            </div>
          </div>
        </div>
        <div class="info-card">
          <div class="info-icon">
            🎯
          </div>
          <div class="info-content">
            <div class="info-label">
              目标温度
            </div>
            <div class="info-value">
              {{ targetTemp }}°C
            </div>
          </div>
        </div>
        <div class="info-card">
          <div class="info-icon">
            💨
          </div>
          <div class="info-content">
            <div class="info-label">
              风速
            </div>
            <div class="info-value">
              {{ getFanSpeedName(selectedFanSpeed) }}
            </div>
          </div>
        </div>
        <div class="info-card">
          <div class="info-icon">
            💰
          </div>
          <div class="info-content">
            <div class="info-label">
              计费标准
            </div>
            <div class="info-value">
              ¥1/度
            </div>
          </div>
        </div>
      </div>

      <!-- 温馨提示 -->
      <div class="tips-box">
        <div class="tips-header">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
          >
            <path
              d="M12 8v4M12 16h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            />
          </svg>
          <span>温馨提示</span>
        </div>
        <ul class="tips-list">
          <li>客户入住后可在房间内自行调节温度和风速</li>
          <li>空调系统将自动记录使用情况并计费</li>
          <li>退房时系统将生成详细的空调使用账单</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { ACMode, FanSpeed } from '../../../types/index';
import { TEMP_RANGE, DEFAULT_TEMP } from '../../../constants/index';

// 定义 props 接口
interface ACSettingsValue {
  mode: string;
  roomTemp: number;
  targetTemp: number;
  fanSpeed: string;
}

const props = defineProps<{
  modelValue?: ACSettingsValue;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: ACSettingsValue];
}>();

// 模式选项
const modes = [
  { value: 'COOLING', icon: '❄️', name: '制冷模式' },
  { value: 'HEATING', icon: '🔥', name: '制热模式' }
];

// 风速选项
const fanSpeeds = [
  { value: 'LOW', icon: '🌬️', name: '低风', rate: '3分钟/度' },
  { value: 'MEDIUM', icon: '💨', name: '中风', rate: '2分钟/度' },
  { value: 'HIGH', icon: '🌪️', name: '高风', rate: '1分钟/度' }
];

// 状态
const selectedMode = ref(props.modelValue?.mode || ACMode.COOLING);
const roomTemp = ref(props.modelValue?.roomTemp || DEFAULT_TEMP);
const targetTemp = ref(props.modelValue?.targetTemp || DEFAULT_TEMP);
const selectedFanSpeed = ref(props.modelValue?.fanSpeed || FanSpeed.MEDIUM);

// 根据模式计算温度范围
const tempRange = computed(() => {
  return TEMP_RANGE[selectedMode.value as ACMode] || { min: 18, max: 30 };
});

// 选择模式
const selectMode = (mode: string) => {
  selectedMode.value = mode;
  // 切换模式时，调整目标温度到有效范围内
  const range = TEMP_RANGE[mode as ACMode];
  if (targetTemp.value < range.min) {
    targetTemp.value = range.min;
  } else if (targetTemp.value > range.max) {
    targetTemp.value = range.max;
  }
  emitUpdate();
};

// 选择风速
const selectFanSpeed = (speed: string) => {
  selectedFanSpeed.value = speed;
  emitUpdate();
};

// 获取风速名称
const getFanSpeedName = (speed: string): string => {
  const speedMap: Record<string, string> = {
    'LOW': '低风',
    'MEDIUM': '中风',
    'HIGH': '高风'
  };
  return speedMap[speed] || '中风';
};

// 发送更新事件
const emitUpdate = () => {
  emit('update:modelValue', {
    mode: selectedMode.value,
    roomTemp: roomTemp.value,
    targetTemp: targetTemp.value,
    fanSpeed: selectedFanSpeed.value
  });
};

// 监听温度变化
watch([roomTemp, targetTemp], () => {
  emitUpdate();
});

// 初始化时发送一次更新
emitUpdate();
</script>

<style scoped>
.step-content {
  padding: 20px;
}

.step-header {
  margin-bottom: 24px;
}

.step-header h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}

.step-description {
  font-size: 14px;
  color: #64748b;
}

.ac-settings {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 模式选择 */
.mode-selection {
  background: #f8fafc;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #e2e8f0;
}

.mode-label,
.fan-label,
.temp-label {
  font-size: 14px;
  font-weight: 500;
  color: #475569;
  display: block;
  margin-bottom: 16px;
}

.mode-buttons {
  display: flex;
  gap: 16px;
}

.mode-btn {
  flex: 1;
  padding: 20px;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.mode-btn:hover {
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.mode-btn.active {
  border-color: #3b82f6;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.mode-icon {
  font-size: 32px;
}

.mode-name {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

/* 温度设置 */
.temp-settings {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  background: #f8fafc;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #e2e8f0;
}

.temp-input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.temp-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.temp-input {
  width: 100px;
  padding: 12px 16px;
  font-size: 18px;
  font-weight: 600;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  text-align: center;
  transition: all 0.2s;
}

.temp-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.temp-unit {
  font-size: 18px;
  font-weight: 600;
  color: #64748b;
}

.temp-hint {
  font-size: 12px;
  color: #94a3b8;
}

/* 风速选择 */
.fan-speed-selection {
  background: #f8fafc;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #e2e8f0;
}

.fan-buttons {
  display: flex;
  gap: 16px;
}

.fan-btn {
  flex: 1;
  padding: 16px;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.fan-btn:hover {
  border-color: #10b981;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
}

.fan-btn.active {
  border-color: #10b981;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
}

.fan-icon {
  font-size: 24px;
}

.fan-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.fan-rate {
  font-size: 11px;
  color: #64748b;
}

/* 设置信息卡片 */
.setting-info {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.info-card {
  padding: 16px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-icon {
  font-size: 24px;
}

.info-content {
  flex: 1;
}

.info-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.info-value {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

/* 温馨提示 */
.tips-box {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border: 2px solid #fbbf24;
  border-radius: 12px;
  padding: 16px;
}

.tips-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #78350f;
}

.tips-header svg {
  stroke: #78350f;
}

.tips-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tips-list li {
  font-size: 13px;
  color: #92400e;
  padding-left: 26px;
  position: relative;
}

.tips-list li::before {
  content: '•';
  position: absolute;
  left: 12px;
  color: #f59e0b;
}

/* 响应式 */
@media (max-width: 768px) {
  .temp-settings {
    grid-template-columns: 1fr;
  }

  .setting-info {
    grid-template-columns: repeat(2, 1fr);
  }

  .fan-buttons {
    flex-direction: column;
  }
}
</style>
