const API_BASE = '/api';

async function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `show ${type}`;
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}

const billRoomSelect = document.getElementById('bill-room-id');


async function loadAllRooms() {
  try {
    const res = await fetch(`${API_BASE}/monitor/roomstatus`);
    const rooms = await res.json();
    const tbody = document.getElementById('rooms-body');
    
    if (billRoomSelect) {
      billRoomSelect.innerHTML = '<option value="">请选择房间</option>';
    }
    if (tbody) {
      tbody.innerHTML = '';
    }
    
    rooms.forEach(room => {
      if (billRoomSelect) {
        const optionAll = document.createElement('option');
        optionAll.value = room.roomId;
        optionAll.textContent = `房间 ${room.roomId}`;
        billRoomSelect.appendChild(optionAll);
      }
      
      if (!tbody) return;
      
      const tr = document.createElement('tr');
      const statusClass = room.roomStatus === 'OCCUPIED' ? 'status-occupied' : 
                         room.roomStatus === 'MAINTENANCE' ? 'status-maintenance' : 'status-available';
      
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
      
      tr.innerHTML = `
        <td>${room.roomId}</td>
        <td><span class="status-badge ${statusClass}">${getStatusText(room.roomStatus)}</span></td>
        <td>${room.customerName || '--'}</td>
        <td>${room.customerIdCard || '--'}</td>
        <td>${room.customerPhone || '--'}</td>
        <td>${formatDateTime(room.checkInTime)}</td>
        <td>
          ${room.roomStatus === 'OCCUPIED' ? 
            `<a href="/reception/checkout?roomId=${room.roomId}" class="btn btn-danger btn-sm" style="text-decoration: none; display: inline-block;">退房</a>` : 
            room.roomStatus === 'AVAILABLE' ? 
            `<a href="/reception/checkin?roomId=${room.roomId}" class="btn btn-primary btn-sm" style="text-decoration: none; display: inline-block;">入住</a>` : 
            '--'}
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (error) {
    showToast('加载房间状态失败', 'error');
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

document.getElementById('btn-refresh-rooms').addEventListener('click', () => {
  loadAllRooms();
});

function renderBills(bills = []) {
  const container = document.getElementById('bills-result');
  if (!bills || bills.length === 0) {
    container.className = 'result show';
    container.innerHTML = '<p>未查询到账单数据。</p>';
    return;
  }

  const formatDate = (value) => {
    if (!value) return '--';
    try {
      let date;
      if (value.endsWith('Z')) {
        date = new Date(value);
      } else if (value.includes('T') && !value.includes('+') && !value.includes('-', 10)) {
        date = new Date(value + 'Z');
      } else {
        date = new Date(value);
      }
      return date.toLocaleString('zh-CN', {
        timeZone: 'Asia/Shanghai',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return value;
    }
  };

  const rows = bills
    .map(
      (bill) => `
        <tr>
          <td>${bill.id}</td>
          <td>${bill.roomId}</td>
          <td>${formatDate(bill.checkInTime)}</td>
          <td>${formatDate(bill.checkOutTime)}</td>
          <td>¥${(bill.roomFee || 0).toFixed(2)}</td>
          <td>¥${(bill.acFee || 0).toFixed(2)}</td>
          <td>¥${(bill.totalAmount || 0).toFixed(2)}</td>
          <td>${bill.status}</td>
        </tr>
      `
    )
    .join('');

  container.className = 'result show';
  container.innerHTML = `
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>账单ID</th>
            <th>房间号</th>
            <th>入住</th>
            <th>退房</th>
            <th>房费</th>
            <th>空调费</th>
            <th>总额</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

document.getElementById('bill-room-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const roomId = parseInt(billRoomSelect.value);
  if (!roomId) {
    showToast('请选择房间', 'error');
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/bills/room-id/${roomId}`);
    const data = await res.json();
    if (res.ok) {
      renderBills(data);
      showToast(`已展示房间 ${roomId} 的账单`, 'success');
    } else {
      showToast(data.error || '查询失败', 'error');
    }
  } catch (error) {
    showToast('查询房间账单失败', 'error');
  }
});

document.getElementById('btn-fetch-all-bills').addEventListener('click', async () => {
  try {
    const res = await fetch(`${API_BASE}/bills`);
    const data = await res.json();
    if (res.ok) {
      renderBills(data);
      showToast('已加载所有账单', 'success');
    } else {
      showToast(data.error || '查询失败', 'error');
    }
  } catch (error) {
    showToast('查询全部账单失败', 'error');
  }
});

loadAllRooms();

