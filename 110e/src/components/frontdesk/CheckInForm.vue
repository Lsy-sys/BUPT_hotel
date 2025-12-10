<template>
  <div class="checkin-section">
    <h2>办理入住</h2>

    <!-- 成功弹窗 -->
    <SuccessModal
      :show="showSuccessModal"
      title="办理入住成功"
      :message="successMessage"
      action-text="前往客房控制"
      close-text="继续办理"
      :show-action="true"
      @action="handleGoToRoom"
      @close="closeSuccessModal"
    >
      <div class="success-details">
        <div class="detail-item">
          <span class="label">房间号：</span>
          <span class="value">{{ checkedInRoomId }}</span>
        </div>
        <div class="detail-item">
          <span class="label">客户姓名：</span>
          <span class="value">{{ form.guestName }}</span>
        </div>
        <div class="detail-item">
          <span class="label">入住天数：</span>
          <span class="value">{{ form.stayDays }} 天</span>
        </div>
      </div>
    </SuccessModal>

    <!-- 步骤指示器 -->
    <StepIndicator :steps="steps" :current-step="currentStep" />

    <!-- 步骤 1: 选择房间 -->
    <Step1RoomSelection
      v-if="currentStep === 0"
      v-model:selected-room-id="form.roomId"
      :available-rooms="availableRooms"
      :check-in-records="checkInRecords"
      @next="nextStep"
    />

    <!-- 步骤 2: 客户信息 -->
    <Step2GuestInfo
      v-if="currentStep === 1"
      v-model="guestInfo"
    />

    <!-- 步骤 3: 空调设置 -->
    <Step3ACSettings
      v-if="currentStep === 2"
      v-model="acSettings"
    />

    <!-- 步骤 4: 确认与支付 -->
    <Step4Confirmation
      v-if="currentStep === 3"
      :form-data="form"
      :room-price="getRoomPrice(form.roomId)"
      @confirm="handleSubmit"
      @prev="prevStep"
    />

    <!-- 导航按钮 -->
    <div v-if="currentStep > 0 && currentStep < 3" class="navigation-buttons">
      <button type="button" class="btn-secondary" @click="prevStep">
        上一步
      </button>
      <button
        type="button"
        class="btn-primary"
        :disabled="!isCurrentStepValid"
        @click="nextStep"
      >
        下一步
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue';
import { ACMode, FanSpeed } from '../../types/index';
import { DEFAULT_TEMP } from '../../constants/index';
import SuccessModal from '../common/SuccessModal.vue';
import StepIndicator from './checkin/StepIndicator.vue';
import Step1RoomSelection from './checkin/Step1RoomSelection.vue';
import Step2GuestInfo from './checkin/Step2GuestInfo.vue';
import Step3ACSettings from './checkin/Step3ACSettings.vue';
import Step4Confirmation from './checkin/Step4Confirmation.vue';
import type { AvailableRoom } from '../../composables/useHvacService';

const props = defineProps<{
  availableRooms: AvailableRoom[];
  checkInRecords: unknown[];
  onCheckIn: (
    roomId: string,
    mode: ACMode,
    guestName?: string,
    guestPhone?: string,
    idCard?: string,
    stayDays?: number,
    roomTemp?: number,
    targetTemp?: number,
    fanSpeed?: FanSpeed
  ) => Promise<{ success: boolean; message: string; }>;
}>();

const emit = defineEmits<{
  switchToRoom: [];
}>();

const steps = ['选择房间', '客户信息', '空调设置', '确认支付'];
const currentStep = ref(0);

// 成功弹窗相关
const showSuccessModal = ref(false);
const successMessage = ref('');
const checkedInRoomId = ref('');

// 表单数据
const form = reactive({
  roomId: '',
  mode: ACMode.COOLING as ACMode,
  guestName: '',
  guestPhone: '',
  idType: 'id_card',
  idNumber: '',
  stayDays: 1,
  specialRequest: '',
  // 空调初始化参数
  roomTemp: DEFAULT_TEMP,
  targetTemp: DEFAULT_TEMP,
  fanSpeed: FanSpeed.MEDIUM as FanSpeed
});

// 客户信息(用于双向绑定)
const guestInfo = computed({
  get: () => ({
    guestName: form.guestName,
    guestPhone: form.guestPhone,
    idType: form.idType,
    idNumber: form.idNumber,
    stayDays: form.stayDays,
    specialRequest: form.specialRequest
  }),
  set: (value) => {
    form.guestName = value.guestName;
    form.guestPhone = value.guestPhone;
    form.idType = value.idType;
    form.idNumber = value.idNumber;
    form.stayDays = value.stayDays;
    form.specialRequest = value.specialRequest;
  }
});

// 空调设置(用于双向绑定)
const acSettings = computed({
  get: () => ({
    mode: form.mode,
    roomTemp: form.roomTemp,
    targetTemp: form.targetTemp,
    fanSpeed: form.fanSpeed
  }),
  set: (value) => {
    form.mode = value.mode as ACMode;
    form.roomTemp = value.roomTemp;
    form.targetTemp = value.targetTemp;
    form.fanSpeed = value.fanSpeed as FanSpeed;
  }
});

// 获取房间价格（从API数据中获取）
const getRoomPrice = (roomId: string): number => {
  if (!roomId) return 0;
  const room = props.availableRooms.find(r => r.roomId === roomId);
  return room ? room.pricePerNight : 0;
};

// 验证当前步骤
const isCurrentStepValid = computed(() => {
  switch (currentStep.value) {
    case 0: // 选择房间
      return !!form.roomId;
    case 1: // 客户信息
      return !!form.guestName && !!form.guestPhone && !!form.idNumber && form.stayDays > 0;
    case 2: // 空调设置
      return !!form.mode;
    default:
      return true;
  }
});

// 下一步
const nextStep = () => {
  if (currentStep.value < steps.length - 1 && isCurrentStepValid.value) {
    currentStep.value++;
  }
};

// 上一步
const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
};

// 提交表单
const handleSubmit = async () => {
  try {
    const result = await props.onCheckIn(
      form.roomId,
      form.mode as ACMode,
      form.guestName,
      form.guestPhone,
      form.idNumber,
      form.stayDays,
      form.roomTemp,
      form.targetTemp,
      form.fanSpeed
    );

    if (result.success) {
      // 保存房间号和成功消息
      checkedInRoomId.value = form.roomId;
      successMessage.value = `房间 ${form.roomId} 已成功办理入住，您可以前往客房控制页面管理空调设置。`;

      // 显示成功弹窗
      showSuccessModal.value = true;

      // 重置表单
      Object.assign(form, {
        roomId: '',
        mode: ACMode.COOLING,
        guestName: '',
        guestPhone: '',
        idType: 'id_card',
        idNumber: '',
        stayDays: 1,
        specialRequest: '',
        roomTemp: DEFAULT_TEMP,
        targetTemp: DEFAULT_TEMP,
        fanSpeed: FanSpeed.MEDIUM
      });
      currentStep.value = 0;
    } else {
      alert(result.message || '办理入住失败，请重试');
    }
  } catch (error) {
    console.error('办理入住失败:', error);
    alert('办理入住失败，请重试');
  }
};

// 关闭成功弹窗
const closeSuccessModal = () => {
  showSuccessModal.value = false;
};

// 跳转到客房控制页面
const handleGoToRoom = () => {
  showSuccessModal.value = false;
  emit('switchToRoom');
};
</script>

<style scoped>
.checkin-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

/* 成功弹窗详情 */
.success-details {
  background: #f8fafc;
  border-radius: 12px;
  padding: 20px;
  margin: 16px 0;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #e2e8f0;
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-item .label {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

.detail-item .value {
  font-size: 15px;
  color: #1e293b;
  font-weight: 600;
}

.checkin-section h2 {
  font-size: 24px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e2e8f0;
}

.navigation-buttons {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 24px;
  padding: 20px;
}

.btn-secondary,
.btn-primary {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.btn-secondary {
  background: white;
  color: #64748b;
  border: 1px solid #e2e8f0;
  min-width: 100px;
}

.btn-secondary:hover {
  background: #f8fafc;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  min-width: 100px;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
