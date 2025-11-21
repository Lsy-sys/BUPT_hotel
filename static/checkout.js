const API_BASE = '/api';

async function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `show ${type}`;
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}

function showAlert(message, type = 'success', data = null) {
  const title = type === 'success' ? '退房成功' : '退房失败';
  const icon = type === 'success' ? '✓' : '✗';
  
  let alertMessage = `${icon} ${title}\n\n${message}`;
  
  if (type === 'success' && data) {
    alertMessage += '\n\n账单详情：\n';
    if (data.roomFee !== undefined) {
      alertMessage += `房费：¥${(data.roomFee || 0).toFixed(2)}\n`;
    }
    if (data.acFee !== undefined) {
      alertMessage += `空调费：¥${(data.acFee || 0).toFixed(2)}\n`;
    }
    if (data.totalAmount !== undefined) {
      alertMessage += `总计：¥${(data.totalAmount || 0).toFixed(2)}\n`;
    }
  }
  
  alert(alertMessage);
}

async function loadOccupiedRooms() {
  try {
    const res = await fetch(`${API_BASE}/monitor/roomstatus`);
    const rooms = await res.json();
    const checkoutSelect = document.getElementById('checkout-room-id');
    const tbody = document.getElementById('rooms-body');
    
    checkoutSelect.innerHTML = '<option value="">请选择房间</option>';
    tbody.innerHTML = '';
    
    const formatDateTime = (dateStr) => {
      if (!dateStr) return '--';
      try {
        let date;
        if (dateStr.endsWith('Z')) {
          date = new Date(dateStr);
        } else if (dateStr.includes('T') && !dateStr.includes('+') && !dateStr.includes('-', 10)) {
          date = new Date(dateStr + 'Z');
        } else {
          date = new Date(dateStr);
        }
        return date.toLocaleString('zh-CN', { 
          timeZone: 'Asia/Shanghai',
          year: 'numeric', 
          month: '2-digit', 
          day: '2-digit', 
          hour: '2-digit', 
          minute: '2-digit' 
        });
      } catch {
        return dateStr;
      }
    };
    
    rooms.forEach(room => {
      if (room.roomStatus === 'OCCUPIED') {
        const option = document.createElement('option');
        option.value = room.roomId;
        option.textContent = `房间 ${room.roomId}`;
        checkoutSelect.appendChild(option);
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${room.roomId}</td>
          <td>${room.customerName || '--'}</td>
          <td>${room.customerIdCard || '--'}</td>
          <td>${room.customerPhone || '--'}</td>
          <td>${formatDateTime(room.checkInTime)}</td>
          <td>
            <button class="btn btn-danger btn-sm" onclick="checkoutRoom(${room.roomId})">退房</button>
          </td>
        `;
        tbody.appendChild(tr);
      }
    });
  } catch (error) {
    showToast('加载已入住房间失败', 'error');
  }
}

document.getElementById('checkout-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const roomId = parseInt(document.getElementById('checkout-room-id').value);
  if (!roomId) {
    showToast('请选择房间', 'error');
    showAlert('请选择要退房的房间', 'error');
    return;
  }
  
  // 确认对话框，防止误触
  const confirmMessage = `确认要办理房间 ${roomId} 的退房手续吗？\n\n退房后将：\n- 生成账单\n- 清空房间状态\n- 房间恢复为空闲状态`;
  if (!confirm(confirmMessage)) {
    return; // 用户取消
  }
  
  try {
    const res = await fetch(`${API_BASE}/hotel/checkout/${roomId}`, {
      method: 'POST'
    });
    const data = await res.json();
    if (res.ok) {
      const resultDiv = document.getElementById('checkout-result');
      resultDiv.className = 'result show';
      resultDiv.innerHTML = renderCheckoutResult(data, roomId);
      
      const message = '退房成功';
      showToast(message, 'success');
      
      // 显示alert
      showAlert(`房间 ${roomId} 退房成功`, 'success', data);
      
      document.getElementById('checkout-form').reset();
      loadOccupiedRooms();
    } else {
      const errorMsg = data.error || '退房失败';
      showToast(errorMsg, 'error');
      showAlert(errorMsg, 'error');
    }
  } catch (error) {
    const errorMsg = '办理退房失败：' + error.message;
    showToast(errorMsg, 'error');
    showAlert(errorMsg, 'error');
  }
});

document.getElementById('btn-refresh-rooms').addEventListener('click', () => {
  loadOccupiedRooms();
});

window.checkoutRoom = async function(roomId) {
  // 确认对话框，防止误触
  const confirmMessage = `确认要办理房间 ${roomId} 的退房手续吗？\n\n退房后将：\n- 生成账单\n- 清空房间状态\n- 房间恢复为空闲状态`;
  if (!confirm(confirmMessage)) {
    return; // 用户取消
  }
  
  document.getElementById('checkout-room-id').value = roomId;
  document.getElementById('checkout-form').dispatchEvent(new Event('submit'));
};

// 从URL参数中获取房间号
function initFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  const roomId = urlParams.get('roomId');
  if (roomId) {
    document.getElementById('checkout-room-id').value = roomId;
  }
}

function formatDateTime(dateStr) {
  if (!dateStr) return '--';
  try {
    let date;
    if (dateStr.endsWith('Z')) {
      date = new Date(dateStr);
    } else if (dateStr.includes('T') && !dateStr.includes('+') && !dateStr.includes('-', 10)) {
      date = new Date(dateStr + 'Z');
    } else {
      date = new Date(dateStr);
    }
    return date.toLocaleString('zh-CN', { 
      timeZone: 'Asia/Shanghai',
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit', 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
  } catch {
    return dateStr;
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '--';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', { 
      timeZone: 'Asia/Shanghai',
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit'
    });
  } catch {
    return dateStr;
  }
}

function getFanSpeedText(speed) {
  const map = {
    'LOW': '低风',
    'MEDIUM': '中风',
    'HIGH': '高风'
  };
  return map[speed] || speed;
}

function renderCheckoutResult(data, roomId) {
  const customer = data.customer || {};
  const bill = data.bill || {};
  const detailBills = data.detailBill || [];
  
  let html = `
    <div class="checkout-details">
      <div class="detail-section">
        <h3>客户信息</h3>
        <div class="info-grid">
          <div class="info-item">
            <label>客户姓名：</label>
            <span>${customer.name || '--'}</span>
          </div>
          <div class="info-item">
            <label>身份证号：</label>
            <span>${customer.idCard || '--'}</span>
          </div>
          <div class="info-item">
            <label>联系电话：</label>
            <span>${customer.phoneNumber || '--'}</span>
          </div>
          <div class="info-item">
            <label>房间号：</label>
            <span>${roomId}</span>
          </div>
        </div>
      </div>
      
      <div class="detail-section">
        <h3>住宿信息</h3>
        <div class="info-grid">
          <div class="info-item">
            <label>入住时间：</label>
            <span>${formatDate(bill.checkinTime)}</span>
          </div>
          <div class="info-item">
            <label>退房时间：</label>
            <span>${formatDate(bill.checkoutTime)}</span>
          </div>
          <div class="info-item">
            <label>住宿天数：</label>
            <span>${bill.duration || '--'} 天</span>
          </div>
        </div>
      </div>
      
      <div class="detail-section">
        <h3>费用明细</h3>
        <div class="bill-summary">
          <div class="bill-item">
            <label>房费：</label>
            <span class="amount">¥${(bill.roomFee || 0).toFixed(2)}</span>
          </div>
          <div class="bill-item">
            <label>空调费：</label>
            <span class="amount">¥${(bill.acFee || 0).toFixed(2)}</span>
          </div>
          <div class="bill-item total">
            <label>总计：</label>
            <span class="amount">¥${((bill.roomFee || 0) + (bill.acFee || 0)).toFixed(2)}</span>
          </div>
        </div>
      </div>
  `;
  
  if (detailBills.length > 0) {
    html += `
      <div class="detail-section">
        <h3>空调使用明细</h3>
        <div class="table-container">
          <table class="detail-table">
            <thead>
              <tr>
                <th>开始时间</th>
                <th>结束时间</th>
                <th>使用时长（分钟）</th>
                <th>风速</th>
                <th>费用</th>
              </tr>
            </thead>
            <tbody>
    `;
    
    detailBills.forEach(detail => {
      html += `
        <tr>
          <td>${formatDateTime(detail.startTime)}</td>
          <td>${formatDateTime(detail.endTime)}</td>
          <td>${detail.duration || 0}</td>
          <td>${getFanSpeedText(detail.fanSpeed)}</td>
          <td>¥${(detail.fee || 0).toFixed(2)}</td>
        </tr>
      `;
    });
    
    html += `
            </tbody>
          </table>
        </div>
      </div>
    `;
  }
  
  html += `</div>`;
  
  return html;
}

loadOccupiedRooms();
initFromUrl();

