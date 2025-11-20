const API_BASE = '/api';

async function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `show ${type}`;
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}

function showAlert(message, type = 'success') {
  const title = type === 'success' ? '入住成功' : '入住失败';
  const icon = type === 'success' ? '✓' : '✗';
  alert(`${icon} ${title}\n\n${message}`);
}

async function loadAvailableRooms() {
  try {
    const res = await fetch(`${API_BASE}/hotel/rooms/available`);
    const rooms = await res.json();
    const checkinSelect = document.getElementById('checkin-room-id');
    const tbody = document.getElementById('rooms-body');
    
    checkinSelect.innerHTML = '<option value="">请选择房间</option>';
    tbody.innerHTML = '';
    
    rooms.forEach(room => {
      if (room.status === 'AVAILABLE') {
        const option = document.createElement('option');
        option.value = room.id;
        option.textContent = `房间 ${room.id}`;
        checkinSelect.appendChild(option);
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${room.id}</td>
          <td><span class="status-badge status-available">空闲</span></td>
          <td>
            <button class="btn btn-primary btn-sm" onclick="quickCheckin(${room.id})">选择此房间</button>
          </td>
        `;
        tbody.appendChild(tr);
      }
    });
  } catch (error) {
    showToast('加载可用房间失败', 'error');
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

document.getElementById('checkin-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const roomId = parseInt(document.getElementById('checkin-room-id').value);
  const name = document.getElementById('checkin-name').value;
  const idCard = document.getElementById('checkin-id-card').value;
  const phone = document.getElementById('checkin-phone').value;
  
  if (!roomId || !name) {
    showToast('请填写必填项', 'error');
    showAlert('请填写必填项（房间号和客户姓名）', 'error');
    return;
  }
  
  try {
    const res = await fetch(`${API_BASE}/hotel/checkin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ roomId, name, idCard, phoneNumber: phone })
    });
    const data = await res.json();
    if (res.ok) {
      const message = data.message || '入住成功';
      showToast(message, 'success');
      
      // 显示alert
      const alertMessage = `房间号：${roomId}\n客户姓名：${name}\n${idCard ? '身份证号：' + idCard + '\n' : ''}${phone ? '联系电话：' + phone + '\n' : ''}\n\n${message}`;
      showAlert(alertMessage, 'success');
      
      document.getElementById('checkin-form').reset();
      loadAvailableRooms();
    } else {
      const errorMsg = data.error || '入住失败';
      showToast(errorMsg, 'error');
      showAlert(errorMsg, 'error');
    }
  } catch (error) {
    const errorMsg = '办理入住失败：' + error.message;
    showToast(errorMsg, 'error');
    showAlert(errorMsg, 'error');
  }
});

document.getElementById('btn-refresh-rooms').addEventListener('click', () => {
  loadAvailableRooms();
});

window.quickCheckin = function(roomId) {
  document.getElementById('checkin-room-id').value = roomId;
  document.getElementById('checkin-name').focus();
};

// 从URL参数中获取房间号
function initFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  const roomId = urlParams.get('roomId');
  if (roomId) {
    document.getElementById('checkin-room-id').value = roomId;
    document.getElementById('checkin-name').focus();
  }
}

loadAvailableRooms();
initFromUrl();

