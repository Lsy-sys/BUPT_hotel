/**
 * HVAC 系统 API 接口
 */
import request from './request';
import type {
  RoomState,
  DetailRecord,
  CheckInRecord
} from '../types';
import { ACMode, FanSpeed } from '../types';
import { ROOM_PRICES, DEFAULT_TEMP } from '../constants';

const normalizeRoomId = (id: string | number | undefined) => String(id ?? '');

/**
 * 前台管理接口
 */
export const frontDeskApi = {
  // 办理入住（支持空调初始化参数）
  async checkIn(
    roomId: string,
    guestName: string,
    guestPhone: string,
    idCard: string,
    stayDays: number,
    mode?: ACMode,
    roomTemp?: number,
    targetTemp?: number,
    fanSpeed?: FanSpeed
  ) {
    // 后端只需要基本入住信息，其余字段由后端默认处理
    const payload = {
      roomId: Number(roomId),
      name: guestName,
      phoneNumber: guestPhone,
      idCard
    };
    // 额外参数（模式/温度）后端会忽略，不影响
    return request.post('/hotel/checkin', payload);
  },

  // 办理退房
  checkOut(roomId: string) {
    return request.post(`/hotel/checkout/${roomId}`);
  },

  // 获取账单（后端暂无单独接口，返回空）
  async getBill(_roomId?: string) {
    return null;
  },

  // 获取所有账单（后端暂无列表接口，返回空数组）
  async getAllBills() {
    return [];
  },

  // 获取可入住房间列表
  async getAvailableRooms() {
    const rooms = await request.get<any[]>('/hotel/rooms/available');
    return rooms.map((room) => {
      const rid = normalizeRoomId(room.id ?? room.roomId ?? room.room_id);
      return {
        roomId: rid,
        pricePerNight: ROOM_PRICES[rid] ?? 100,
        isOccupied: false
      };
    });
  },

  // 获取已入住房间列表
  async getOccupiedRooms() {
    const rooms = await request.get<any[]>('/hotel/rooms');
    return rooms
      .filter((room) => room.status && room.status !== 'AVAILABLE')
      .map((room) => normalizeRoomId(room.id));
  },

  // 获取所有房间的基础信息
  getAllRooms() {
    return request.get<any[]>('/hotel/rooms');
  },

  // 获取入住记录（后端暂无独立接口，基于房间状态模拟）
  async getCheckInRecords(): Promise<CheckInRecord[]> {
    const rooms = await request.get<any[]>('/hotel/rooms');
    return rooms
      .filter((room) => room.status && room.status !== 'AVAILABLE')
      .map((room) => ({
        roomId: normalizeRoomId(room.id),
        checkInTime: Date.now(),
        mode: room.acMode || ACMode.COOLING,
        checkedOut: false,
        guestName: room.customer_name,
        guestPhone: room.phone_number
      })) as CheckInRecord[];
  },

  // 获取详单记录（使用报表接口）
  getDetailRecords(roomId: string) {
    return request.get<DetailRecord[]>('/report/room', { params: { roomId: Number(roomId) } });
  }
};

/**
 * 房间客户端接口
 */
export const roomApi = {
  // 获取房间状态
  getRoomState(roomId: string) {
    return request.get<RoomState>('/ac/state', { params: { roomId: Number(roomId) } });
  },

  // 开机
  turnOn(roomId: string) {
    return request.post('/ac/power', { roomId: Number(roomId) });
  },

  // 关机
  turnOff(roomId: string) {
    return request.post('/ac/power/off', { roomId: Number(roomId) });
  },

  // 发送请求（调温、调风）
  sendRequest(roomId: string, targetTemp: number, fanSpeed: FanSpeed, mode: ACMode) {
    const rid = Number(roomId);
    const tasks: Promise<any>[] = [];
    if (mode) tasks.push(request.post('/ac/mode', { roomId: rid, mode }));
    if (typeof targetTemp === 'number') tasks.push(request.post('/ac/temp', { roomId: rid, targetTemp }));
    if (fanSpeed) tasks.push(request.post('/ac/speed', { roomId: rid, fanSpeed }));
    return Promise.all(tasks);
  },

  // 初始化房间参数
  initializeRoom(roomId: string, mode: ACMode, roomTemp: number, targetTemp: number, fanSpeed: FanSpeed) {
    return request.post('/test/initRoom', {
      roomId: Number(roomId),
      temperature: roomTemp ?? DEFAULT_TEMP,
      defaultTemp: roomTemp ?? DEFAULT_TEMP,
      dailyRate: ROOM_PRICES[roomId] ?? 100
    });
  },

  // 切换模式
  setMode(roomId: string, mode: ACMode) {
    return request.post('/ac/mode', { roomId: Number(roomId), mode });
  }
};

/**
 * 管理员监控接口
 */
export const adminApi = {
  // 获取所有房间状态（从 room 接口获取）
  getAllRoomStates() {
    return request.get<RoomState[]>('/admin/rooms/status');
  },

  // 获取服务队列
  getServiceQueue() {
    return request.get<any>('/monitor/status').then((res) => res?.servingQueue || []);
  },

  // 获取等待队列
  getWaitingQueue() {
    return request.get<any>('/monitor/status').then((res) => res?.waitingQueue || []);
  },

  // 一键关机
  turnOffAll() {
    return Promise.resolve();
  },

  // 一键开机
  turnOnAll() {
    return Promise.resolve();
  },

  // 清空等待队列
  clearWaitingQueue() {
    return Promise.resolve();
  }
};

/**
 * 经理统计接口
 */
export const managerApi = {
  // 获取统计报表（使用周报接口，按开始日期计算）
  getStatistics(startTime: number, endTime: number) {
    const formatDate = (timestamp: number): string => {
      const date = new Date(timestamp);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };

    return request.get('/report/weekly', { params: { startDate: formatDate(startTime), endDate: formatDate(endTime) } });
  },

  // 获取所有账单
  getAllBills() {
    return Promise.resolve([]);
  }
};

/**
 * 导出所有 API
 */
export default {
  frontDesk: frontDeskApi,
  room: roomApi,
  admin: adminApi,
  manager: managerApi
};

