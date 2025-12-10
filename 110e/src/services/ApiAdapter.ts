/**
 * API 适配器 - 后端 API 服务
 */
import api from '../api/hvac';
import type {
  RoomState,
  DetailRecord,
  Bill,
  CheckInRecord,
  StatisticsReport,
  ServiceObject,
  WaitingObject
} from '../types/index';
import { ACMode, FanSpeed, RoomStatus } from '../types/index';
import { ROOM_PRICES, DEFAULT_TEMP } from '../constants/index';

/**
 * HVAC服务接口定义
 */
export interface IHvacService {
  // 前台接口
  checkIn(roomId: string, mode: ACMode, guestName?: string, guestPhone?: string, idCard?: string, stayDays?: number, roomTemp?: number, targetTemp?: number, fanSpeed?: FanSpeed): Promise<{ success: boolean; message: string }>;
  checkOut(roomId: string): Promise<Bill>;
  getDetailRecords(roomId: string): Promise<DetailRecord[]>;
  getBill(roomId: string): Promise<Bill | null>;
  getBillHistory(): Promise<Bill[]>;
  getCheckInRecords(): Promise<CheckInRecord[]>;
  getCheckInRecord(roomId: string): CheckInRecord | null;
  getOccupiedRooms(): string[];

  // 房间接口
  getRoomState(roomId: string): RoomState | null;
  getAllRoomStates(): RoomState[];
  turnOn(roomId: string): Promise<void>;
  turnOff(roomId: string): Promise<void>;
  sendRequest(roomId: string, targetTemp: number, fanSpeed: FanSpeed, mode: ACMode): Promise<void>;
  setMode(roomId: string, mode: ACMode): Promise<void>;

  // 管理员接口
  getServiceQueue(): ServiceObject[];
  getWaitingQueue(): WaitingObject[];
  turnOffAll(): Promise<void>;
  turnOnAll(): Promise<void>;
  clearWaitingQueue(): Promise<void>;

  // 经理接口
  generateStatistics(startTime: number, endTime: number, roomId?: string): Promise<StatisticsReport>;

  // 系统方法
  refreshRoomStates(): Promise<void>;      // 刷新房间状态
  refreshQueues(): Promise<void>;          // 刷新队列
  refreshCheckInRecords(): Promise<void>;  // 刷新入住记录
  refreshBillHistory(): Promise<void>;     // 刷新历史账单
  onStateChange(callback: () => void): void;
  destroy(): void;
}

/**
 * 后端API适配器
 */
class HvacService implements IHvacService {
  // 缓存数据
  private roomStatesCache: Map<string, RoomState> = new Map();
  private serviceQueueCache: ServiceObject[] = [];
  private waitingQueueCache: WaitingObject[] = [];
  private checkInRecordsCache: Map<string, CheckInRecord> = new Map();
  private billHistoryCache: Bill[] = [];
  // 记录房间的基础信息（酒店接口返回）
  private roomBasicsCache: Map<string, any> = new Map();
  private stateChangeCallbacks: Set<() => void> = new Set();

  constructor() {
    // 初始化时加载基础数据
    this.refreshRoomStates();
    this.refreshCheckInRecords();
    this.refreshBillHistory();
    this.refreshQueues();
  }

  // ==================== 辅助方法 ====================

  private mapRoomState(roomId: string, basic: any, state: any): RoomState {
    const mode = (state?.ac_mode || state?.mode || basic?.acMode || ACMode.COOLING) as ACMode;
    const currentTemp = Number(
      state?.currentTemp ??
      state?.current_temp ??
      basic?.currentTemp ??
      basic?.current_temp ??
      DEFAULT_TEMP
    );
    const targetTemp = Number(
      state?.targetTemp ??
      state?.target_temp ??
      basic?.targetTemp ??
      basic?.target_temp ??
      DEFAULT_TEMP
    );
    const fanSpeed = (state?.fanSpeed || state?.fan_speed || basic?.fanSpeed || FanSpeed.MEDIUM) as FanSpeed;
    const queueState = (state?.state || state?.queueState || state?.queue_state || '').toString().toUpperCase();

    let status: RoomStatus = RoomStatus.OFF;
    if (queueState === 'SERVING') {
      status = RoomStatus.SERVING;
    } else if (queueState === 'WAITING') {
      status = RoomStatus.WAITING;
    } else if (queueState === 'PAUSED') {
      status = RoomStatus.TARGET_REACHED;
    } else if (basic?.status && basic.status !== 'AVAILABLE') {
      status = RoomStatus.STANDBY;
    }

    const totalCost = Number(state?.total_cost ?? 0) + Number(state?.ac_fee ?? 0);

    return {
      roomId,
      pricePerNight: ROOM_PRICES[roomId] ?? 100,
      isOn: Boolean(state?.ac_on ?? basic?.acOn ?? false),
      mode,
      currentTemp,
      initialTemp: Number(basic?.defaultTemp ?? basic?.default_temp ?? DEFAULT_TEMP),
      targetTemp,
      fanSpeed,
      status,
      totalCost,
      lastUpdateTime: Date.now(),
      serviceStartTime: null,
      detailRecords: []
    };
  }

  private mapServiceObject(entry: any): ServiceObject {
    const roomId = String(entry?.roomId ?? '');
    const cached = roomId ? this.roomStatesCache.get(roomId) : null;
    const durationSeconds = Math.round(entry?.servingSeconds ?? entry?.totalSeconds ?? 0);
    const startTime = entry?.servingTime ? new Date(entry.servingTime).getTime() : Date.now();

    return {
      id: `${roomId}-${Date.now()}`,
      roomId,
      fanSpeed: (entry?.fanSpeed ?? cached?.fanSpeed ?? FanSpeed.MEDIUM) as FanSpeed,
      targetTemp: cached?.targetTemp ?? entry?.targetTemp ?? DEFAULT_TEMP,
      currentTemp: cached?.currentTemp ?? entry?.currentTemp ?? DEFAULT_TEMP,
      serviceStartTime: startTime,
      serviceDuration: durationSeconds,
      cost: cached?.totalCost ?? 0
    };
  }

  private mapWaitingObject(entry: any): WaitingObject {
    const roomId = String(entry?.roomId ?? '');
    const cached = roomId ? this.roomStatesCache.get(roomId) : null;

    return {
      roomId,
      fanSpeed: (entry?.fanSpeed ?? cached?.fanSpeed ?? FanSpeed.MEDIUM) as FanSpeed,
      targetTemp: cached?.targetTemp ?? entry?.targetTemp ?? DEFAULT_TEMP,
      currentTemp: cached?.currentTemp ?? entry?.currentTemp ?? DEFAULT_TEMP,
      waitStartTime: entry?.waitingTime ? new Date(entry.waitingTime).getTime() : 0,
      waitDuration: Math.round(entry?.waitingSeconds ?? 0),
      assignedWaitTime: Math.round(entry?.assignedWaitTime ?? 0)
    };
  }

  private mapDetailRecords(records: any[]): DetailRecord[] {
    if (!records || records.length === 0) return [];
    let accumulated = 0;
    return records.map((rec) => {
      const cost = Number(rec?.fee ?? rec?.acFee ?? rec?.cost ?? 0);
      accumulated += cost;
      return {
        timestamp: rec?.startTime || rec?.requestTime || new Date().toISOString(),
        action: rec?.type || '空调服务',
        fanSpeed: rec?.fanSpeed as FanSpeed,
        targetTemp: rec?.targetTemp,
        currentTemp: Number(rec?.currentTemp ?? 0),
        cost,
        accumulatedCost: accumulated,
        duration: Math.round((rec?.duration ?? 0) * 60)
      };
    });
  }

  private mapCheckoutResponseToBill(resp: any): Bill {
    const billInfo = resp?.bill || {};
    const detailBill = Array.isArray(resp?.detailBill) ? resp.detailBill : [];
    const roomId = String(billInfo.roomId ?? '');
    const checkInTime = billInfo.checkinTime ? new Date(billInfo.checkinTime).getTime() : Date.now();
    const checkOutTime = billInfo.checkoutTime ? new Date(billInfo.checkoutTime).getTime() : Date.now();

    const detailRecords = this.mapDetailRecords(detailBill);
    const acCost = Number(billInfo.acFee ?? 0);
    const roomFee = Number(billInfo.roomFee ?? 0);

    return {
      roomId,
      checkInTime,
      checkOutTime,
      roomFee,
      acCost,
      totalCost: roomFee + acCost,
      totalServiceDuration: detailRecords.reduce((sum, r) => sum + (r.duration || 0), 0),
      detailRecords,
      roomRate: ROOM_PRICES[roomId] ?? 100,
      stayDays: billInfo.duration ? Number(billInfo.duration) : undefined,
      guestName: resp?.customer?.name,
      guestPhone: resp?.customer?.phoneNumber
    };
  }

  // ==================== 刷新方法 ====================

  async refreshRoomStates(): Promise<void> {
    try {
      const [roomBasics, adminStates] = await Promise.all([
        api.frontDesk.getAllRooms(),
        api.admin.getAllRoomStates()
      ]);

      this.roomBasicsCache.clear();
      roomBasics?.forEach((room: any) => {
        const rid = String(room.id ?? room.roomId ?? room.room_id ?? '');
        if (rid) {
          this.roomBasicsCache.set(rid, room);
        }
      });

      const mappedStates: Map<string, RoomState> = new Map();

      adminStates?.forEach((state: any) => {
        const rid = String(state.room_id ?? state.id ?? state.roomId ?? '');
        if (!rid) return;
        const basic = this.roomBasicsCache.get(rid);
        mappedStates.set(rid, this.mapRoomState(rid, basic, state));
      });

      // 补充没有出现在调度状态里的房间
      roomBasics?.forEach((basic: any) => {
        const rid = String(basic.id ?? basic.roomId ?? basic.room_id ?? '');
        if (rid && !mappedStates.has(rid)) {
          mappedStates.set(rid, this.mapRoomState(rid, basic, null));
        }
      });

      this.roomStatesCache = mappedStates;
      this.stateChangeCallbacks.forEach((callback: () => void) => callback());
    } catch (error) {
      console.error('刷新房间状态失败:', error);
    }
  }

  async refreshQueues(): Promise<void> {
    try {
      const [serviceQueue, waitingQueue] = await Promise.all([
        api.admin.getServiceQueue(),
        api.admin.getWaitingQueue()
      ]);
      this.serviceQueueCache = (serviceQueue || []).map((entry: any) => this.mapServiceObject(entry));
      this.waitingQueueCache = (waitingQueue || []).map((entry: any) => this.mapWaitingObject(entry));
      this.stateChangeCallbacks.forEach((callback: () => void) => callback());
    } catch (error) {
      console.error('刷新队列失败:', error);
    }
  }

  async refreshCheckInRecords(): Promise<void> {
    try {
      const checkInRecords = await api.frontDesk.getCheckInRecords();
      this.checkInRecordsCache.clear();

      // 只缓存未退房的记录，并补充本地可用信息
      checkInRecords
        .filter(record => !record.checkedOut)
        .forEach((record) => {
          const rid = record.roomId;
          const cachedRoom = this.roomStatesCache.get(rid);
          this.checkInRecordsCache.set(rid, {
            ...record,
            mode: record.mode || cachedRoom?.mode || ACMode.COOLING,
            checkInTime: record.checkInTime || Date.now(),
            guestName: record.guestName,
            guestPhone: record.guestPhone
          });
        });

      this.stateChangeCallbacks.forEach((callback: () => void) => callback());
    } catch (error) {
      console.error('刷新入住记录失败:', error);
    }
  }

  async refreshBillHistory(): Promise<void> {
    try {
      const bills = await api.frontDesk.getAllBills();
      if (bills && bills.length > 0) {
        this.billHistoryCache = bills;
      }
      this.stateChangeCallbacks.forEach((callback: () => void) => callback());
    } catch (error) {
      console.error('刷新历史账单失败:', error);
    }
  }

  // ==================== 前台接口 ====================

  async checkIn(roomId: string, mode: ACMode, guestName?: string, guestPhone?: string, idCard?: string, stayDays?: number, roomTemp?: number, targetTemp?: number, fanSpeed?: FanSpeed): Promise<{ success: boolean; message: string }> {
    try {
      await api.frontDesk.checkIn(
        roomId,
        guestName || '未提供',
        guestPhone || '00000000000',
        idCard || '000000000000000000',
        stayDays || 1,
        mode,
        roomTemp ?? 25,
        targetTemp ?? 25,
        fanSpeed || FanSpeed.MEDIUM
      );
      await Promise.all([this.refreshRoomStates(), this.refreshCheckInRecords()]);
      return { success: true, message: `房间 ${roomId} 入住办理成功` };
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } }; message?: string };
      return { success: false, message: err.response?.data?.message || err.message || '入住失败' };
    }
  }

  async checkOut(roomId: string): Promise<Bill> {
    const resp = await api.frontDesk.checkOut(roomId);
    const bill = this.mapCheckoutResponseToBill(resp);
    // 退房成功后，更新缓存
    this.billHistoryCache.unshift(bill);
    this.checkInRecordsCache.delete(roomId);
    await Promise.all([this.refreshRoomStates(), this.refreshQueues()]);
    return bill;
  }

  async getDetailRecords(roomId: string): Promise<DetailRecord[]> {
    const records = await api.frontDesk.getDetailRecords(roomId);
    return this.mapDetailRecords(records || []);
  }

  async getBill(roomId: string): Promise<Bill | null> {
    try {
      const bill = await api.frontDesk.getBill(roomId);
      return bill;
    } catch {
      return null;
    }
  }

  async getBillHistory(): Promise<Bill[]> {
    // 如果缓存为空，先刷新一次
    if (this.billHistoryCache.length === 0) {
      await this.refreshBillHistory();
    }
    return this.billHistoryCache;
  }

  async getCheckInRecords(): Promise<CheckInRecord[]> {
    return Array.from(this.checkInRecordsCache.values());
  }

  getCheckInRecord(roomId: string): CheckInRecord | null {
    return this.checkInRecordsCache.get(roomId) || null;
  }

  getOccupiedRooms(): string[] {
    const occupied = new Set<string>(Array.from(this.checkInRecordsCache.keys()));
    // 兜底：根据房间基础状态判断
    this.roomBasicsCache.forEach((room: any, rid: string) => {
      if (room.status && room.status !== 'AVAILABLE') {
        occupied.add(rid);
      }
    });
    return Array.from(occupied);
  }

  // ==================== 房间接口 ====================

  getRoomState(roomId: string): RoomState | null {
    return this.roomStatesCache.get(roomId) || null;
  }

  getAllRoomStates(): RoomState[] {
    return Array.from(this.roomStatesCache.values());
  }

  async turnOn(roomId: string): Promise<void> {
    try {
      await api.room.turnOn(roomId);
      await this.refreshRoomStates();

      const room = this.roomStatesCache.get(roomId);
      if (room) {
        await api.room.sendRequest(roomId, room.targetTemp, room.fanSpeed, room.mode);
        await this.refreshRoomStates();
        // 开机后立即刷新队列，确保队列状态更新
        await this.refreshQueues();
      }
    } catch (error) {
      console.error('开机失败:', error);
      throw error;
    }
  }

  async turnOff(roomId: string): Promise<void> {
    try {
      await api.room.turnOff(roomId);
      await this.refreshRoomStates();
      // 关机后立即刷新队列，确保队列状态更新
      await this.refreshQueues();
    } catch (error) {
      console.error('关机失败:', error);
      throw error;
    }
  }

  async sendRequest(roomId: string, targetTemp: number, fanSpeed: FanSpeed, mode: ACMode): Promise<void> {
    try {
      await api.room.sendRequest(roomId, targetTemp, fanSpeed, mode);
      await this.refreshRoomStates();
      // 发送请求后立即刷新队列，确保队列状态更新
      await this.refreshQueues();
    } catch (error) {
      console.error('发送服务请求失败:', error);
      throw error;
    }
  }

  async setMode(roomId: string, mode: ACMode): Promise<void> {
    try {
      await api.room.setMode(roomId, mode);
      await this.refreshRoomStates();
      await this.refreshQueues();
    } catch (error) {
      console.error('切换模式失败:', error);
      throw error;
    }
  }

  // ==================== 管理员接口 ====================

  getServiceQueue(): ServiceObject[] {
    return this.serviceQueueCache;
  }

  getWaitingQueue(): WaitingObject[] {
    return this.waitingQueueCache;
  }

  async turnOffAll(): Promise<void> {
    try {
      const roomIds = Array.from(this.roomStatesCache.keys());
      await Promise.all(roomIds.map((rid) => api.room.turnOff(rid)));
      await this.refreshRoomStates();
      await this.refreshQueues();
    } catch (error) {
      console.error('一键关机失败:', error);
      throw error;
    }
  }

  async turnOnAll(): Promise<void> {
    try {
      const roomIds = Array.from(this.roomStatesCache.keys());
      await Promise.all(roomIds.map((rid) => api.room.turnOn(rid)));
      await this.refreshRoomStates();
      await this.refreshQueues();
    } catch (error) {
      console.error('一键开机失败:', error);
      throw error;
    }
  }

  async clearWaitingQueue(): Promise<void> {
    try {
      // 后端未提供清空等待队列接口，直接重刷以保持同步
      await this.refreshQueues();
    } catch (error) {
      console.error('清空等待队列失败:', error);
      throw error;
    }
  }

  // ==================== 经理接口 ====================

  async generateStatistics(startTime: number, endTime: number, _roomId?: string): Promise<StatisticsReport> {
    try {
      const rawStats = await api.manager.getStatistics(startTime, endTime);
      const roomStatistics = (rawStats || []).map((item: any) => ({
        roomId: String(item.roomId ?? ''),
        serviceCount: Number(item.dispatchCount ?? item.recordCount ?? 0),
        totalCost: Number(item.totalFee ?? 0),
        totalServiceDuration: Math.round((item.totalDuration ?? 0) * 60),
        averageTemp: Number(item.avgTempDiff ?? 0),
        mostUsedFanSpeed: FanSpeed.MEDIUM
      }));

      const totalRooms = roomStatistics.length;
      const totalServiceRequests = roomStatistics.reduce((sum: number, r: typeof roomStatistics[number]) => sum + r.serviceCount, 0);
      const totalCost = roomStatistics.reduce((sum: number, r: typeof roomStatistics[number]) => sum + r.totalCost, 0);

      return {
        startTime,
        endTime,
        totalRooms,
        totalServiceRequests,
        totalCost,
        averageCostPerRoom: totalRooms > 0 ? totalCost / totalRooms : 0,
        roomStatistics,
        fanSpeedDistribution: {
          low: 0,
          medium: 0,
          high: 0
        }
      };
    } catch (error) {
      console.error('生成报表失败:', error);
      throw error;
    }
  }

  // ==================== 系统方法 ====================

  onStateChange(callback: () => void): void {
    this.stateChangeCallbacks.add(callback);
  }

  destroy(): void {
    this.stateChangeCallbacks.clear();
  }
}

/**
 * 创建HVAC服务实例
 */
export function createHvacService(): IHvacService {
  return new HvacService();
}

export default HvacService;
