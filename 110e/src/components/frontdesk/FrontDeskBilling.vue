<template>
  <div class="front-desk">
    <div class="desk-header">
      <h1>前台服务系统</h1>
      <div class="header-tabs">
        <button
          :class="['tab-btn', { active: activeTab === 'checkin' }]"
          @click="activeTab = 'checkin'"
        >
          办理入住
        </button>
        <button
          :class="['tab-btn', { active: activeTab === 'checkout' }]"
          @click="activeTab = 'checkout'"
        >
          退房结账
        </button>
      </div>
    </div>

    <!-- 入住办理 -->
    <CheckInForm
      v-if="activeTab === 'checkin'"
      :available-rooms="availableRoomsForCheckIn"
      :check-in-records="checkInRecords"
      :on-check-in="handleCheckIn"
      @switch-to-room="handleSwitchToRoom"
    />

    <!-- 退房结账 -->
    <CheckOutForm
      v-if="activeTab === 'checkout'"
      :occupied-rooms="occupiedRooms"
      :all-rooms="allRooms"
      :check-in-records="checkInRecords"
      :on-checkout="handleCheckoutSubmit"
    />

    <!-- 历史账单 -->
    <BillHistory
      :bills="allBills"
      @view-bill="handleViewBill"
    />

    <!-- 账单显示 -->
    <BillDetail
      v-if="currentBill"
      :bill="currentBill"
      @print="handlePrintBill"
      @close="handleCloseBill"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { Bill, RoomState, CheckInRecord } from '../../types/index';
import { ACMode, FanSpeed } from '../../types/index';
import CheckInForm from './CheckInForm.vue';
import CheckOutForm from './CheckOutForm.vue';
import BillDetail from './BillDetail.vue';
import BillHistory from './BillHistory.vue';
import { showError } from '../../composables/useDialog';
import type { AvailableRoom } from '../../composables/useHvacService';

const props = defineProps<{
  availableRooms: AvailableRoom[];
  occupiedRooms: string[];
  checkInRecords: CheckInRecord[];
  allRooms: RoomState[];
  allBills: Bill[];
  onCheckIn: (roomId: string, mode: ACMode, guestName?: string, guestPhone?: string, idCard?: string, stayDays?: number, roomTemp?: number, targetTemp?: number, fanSpeed?: FanSpeed) => Promise<{ success: boolean; message: string; }>;
  onCheckout: (roomId: string) => Promise<Bill | null>;
}>();

const emit = defineEmits<{
  switchToRoom: [];
}>();

const activeTab = ref<'checkin' | 'checkout'>('checkin');
const currentBill = ref<Bill | null>(null);

const availableRoomsForCheckIn = computed(() => {
  // 过滤掉已入住的房间
  return props.availableRooms.filter(room => !props.occupiedRooms.includes(room.roomId));
});

const handleSwitchToRoom = () => {
  emit('switchToRoom');
};

const handleCheckIn = async (roomId: string, mode: ACMode, guestName?: string, guestPhone?: string, idCard?: string, stayDays?: number, roomTemp?: number, targetTemp?: number, fanSpeed?: FanSpeed) => {
  return await props.onCheckIn(roomId, mode, guestName, guestPhone, idCard, stayDays, roomTemp, targetTemp, fanSpeed);
};

const handleCheckoutSubmit = async (roomId: string) => {
  const bill = await props.onCheckout(roomId);
  if (bill) {
    currentBill.value = bill;
    // 退房成功后，自动切换到账单详情，方便前台查看
    await new Promise(resolve => setTimeout(resolve, 100));
    // 滚动到账单位置
    const billElement = document.querySelector('.bill-section');
    if (billElement) {
      billElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  } else {
    showError('退房结账失败，请检查房间是否已入住');
  }
};

const handleViewBill = (bill: Bill) => {
  currentBill.value = bill;
  // 滚动到账单位置
  setTimeout(() => {
    const billElement = document.querySelector('.bill-section');
    if (billElement) {
      billElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, 100);
};

const handleCloseBill = () => {
  currentBill.value = null;
};

const handlePrintBill = (bill: Bill) => {
  const printWindow = window.open('', '_blank');
  if (!printWindow) return;

  const billHtml = generateBillHTML(bill);
  printWindow.document.write(billHtml);
  printWindow.document.close();
  printWindow.print();
};

const generateBillHTML = (bill: Bill): string => {
  const formatDateTime = (timestamp: number) => new Date(timestamp).toLocaleString('zh-CN');
  // 格式化详单时间（支持字符串和数字格式）
  const formatTime = (timestamp: number | string) => {
    // 如果是字符串格式 "2025-12-09 01:04:57"，直接提取 MM-DD HH:MM:SS
    if (typeof timestamp === 'string') {
      const match = timestamp.match(/\d{4}-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
      if (match) {
        return `${match[1]}-${match[2]} ${match[3]}:${match[4]}:${match[5]}`;
      }
      return timestamp;
    }
    const date = new Date(timestamp);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${month}-${day} ${hours}:${minutes}:${seconds}`;
  };
  const formatDurationSeconds = (seconds: number) => {
    if (seconds === 0) return '0秒';
    return `${seconds}秒`;
  };

  // 计算入住天数
  const stayDays = bill.stayDays || Math.ceil((bill.checkOutTime - bill.checkInTime) / (1000 * 60 * 60 * 24)) || 1;
  const roomRate = bill.roomRate || 280;
  const roomCharge = bill.roomFee || (roomRate * stayDays);
  const deposit = bill.deposit || 200;
  const subtotal = roomCharge + bill.acCost;

  // 获取累计费用（直接使用后端返回的值）
  const getAccumulatedCost = (index: number) => {
    const record = bill.detailRecords[index];
    return record?.accumulatedCost ?? 0;
  };

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>账单 - 房间 ${bill.roomId}</title>
      <style>
        body { font-family: 'Courier New', monospace; padding: 20px; max-width: 800px; margin: 0 auto; }
        .header { text-align: center; border-bottom: 3px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .section { margin-bottom: 24px; padding: 16px; border: 1px solid #ddd; border-radius: 8px; }
        .section-title { font-size: 16px; font-weight: bold; margin-bottom: 12px; border-bottom: 2px solid #333; padding-bottom: 8px; }
        .row { display: flex; justify-content: space-between; padding: 6px 0; }
        .row.bold { font-weight: bold; }
        .charge-row { display: flex; justify-content: space-between; padding: 8px 12px; background: #f9f9f9; margin: 4px 0; border-radius: 4px; }
        .subtotal { font-size: 16px; font-weight: bold; border-top: 2px solid #333; margin-top: 12px; padding-top: 12px; }
        .deposit { color: #10b981; font-weight: bold; }
        .final { font-size: 20px; font-weight: bold; background: #333; color: white; padding: 16px; margin-top: 16px; border-radius: 8px; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 12px; }
        th, td { border: 1px solid #333; padding: 8px; text-align: left; font-size: 12px; }
        th { background: #f0f0f0; font-weight: bold; }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>🏨 酒店住宿账单</h1>
        <p>Hotel Billing Statement</p>
      </div>
      
      ${bill.guestName || bill.guestPhone ? `
      <div class="section">
        <div class="section-title">👤 客户信息</div>
        ${bill.guestName ? `<div class="row"><span>客户姓名：</span><span>${bill.guestName}</span></div>` : ''}
        ${bill.guestPhone ? `<div class="row"><span>联系电话：</span><span>${bill.guestPhone}</span></div>` : ''}
      </div>
      ` : ''}
      
      <div class="section">
        <div class="section-title">🏠 入住信息</div>
        <div class="row"><span>房间号：</span><span>${bill.roomId}</span></div>
        <div class="row"><span>入住时间：</span><span>${formatDateTime(bill.checkInTime)}</span></div>
        <div class="row"><span>退房时间：</span><span>${formatDateTime(bill.checkOutTime)}</span></div>
        <div class="row bold"><span>入住天数：</span><span>${stayDays} 天</span></div>
      </div>
      
      <div class="section">
        <div class="section-title">💰 费用明细</div>
        <div class="charge-row">
          <span>房费</span>
          <span>¥${roomRate}/天 × ${stayDays}天</span>
          <span>¥${roomCharge.toFixed(2)}</span>
        </div>
        <div class="charge-row">
          <span>空调使用费</span>
          <span>¥1/度（调温计费）</span>
          <span>¥${bill.acCost.toFixed(2)}</span>
        </div>
        <div style="padding: 8px; background: #f5f5f5; border-left: 3px solid #666; margin: 8px 0; font-size: 11px; color: #666;">
          💡 实际费用以系统计算为准
        </div>
        <div class="row subtotal">
          <span>小计：</span>
          <span>¥${subtotal.toFixed(2)}</span>
        </div>
      </div>
      
      <div class="section" style="background: #f9f9f9; border: 2px solid #ccc;">
        <div class="section-title">🔒 押金处理说明</div>
        <div style="line-height: 1.8; color: #333;">
          • 入住时收取押金：¥${deposit.toFixed(2)}<br>
          • 退房时原路退还，与住宿费用分离计算<br>
          • 押金不包含在应付金额中
        </div>
      </div>
      
      <div class="final">
        应付金额（不含押金）：¥${subtotal.toFixed(2)}
      </div>
      
      <div class="section">
        <div class="section-title">📋 空调使用详单（共 ${bill.detailRecords.length} 条请求记录）</div>
        <table>
          <thead>
            <tr>
              <th style="width: 40px;">序号</th>
              <th style="width: 120px;">请求时间</th>
              <th style="width: 100px;">操作类型</th>
              <th style="width: 60px;">风速</th>
              <th style="width: 80px;">目标温度</th>
              <th style="width: 80px;">当前温度</th>
              <th style="width: 80px;">服务时长</th>
              <th style="width: 80px;">当前费用</th>
              <th style="width: 80px;">累计费用</th>
            </tr>
          </thead>
          <tbody>
            ${bill.detailRecords.map((record, index) => `
              <tr>
                <td style="text-align: center;">${index + 1}</td>
                <td style="font-family: 'Courier New', monospace;">${formatTime(record.timestamp)}</td>
                <td>${record.action}</td>
                <td>${record.fanSpeed ? (record.fanSpeed === 'LOW' ? '低风' : record.fanSpeed === 'MEDIUM' ? '中风' : record.fanSpeed === 'HIGH' ? '高风' : record.fanSpeed) : '-'}</td>
                <td>${record.targetTemp ? record.targetTemp.toFixed(1) + '°C' : '-'}</td>
                <td>${record.currentTemp.toFixed(1)}°C</td>
                <td style="font-family: 'Courier New', monospace;">${formatDurationSeconds(record.duration)}</td>
                <td style="font-weight: bold;">¥${record.cost.toFixed(2)}</td>
                <td style="font-weight: bold;">¥${getAccumulatedCost(index).toFixed(2)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      
      <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px;">
        <p>感谢您的入住！欢迎再次光临</p>
        <p>打印时间：${new Date().toLocaleString('zh-CN')}</p>
      </div>
    </body>
    </html>
  `;
};
</script>

<style scoped>
.front-desk {
  max-width: 1200px;
  margin: 0 auto;
}

.desk-header {
  margin-bottom: 24px;
  padding: 24px;
  background: white;
  border-radius: 12px;
  border: 2px solid #f0f4f8;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.desk-header h1 {
  margin: 0;
  color: #1e293b;
  font-size: 22px;
  font-weight: 600;
}

.header-tabs {
  display: flex;
  gap: 12px;
}

.tab-btn {
  padding: 10px 24px;
  background: #f8fafc;
  color: #64748b;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: #e0f2fe;
  border-color: #067ef5;
  color: #067ef5;
}

.tab-btn.active {
  background: linear-gradient(135deg, #067ef5 0%, #0369a1 100%);
  border-color: #067ef5;
  color: white;
  box-shadow: 0 4px 12px rgba(6, 126, 245, 0.3);
  transform: translateY(-1px);
}
</style>
