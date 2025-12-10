<template>
  <div class="manager-statistics">
    <div class="stats-header">
      <h1>统计报表系统</h1>
    </div>

    <!-- 时间范围选择 -->
    <TimeRangeSelector
      v-model:start-time="startTimeInput"
      v-model:end-time="endTimeInput"
      @generate="generateReport"
      @select-today="selectToday"
      @select-week="selectThisWeek"
      @select-month="selectThisMonth"
      @select-all="selectAll"
    />

    <!-- 统计报表 -->
    <div v-if="report" class="report-section">
      <div class="report-header">
        <h2>统计报表</h2>
        <button class="btn-print" @click="printReport">
          打印报表
        </button>
      </div>

      <!-- 总体统计 -->
      <StatisticsOverview
        :total-rooms="report.totalRooms"
        :total-requests="report.totalServiceRequests"
        :total-duration="totalServiceDuration"
        :total-cost="report.totalCost"
      />

      <!-- 风速使用分布 -->
      <FanSpeedChart
        :high="report.fanSpeedDistribution.high"
        :medium="report.fanSpeedDistribution.medium"
        :low="report.fanSpeedDistribution.low"
      />

      <!-- 房间明细统计 -->
      <RoomDetailsTable :room-stats="report.roomStatistics" />

      <!-- 时间信息 -->
      <div class="report-footer">
        <div class="time-range-info">
          <strong>统计时间范围：</strong>
          <span>{{ formatDateTime(report.startTime) }}</span>
          <span> 至 </span>
          <span>{{ formatDateTime(report.endTime) }}</span>
        </div>
        <div class="generate-time">
          生成时间：{{ formatDateTime(Date.now()) }}
        </div>
      </div>
    </div>

    <div v-else class="no-report">
      <p>请选择时间范围并生成报表</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { StatisticsReport } from '../../types/index';
import TimeRangeSelector from './TimeRangeSelector.vue';
import StatisticsOverview from './StatisticsOverview.vue';
import FanSpeedChart from './FanSpeedChart.vue';
import RoomDetailsTable from './RoomDetailsTable.vue';
import { showWarning } from '../../composables/useDialog';

const props = defineProps<{
  onGenerateReport: (startTime: number, endTime: number) => Promise<StatisticsReport>;
}>();

const startTimeInput = ref('');
const endTimeInput = ref('');
const report = ref<StatisticsReport | null>(null);

// 计算总服务时长（从房间统计中累加）
const totalServiceDuration = computed(() => {
  if (!report.value || !report.value.roomStatistics) return 0;
  return report.value.roomStatistics.reduce((sum, stat) => sum + (stat.totalServiceDuration || 0), 0);
});

const selectToday = () => {
  const now = new Date();
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);

  startTimeInput.value = formatInputDateTime(startOfDay);
  endTimeInput.value = formatInputDateTime(endOfDay);
};

const selectThisWeek = () => {
  const now = new Date();
  const dayOfWeek = now.getDay();
  const startOfWeek = new Date(now);
  startOfWeek.setDate(now.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
  startOfWeek.setHours(0, 0, 0, 0);

  const endOfWeek = new Date(startOfWeek);
  endOfWeek.setDate(startOfWeek.getDate() + 6);
  endOfWeek.setHours(23, 59, 59);

  startTimeInput.value = formatInputDateTime(startOfWeek);
  endTimeInput.value = formatInputDateTime(endOfWeek);
};

const selectThisMonth = () => {
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59);

  startTimeInput.value = formatInputDateTime(startOfMonth);
  endTimeInput.value = formatInputDateTime(endOfMonth);
};

const selectAll = () => {
  const now = new Date();
  // 限制最早时间为30天前，避免查询过多数据
  const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

  startTimeInput.value = formatInputDateTime(thirtyDaysAgo);
  endTimeInput.value = formatInputDateTime(now);
};

const generateReport = async () => {
  if (!startTimeInput.value || !endTimeInput.value) {
    showWarning('请选择时间范围');
    return;
  }

  const startTime = new Date(startTimeInput.value).getTime();
  const endTime = new Date(endTimeInput.value).getTime();

  if (startTime >= endTime) {
    showWarning('结束时间必须晚于开始时间');
    return;
  }

  report.value = await props.onGenerateReport(startTime, endTime);
};

const printReport = () => {
  if (!report.value) return;

  const printWindow = window.open('', '_blank');
  if (!printWindow) return;

  const reportHtml = generatePrintHTML(report.value);
  printWindow.document.write(reportHtml);
  printWindow.document.close();
  printWindow.print();
};

const generatePrintHTML = (rep: StatisticsReport): string => {
  const getFanSpeedText = (speed: string) => {
    const map: Record<string, string> = { low: '低风', medium: '中风', high: '高风', LOW: '低风', MEDIUM: '中风', HIGH: '高风' };
    return map[speed] || '未知';
  };

  // 格式化时长
  const formatDurationPrint = (seconds: number): string => {
    if (!seconds || seconds === 0) return '0秒';
    if (seconds < 60) return `${seconds}秒`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`;
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}时${mins}分`;
  };

  // 计算总服务时长
  const totalDuration = rep.roomStatistics.reduce((sum, stat) => sum + (stat.totalServiceDuration || 0), 0);

  // 计算平均费用/房间
  const avgCostPerRoom = rep.totalRooms > 0 ? rep.totalCost / rep.totalRooms : 0;

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>空调系统统计报表</title>
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          font-family: 'SimSun', 'Songti SC', serif;
          padding: 40px;
          max-width: 800px;
          margin: 0 auto;
          color: #000;
          line-height: 1.6;
        }
        .header {
          text-align: center;
          padding-bottom: 20px;
          margin-bottom: 30px;
          border-bottom: 2px solid #000;
        }
        .header h1 {
          font-size: 24px;
          font-weight: bold;
          letter-spacing: 4px;
        }
        .header .subtitle {
          font-size: 12px;
          color: #666;
          margin-top: 8px;
        }
        .section {
          margin-bottom: 24px;
        }
        .section-title {
          font-size: 14px;
          font-weight: bold;
          padding: 8px 0;
          border-bottom: 1px solid #000;
          margin-bottom: 12px;
        }
        .summary-grid {
          display: table;
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 20px;
        }
        .summary-row {
          display: table-row;
        }
        .summary-cell {
          display: table-cell;
          width: 20%;
          padding: 12px 8px;
          text-align: center;
          border: 1px solid #333;
        }
        .summary-cell .value {
          font-size: 20px;
          font-weight: bold;
          margin-bottom: 4px;
        }
        .summary-cell .label {
          font-size: 11px;
          color: #333;
        }
        .fan-speed-row {
          padding: 12px;
          background: #f5f5f5;
          border: 1px solid #333;
          text-align: center;
          font-size: 13px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12px;
        }
        th, td {
          border: 1px solid #333;
          padding: 8px 6px;
          text-align: center;
        }
        th {
          background: #e0e0e0;
          font-weight: bold;
          font-size: 11px;
        }
        td {
          font-size: 12px;
        }
        .room-id { font-weight: bold; }
        .cost { font-weight: bold; }
        .footer {
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid #999;
          text-align: center;
          font-size: 11px;
          color: #666;
        }
        .footer p { margin: 4px 0; }
        @media print {
          body { padding: 20px; }
          .header { page-break-after: avoid; }
          table { page-break-inside: avoid; }
        }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>空调系统统计报表</h1>
        <div class="subtitle">HVAC System Statistics Report</div>
      </div>

      <div class="section">
        <div class="section-title">一、总体统计</div>
        <div class="summary-grid">
          <div class="summary-row">
            <div class="summary-cell">
              <div class="value">${rep.totalRooms}</div>
              <div class="label">使用房间数</div>
            </div>
            <div class="summary-cell">
              <div class="value">${rep.totalServiceRequests}</div>
              <div class="label">服务请求次数</div>
            </div>
            <div class="summary-cell">
              <div class="value">${formatDurationPrint(totalDuration)}</div>
              <div class="label">总服务时长</div>
            </div>
            <div class="summary-cell">
              <div class="value">¥${rep.totalCost.toFixed(2)}</div>
              <div class="label">总费用</div>
            </div>
            <div class="summary-cell">
              <div class="value">¥${avgCostPerRoom.toFixed(2)}</div>
              <div class="label">平均费用/房间</div>
            </div>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">二、风速使用统计</div>
        <div class="fan-speed-row">
          高风：<strong>${rep.fanSpeedDistribution.high}</strong> 次 &nbsp;&nbsp;|&nbsp;&nbsp;
          中风：<strong>${rep.fanSpeedDistribution.medium}</strong> 次 &nbsp;&nbsp;|&nbsp;&nbsp;
          低风：<strong>${rep.fanSpeedDistribution.low}</strong> 次
        </div>
      </div>

      <div class="section">
        <div class="section-title">三、房间明细统计</div>
        <table>
          <thead>
            <tr>
              <th style="width: 60px;">房间号</th>
              <th style="width: 70px;">服务次数</th>
              <th style="width: 90px;">服务时长</th>
              <th style="width: 90px;">总费用(元)</th>
              <th style="width: 70px;">平均温度</th>
              <th style="width: 70px;">常用风速</th>
            </tr>
          </thead>
          <tbody>
            ${rep.roomStatistics.map(stat => `
              <tr>
                <td class="room-id">${stat.roomId}</td>
                <td>${stat.serviceCount}</td>
                <td>${formatDurationPrint(stat.totalServiceDuration || 0)}</td>
                <td class="cost">¥${stat.totalCost.toFixed(2)}</td>
                <td>${stat.averageTemp.toFixed(1)}°C</td>
                <td>${getFanSpeedText(stat.mostUsedFanSpeed)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>

      <div class="footer">
        <p>统计时间范围：${formatDateTime(rep.startTime)} 至 ${formatDateTime(rep.endTime)}</p>
        <p>报表生成时间：${formatDateTime(Date.now())}</p>
      </div>
    </body>
    </html>
  `;
};

const formatDateTime = (timestamp: number): string => {
  return new Date(timestamp).toLocaleString('zh-CN');
};

const formatInputDateTime = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
};
</script>

<style scoped>
.manager-statistics {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 16px;
}

.stats-header {
  margin-bottom: 24px;
  padding: 32px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 12px;
  border: 2px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  text-align: center;
}

.stats-header h1 {
  margin: 0;
  color: #1e293b;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.report-section {
  margin-bottom: 24px;
  padding: 32px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 12px;
  border: 2px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding-bottom: 20px;
  border-bottom: 2px solid #e2e8f0;
}

h2 {
  margin: 0;
  color: #1e293b;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.btn-print {
  padding: 12px 28px;
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 8px rgba(5, 150, 105, 0.2);
}

.btn-print:hover {
  background: linear-gradient(135deg, #047857 0%, #065f46 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(5, 150, 105, 0.3);
}

.btn-print:active {
  transform: translateY(0);
}

.report-footer {
  margin-top: 40px;
  padding: 24px;
  background: #f8fafc;
  border-radius: 8px;
  border: 2px solid #e2e8f0;
  text-align: center;
  color: #64748b;
}

.time-range-info {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
}

.time-range-info strong {
  color: #475569;
}

.time-range-info span {
  color: #067ef5;
  font-weight: 600;
}

.no-report {
  text-align: center;
  padding: 80px 40px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 12px;
  border: 2px dashed #cbd5e1;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  color: #94a3b8;
  font-size: 16px;
  font-weight: 500;
}

.generate-time {
  font-size: 13px;
  color: #94a3b8;
}
</style>
