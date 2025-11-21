const API_BASE = '/api';

let refreshInterval = null;

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
    const tbody = document.getElementById('rooms-body');
    tbody.innerHTML = '';
    
    rooms.forEach(room => {
      const tr = document.createElement('tr');
      const statusClass = room.roomStatus === 'OCCUPIED' ? 'status-occupied' : 
                         room.roomStatus === 'MAINTENANCE' ? 'status-maintenance' : 'status-available';
      const queueClass = room.queueState === 'SERVING' ? 'queue-serving' : 
                        room.queueState === 'WAITING' ? 'queue-waiting' : '';
      
      // 操作按钮（维修相关）
      let actionButtons = '';
      if (room.roomStatus === 'AVAILABLE') {
        actionButtons = `<button class="btn btn-danger btn-sm" onclick="takeRoomOffline(${room.roomId})">标记维修</button>`;
      } else if (room.roomStatus === 'MAINTENANCE') {
        actionButtons = `<button class="btn btn-primary btn-sm" onclick="bringRoomOnline(${room.roomId})">恢复可用</button>`;
      } else if (room.roomStatus === 'OCCUPIED') {
        // 已入住房间不能标记为维修，必须先退房
        actionButtons = '<span style="color: #999;" title="已入住房间不能标记为维修，请先办理退房">--</span>';
      } else {
        actionButtons = '<span style="color: #999;">--</span>';
      }
      
      // 空调控制按钮（已入住或空闲房间都可以操作）
      let acControls = '';
      if (room.roomStatus === 'OCCUPIED' || room.roomStatus === 'AVAILABLE') {
        if (room.acOn) {
          acControls = `
            <div class="ac-controls">
              <button class="btn btn-danger btn-sm" onclick="powerOff(${room.roomId})" title="关机">关机</button>
              <button class="btn btn-primary btn-sm" onclick="changeTemp(${room.roomId})" title="改温度">改温度</button>
              <button class="btn btn-primary btn-sm" onclick="changeSpeed(${room.roomId})" title="改风速">改风速</button>
            </div>
          `;
        } else {
          acControls = `
            <div class="ac-controls">
              <button class="btn btn-primary btn-sm" onclick="powerOn(${room.roomId})" title="开机">开机</button>
            </div>
          `;
        }
      } else {
        acControls = '<span style="color: #999;">--</span>';
      }
      
      tr.innerHTML = `
        <td>${room.roomId}</td>
        <td><span class="status-badge ${statusClass}">${getStatusText(room.roomStatus)}</span></td>
        <td>${room.currentTemp?.toFixed(1) || '--'}°C</td>
        <td>${room.targetTemp || '--'}°C</td>
        <td>${getFanSpeedText(room.fanSpeed)}</td>
        <td>${room.acOn ? '开启' : '关闭'}</td>
        <td class="${queueClass}">${getQueueStateText(room.queueState || 'IDLE')}</td>
        <td>${actionButtons}</td>
        <td>${acControls}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (error) {
    showToast('加载房间状态失败', 'error');
  }
}

async function loadQueues() {
  try {
    const res = await fetch(`${API_BASE}/ac/schedule/status`);
    const data = await res.json();
    
    const servingList = document.getElementById('serving-list');
    const waitingList = document.getElementById('waiting-list');
    const servingCount = document.getElementById('serving-count');
    const waitingCount = document.getElementById('waiting-count');
    const capacityInfo = document.getElementById('queue-capacity-info');
    
    servingList.innerHTML = '';
    waitingList.innerHTML = '';
    
    const capacity = data.capacity || 0;
    const timeSlice = data.timeSlice || 120;
    const servingCountNum = data.servingQueue?.length || 0;
    const waitingCountNum = data.waitingQueue?.length || 0;
    
    capacityInfo.textContent = `容量：${servingCountNum}/${capacity}`;
    servingCount.textContent = `(${servingCountNum})`;
    waitingCount.textContent = `(${waitingCountNum})`;
    
    // 更新调度策略说明中的动态数值
    const strategyCapacityElements = document.querySelectorAll('#strategy-capacity, #strategy-capacity-2');
    strategyCapacityElements.forEach(el => {
      if (el) el.textContent = capacity;
    });
    const strategyTimeSliceElement = document.getElementById('strategy-time-slice');
    if (strategyTimeSliceElement) {
      strategyTimeSliceElement.textContent = timeSlice;
    }
    
    if (data.servingQueue && data.servingQueue.length > 0) {
      data.servingQueue.forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = `
          <span>房间 ${item.roomId}</span>
          <span style="margin: 0 10px;">风速：${getFanSpeedText(item.fanSpeed)}</span>
          <span style="color: #666; font-size: 0.85rem;">目标温度：${item.targetTemp || '--'}°C</span>
        `;
        servingList.appendChild(li);
      });
    } else {
      const li = document.createElement('li');
      li.textContent = '暂无房间';
      li.style.color = '#999';
      servingList.appendChild(li);
    }
    
    if (data.waitingQueue && data.waitingQueue.length > 0) {
      data.waitingQueue.forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = `
          <span>房间 ${item.roomId}</span>
          <span style="margin: 0 10px;">风速：${getFanSpeedText(item.fanSpeed)}</span>
          <span style="color: #666; font-size: 0.85rem;">等待中...</span>
        `;
        waitingList.appendChild(li);
      });
    } else {
      const li = document.createElement('li');
      li.textContent = '暂无房间';
      li.style.color = '#999';
      waitingList.appendChild(li);
    }
  } catch (error) {
    showToast('加载队列状态失败', 'error');
  }
}

function getStatusText(status) {
  const map = {
    'AVAILABLE': '空闲',
    'OCCUPIED': '已入住',
    'MAINTENANCE': '维修中'
  };
  return map[status] || status;
}

function getQueueStateText(state) {
  const map = {
    'SERVING': '服务中',
    'WAITING': '等待中',
    'IDLE': '空闲'
  };
  return map[state] || state;
}

function getFanSpeedText(speed) {
  const map = {
    'LOW': '低风',
    'MEDIUM': '中风',
    'HIGH': '高风'
  };
  return map[speed] || speed || '--';
}

function getNextFanSpeed(currentSpeed) {
  const speeds = ['LOW', 'MEDIUM', 'HIGH'];
  const currentIndex = speeds.indexOf(currentSpeed || 'LOW');
  const nextIndex = (currentIndex + 1) % speeds.length;
  return speeds[nextIndex];
}

function startAutoRefresh() {
  if (refreshInterval) clearInterval(refreshInterval);
  refreshInterval = setInterval(() => {
    loadRooms();
    loadQueues();
  }, 5000);
}

document.getElementById('btn-refresh-rooms').addEventListener('click', loadRooms);
document.getElementById('btn-refresh-queues').addEventListener('click', loadQueues);

document.querySelectorAll('[data-action]').forEach(btn => {
  btn.addEventListener('click', async () => {
    const roomId = parseInt(document.getElementById('maintenance-room-id').value);
    if (!roomId) {
      showToast('请输入房间号', 'error');
      return;
    }
    const action = btn.dataset.action;
    try {
      const endpoint = action === 'offline' ? 'offline' : 'online';
      const res = await fetch(`${API_BASE}/admin/rooms/${roomId}/${endpoint}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message || '操作成功', 'success');
        loadRooms();
      } else {
        showToast(data.error || '操作失败', 'error');
      }
    } catch (error) {
      showToast('操作失败', 'error');
    }
  });
});

document.getElementById('btn-force-rotation').addEventListener('click', async () => {
  try {
    const res = await fetch(`${API_BASE}/admin/maintenance/force-rotation`, {
      method: 'POST'
    });
    const data = await res.json();
    const resultDiv = document.getElementById('admin-result');
    resultDiv.className = 'result show';
    resultDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    showToast('强制轮转完成', 'success');
    loadQueues();
  } catch (error) {
    showToast('强制轮转失败', 'error');
  }
});

document.getElementById('btn-simulate-temp').addEventListener('click', async () => {
  try {
    const res = await fetch(`${API_BASE}/admin/maintenance/simulate-temperature`, {
      method: 'POST'
    });
    const data = await res.json();
    const resultDiv = document.getElementById('admin-result');
    resultDiv.className = 'result show';
    resultDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    showToast('温度模拟完成', 'success');
    loadRooms();
  } catch (error) {
    showToast('温度模拟失败', 'error');
  }
});

window.takeRoomOffline = async function(roomId) {
  try {
    const res = await fetch(`${API_BASE}/admin/rooms/${roomId}/offline`, {
      method: 'POST'
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || '房间已标记为维修', 'success');
      loadRooms();
    } else {
      showToast(data.error || '操作失败', 'error');
    }
  } catch (error) {
    showToast('操作失败', 'error');
  }
};

window.bringRoomOnline = async function(roomId) {
  try {
    const res = await fetch(`${API_BASE}/admin/rooms/${roomId}/online`, {
      method: 'POST'
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || '房间已恢复可用', 'success');
      loadRooms();
    } else {
      showToast(data.error || '操作失败', 'error');
    }
  } catch (error) {
    showToast('操作失败', 'error');
  }
};

// 开机功能
window.powerOn = async function(roomId) {
  try {
    // 先获取当前房间状态，使用实际的当前温度
    let currentTemp = null;
    try {
      const statusRes = await fetch(`${API_BASE}/ac/room/${roomId}/status`);
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        currentTemp = statusData.currentTemp;
      }
    } catch (error) {
      currentTemp = 32;
    }
    
    if (currentTemp === null || currentTemp === undefined) {
      currentTemp = 32;
    }
    
    const res = await fetch(`${API_BASE}/ac/room/${roomId}/start?currentTemp=${currentTemp}`, {
      method: 'POST'
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || '空调已开启', 'success');
      loadRooms();
      loadQueues();
    } else {
      showToast(data.error || '开机失败', 'error');
    }
  } catch (error) {
    showToast('开机失败：' + error.message, 'error');
  }
};

// 关机功能
window.powerOff = async function(roomId) {
  try {
    const res = await fetch(`${API_BASE}/ac/room/${roomId}/stop`, {
      method: 'POST'
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || '空调已关闭', 'success');
      // 关机后自动刷新队列（后端会自动补位）
      loadRooms();
      loadQueues();
    } else {
      showToast(data.error || '关机失败', 'error');
    }
  } catch (error) {
    showToast('关机失败：' + error.message, 'error');
  }
};

// 改温度功能
window.changeTemp = async function(roomId) {
  const currentTemp = prompt('请输入新的目标温度（18-30°C）：');
  if (currentTemp === null) {
    return; // 用户取消
  }
  
  const temp = parseFloat(currentTemp);
  if (isNaN(temp) || temp < 18 || temp > 30) {
    showToast('请输入18-30之间的有效温度值', 'error');
    return;
  }
  
  try {
    const res = await fetch(`${API_BASE}/ac/room/${roomId}/temp?targetTemp=${temp}`, {
      method: 'PUT'
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || '温度已设置', 'success');
      loadRooms();
    } else {
      showToast(data.error || '设置失败', 'error');
    }
  } catch (error) {
    showToast('设置温度失败：' + error.message, 'error');
  }
};

// 改风速功能（循环切换：低→中→高）
window.changeSpeed = async function(roomId) {
  try {
    // 先获取当前风速
    const statusRes = await fetch(`${API_BASE}/ac/room/${roomId}/status`);
    if (!statusRes.ok) {
      showToast('获取当前风速失败', 'error');
      return;
    }
    
    const statusData = await statusRes.json();
    const currentSpeed = statusData.fanSpeed || 'LOW';
    const nextSpeed = getNextFanSpeed(currentSpeed);
    
    const res = await fetch(`${API_BASE}/ac/room/${roomId}/speed?fanSpeed=${nextSpeed}`, {
      method: 'PUT'
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || `风速已切换为${getFanSpeedText(nextSpeed)}`, 'success');
      loadRooms();
      loadQueues();
    } else {
      showToast(data.error || '设置失败', 'error');
    }
  } catch (error) {
    showToast('设置风速失败：' + error.message, 'error');
  }
};

loadRooms();
loadQueues();
startAutoRefresh();

