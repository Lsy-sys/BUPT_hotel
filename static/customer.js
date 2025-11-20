const API_BASE = '/api';

let currentRoomId = null;
let refreshInterval = null;
let isUserEditing = false;
let isUserEditingSpeed = false;

async function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `show ${type}`;
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}

async function loadRooms() {
  try {
    const res = await fetch(`${API_BASE}/monitor/roomstatus`);
    const rooms = await res.json();
    const selector = document.getElementById('room-selector');
    selector.innerHTML = '<option value="">请选择房间</option>';
    const occupiedRooms = rooms.filter(room => (room.roomStatus || room.status) === 'OCCUPIED');
    if (occupiedRooms.length === 0) {
      const option = document.createElement('option');
      option.disabled = true;
      option.textContent = '暂无已入住房间';
      selector.appendChild(option);
      return;
    }
    occupiedRooms.forEach(room => {
      const option = document.createElement('option');
      option.value = room.roomId || room.id;
      option.textContent = `房间 ${room.roomId || room.id} - 已入住`;
      selector.appendChild(option);
    });
  } catch (error) {
    showToast('加载房间列表失败', 'error');
  }
}

async function loadRoomStatus(roomId) {
  try {
    const res = await fetch(`${API_BASE}/ac/room/${roomId}/status`);
    const data = await res.json();
    
    document.getElementById('current-temp').textContent = `${data.currentTemp?.toFixed(1) || '--'}°C`;
    document.getElementById('target-temp').textContent = `${data.targetTemp || '--'}°C`;
    document.getElementById('fan-speed').textContent = data.fanSpeed || '--';
    document.getElementById('ac-status').textContent = data.acOn ? '开启' : '关闭';
    
    // 只有在用户没有正在编辑时才更新输入框
    const tempInput = document.getElementById('temp-input');
    if (!isUserEditing && document.activeElement !== tempInput) {
      tempInput.value = data.targetTemp || '';
    }
    // 只有在用户没有正在编辑风速时才更新select的值
    const speedSelect = document.getElementById('speed-select');
    if (!isUserEditingSpeed && document.activeElement !== speedSelect) {
      speedSelect.value = data.fanSpeed || 'LOW';
    }
    
    const acStatusEl = document.getElementById('ac-status');
    acStatusEl.textContent = data.acOn ? '开启' : '关闭';
    acStatusEl.style.color = data.acOn ? '#10b981' : '#666';
  } catch (error) {
    showToast('加载房间状态失败', 'error');
  }
}

async function loadUsageStats(roomId) {
  try {
    const res = await fetch(`${API_BASE}/ac/room/${roomId}/detail`);
    if (!res.ok) {
      throw new Error('获取账单详情失败');
    }
    const data = await res.json();
    document.getElementById('total-duration').textContent = `${data.totalDuration || 0} 分钟`;
    document.getElementById('total-cost').textContent = `¥${(data.totalCost || 0).toFixed(2)}`;
  } catch (error) {
    console.error('加载使用统计失败', error);
    // 不显示错误提示，避免干扰用户
  }
}

function startAutoRefresh() {
  if (refreshInterval) clearInterval(refreshInterval);
  refreshInterval = setInterval(() => {
    if (currentRoomId) {
      // 刷新房间状态和账单（后端会在获取状态时自动更新温度）
      loadRoomStatus(currentRoomId);
      loadUsageStats(currentRoomId);
    }
  }, 3000);
}

document.getElementById('room-selector').addEventListener('change', (e) => {
  const roomId = parseInt(e.target.value);
  if (roomId) {
    currentRoomId = roomId;
    document.getElementById('current-room-id').textContent = roomId;
    document.getElementById('room-control').style.display = 'block';
    loadRoomStatus(roomId);
    loadUsageStats(roomId);
    startAutoRefresh();
  } else {
    currentRoomId = null;
    document.getElementById('room-control').style.display = 'none';
    if (refreshInterval) clearInterval(refreshInterval);
  }
});

document.getElementById('btn-refresh-rooms').addEventListener('click', loadRooms);

document.getElementById('btn-power-on').addEventListener('click', async () => {
  if (!currentRoomId) return;
  try {
    // 先获取当前房间状态，使用实际的当前温度
    let currentTemp = null;
    try {
      const statusRes = await fetch(`${API_BASE}/ac/room/${currentRoomId}/status`);
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        currentTemp = statusData.currentTemp;
      }
    } catch (error) {
      // 如果获取状态失败，使用默认值32
      currentTemp = 32;
    }
    
    // 如果没有获取到温度，使用默认值
    if (currentTemp === null || currentTemp === undefined) {
      currentTemp = 32;
    }
    
    const res = await fetch(`${API_BASE}/ac/room/${currentRoomId}/start?currentTemp=${currentTemp}`, {
      method: 'POST'
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || '空调已开启', 'success');
      loadRoomStatus(currentRoomId);
      loadUsageStats(currentRoomId);
    } else {
      showToast(data.error || '开启失败', 'error');
    }
  } catch (error) {
    showToast('开启空调失败', 'error');
  }
});

document.getElementById('btn-power-off').addEventListener('click', async () => {
  if (!currentRoomId) return;
  try {
    const res = await fetch(`${API_BASE}/ac/room/${currentRoomId}/stop`, {
      method: 'POST'
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || '空调已关闭', 'success');
      loadRoomStatus(currentRoomId);
      loadUsageStats(currentRoomId);
    } else {
      showToast(data.error || '关闭失败', 'error');
    }
  } catch (error) {
    showToast('关闭空调失败', 'error');
  }
});

document.getElementById('temp-input').addEventListener('focus', () => {
  isUserEditing = true;
});

document.getElementById('temp-input').addEventListener('blur', () => {
  isUserEditing = false;
});

document.getElementById('speed-select').addEventListener('focus', () => {
  isUserEditingSpeed = true;
});

document.getElementById('speed-select').addEventListener('blur', () => {
  isUserEditingSpeed = false;
});

document.getElementById('btn-set-temp').addEventListener('click', async () => {
  if (!currentRoomId) {
    showToast('请先选择房间', 'error');
    return;
  }
  
  // 先检查空调是否开启
  try {
    const statusRes = await fetch(`${API_BASE}/ac/room/${currentRoomId}/status`);
    const statusData = await statusRes.json();
    if (!statusData.acOn) {
      showToast('请先开启空调', 'error');
      return;
    }
  } catch (error) {
    showToast('检查空调状态失败', 'error');
    return;
  }
  
  const temp = parseFloat(document.getElementById('temp-input').value);
  if (!temp || isNaN(temp) || temp < 18 || temp > 30) {
    showToast('请输入18-30之间的有效温度值', 'error');
    return;
  }
  
  try {
    const res = await fetch(`${API_BASE}/ac/room/${currentRoomId}/temp?targetTemp=${temp}`, {
      method: 'PUT'
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || '温度已设置', 'success');
      isUserEditing = false;
      // 立即刷新状态以显示更新后的温度
      await loadRoomStatus(currentRoomId);
      // 刷新账单使用情况
      loadUsageStats(currentRoomId);
    } else {
      showToast(data.error || '设置失败', 'error');
    }
  } catch (error) {
    showToast('设置温度失败', 'error');
  }
});

document.getElementById('btn-set-speed').addEventListener('click', async () => {
  if (!currentRoomId) {
    showToast('请先选择房间', 'error');
    return;
  }
  
  // 先检查空调是否开启
  try {
    const statusRes = await fetch(`${API_BASE}/ac/room/${currentRoomId}/status`);
    const statusData = await statusRes.json();
    if (!statusData.acOn) {
      showToast('请先开启空调', 'error');
      return;
    }
  } catch (error) {
    showToast('检查空调状态失败', 'error');
    return;
  }
  
  const speed = document.getElementById('speed-select').value;
  if (!speed) {
    showToast('请选择风速', 'error');
    return;
  }
  
  try {
    const res = await fetch(`${API_BASE}/ac/room/${currentRoomId}/speed?fanSpeed=${speed}`, {
      method: 'PUT'
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || '风速已设置', 'success');
      isUserEditingSpeed = false;
      // 立即刷新状态以显示更新后的风速
      await loadRoomStatus(currentRoomId);
      // 刷新账单使用情况
      loadUsageStats(currentRoomId);
    } else {
      showToast(data.error || '设置失败', 'error');
    }
  } catch (error) {
    showToast('设置风速失败', 'error');
  }
});

loadRooms();

