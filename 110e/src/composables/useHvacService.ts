import { ref, computed, onMounted, onUnmounted } from 'vue';
import { createHvacService } from '../services/ApiAdapter';
import { POLLING_CONFIG, isRoomActive } from '../config/polling';
import type { Bill } from '../types';
import { frontDeskApi } from '../api/hvac';

// 可用房间接口定义
export interface AvailableRoom {
  roomId: string;
  pricePerNight: number;
  isOccupied: boolean;
}

export function useHvacService() {
  // 创建服务实例
  const hvacService = createHvacService();

  // 强制刷新标记
  const refreshKey = ref(0);

  // 历史账单数据（响应式）
  const billsData = ref<Bill[]>([]);

  // 可用房间数据（响应式）
  const availableRoomsData = ref<AvailableRoom[]>([]);

  // 更新间隔定时器
  let updateInterval: ReturnType<typeof setInterval> | null = null;
  const isPageVisible = ref(true); // 页面可见性状态
  let visibilityHandler: (() => void) | null = null; // 存储事件监听器引用

  // 加载历史账单
  const loadBillHistory = async () => {
    try {
      const bills = await hvacService.getBillHistory();
      billsData.value = bills;
    } catch (error) {
      console.error('加载历史账单失败:', error);
      billsData.value = [];
    }
  };

  // 加载可用房间列表
  const loadAvailableRooms = async () => {
    try {
      const rooms = await frontDeskApi.getAvailableRooms();
      availableRoomsData.value = rooms;
    } catch (error) {
      console.error('加载可用房间失败:', error);
      availableRoomsData.value = [];
    }
  };

  // 初始化
  onMounted(() => {
    // 注册状态变化回调
    if (hvacService.onStateChange) {
      hvacService.onStateChange(() => {
        refreshKey.value++;
        // 状态变化时不刷新历史账单，只在退房时刷新
      });
    }

    // 页面可见性监听（优化轮询）
    visibilityHandler = () => {
      isPageVisible.value = !document.hidden;
      if (isPageVisible.value && hvacService.refreshRoomStates) {
        // 页面重新可见时，立即刷新一次
        hvacService.refreshRoomStates();
      }
    };
    document.addEventListener('visibilitychange', visibilityHandler);

    // 初始加载历史账单和可用房间
    loadBillHistory();
    loadAvailableRooms();

    // 启动智能轮询策略
    let pollInterval = POLLING_CONFIG.ACTIVE_INTERVAL;

    const smartPoll = async () => {
      try {
        // 只在页面可见时才刷新（如果启用了可见性检测）
        if (!POLLING_CONFIG.ENABLE_VISIBILITY_DETECTION || isPageVisible.value) {
          // 同时刷新房间状态、队列和可用房间
          await Promise.all([
            hvacService.refreshRoomStates?.() ?? Promise.resolve(),
            hvacService.refreshQueues?.() ?? Promise.resolve(),
            loadAvailableRooms()
          ]);
        }

        // 根据配置和房间状态动态调整轮询间隔
        if (POLLING_CONFIG.ENABLE_SMART_POLLING) {
          const rooms = hvacService.getAllRoomStates();
          const hasActiveRooms = rooms.some(r => isRoomActive(r));

          // 根据页面可见性和房间状态动态调整
          if (POLLING_CONFIG.ENABLE_VISIBILITY_DETECTION && !isPageVisible.value) {
            pollInterval = POLLING_CONFIG.HIDDEN_INTERVAL; // 页面隐藏
          } else {
            pollInterval = hasActiveRooms
              ? POLLING_CONFIG.ACTIVE_INTERVAL  // 有活跃房间
              : POLLING_CONFIG.IDLE_INTERVAL;   // 无活跃房间
          }
        } else {
          // 禁用智能轮询时使用固定间隔
          pollInterval = POLLING_CONFIG.ACTIVE_INTERVAL;
        }

        // 清除旧定时器，设置新间隔
        if (updateInterval) {
          clearInterval(updateInterval);
        }
        updateInterval = setInterval(smartPoll, pollInterval);
      } catch (error) {
        console.error('定时刷新失败:', error);
      }
    };

    // 首次执行
    smartPoll();
  });

  // 清理
  onUnmounted(() => {
    if (updateInterval) {
      clearInterval(updateInterval);
    }
    // 移除页面可见性监听器
    if (visibilityHandler) {
      document.removeEventListener('visibilitychange', visibilityHandler);
    }
    hvacService.destroy();
  });

  // 计算属性
  const allRooms = computed(() => {
    void refreshKey.value; // 依赖刷新标记
    return hvacService.getAllRoomStates();
  });

  const serviceQueue = computed(() => {
    void refreshKey.value;
    return hvacService.getServiceQueue();
  });

  const waitingQueue = computed(() => {
    void refreshKey.value;
    return hvacService.getWaitingQueue();
  });

  const allBills = computed(() => {
    // 直接返回响应式账单数据
    return billsData.value;
  });

  const occupiedRooms = computed(() => {
    void refreshKey.value;
    return hvacService.getOccupiedRooms();
  });

  const checkInRecords = computed(() => {
    void refreshKey.value;
    return hvacService.getOccupiedRooms().map(roomId => {
      const record = hvacService.getCheckInRecord(roomId);
      return record;
    }).filter(record => record !== null);
  });

  const availableRooms = computed(() => {
    // 返回可用房间数据
    return availableRoomsData.value;
  });

  return {
    hvacService,
    refreshKey,
    allRooms,
    serviceQueue,
    waitingQueue,
    allBills,
    occupiedRooms,
    checkInRecords,
    availableRooms
  };
}

