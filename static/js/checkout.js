// Check-out Logic

// 存储当前结账数据，用于CSV导出
let currentCheckoutData = null;

function performCheckout() {
  const roomId = document.getElementById('roomIdInput').value;
  if (!roomId) {
      alert("请输入房间号");
      return;
  }

  axios.post(`/hotel/checkout/${roomId}`)
      .then(response => {
          renderInvoice(response.data);
      })
      .catch(error => {
          console.error(error);
          alert("退房失败: " + (error.response?.data?.error || error.message));
      });
}

function renderInvoice(data) {
  // 保存数据用于CSV导出
  currentCheckoutData = data;
  
  // data 结构对应 CheckoutResponse
  const customer = data.customer;
  const bill = data.bill;
  const details = data.detailBill;

  // 1. 显示容器
  document.getElementById('invoice-container').style.display = 'flex';

  // 2. 填充头部信息
  document.getElementById('bill-date').innerText = new Date().toLocaleDateString();
  document.getElementById('bill-id').innerText = Date.now().toString().slice(-6); // 模拟单号

  // 3. 客户信息
  if (customer) {
      document.getElementById('customer-info').innerHTML = `
          <div><strong>客户姓名:</strong> ${customer.name}</div>
          <div><strong>身份证号:</strong> ${customer.idCard || '--'}</div>
          <div><strong>联系电话:</strong> ${customer.phoneNumber || '--'}</div>
      `;
  }

  // 4. 汇总数据
  if (bill) {
      document.getElementById('stay-days').innerText = bill.duration + " 天";
      document.getElementById('room-fee').innerText = bill.roomFee.toFixed(2);
      document.getElementById('ac-fee').innerText = bill.acFee.toFixed(2);
      
      const total = (bill.roomFee + bill.acFee).toFixed(2);
      document.getElementById('total-amount').innerText = total;
  }

  // 5. 详单表格
  const tbody = document.getElementById('detail-list');
  tbody.innerHTML = '';

  if (details && details.length > 0) {
      details.forEach(item => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
              <td>${item.roomId}</td>
              <td>${formatTime(item.startTime)}</td>
              <td>${formatTime(item.endTime)}</td>
              <td>${item.duration}</td>
              <td>${item.fanSpeed}</td>
              <td>${item.rate}</td>
              <td>¥ ${(item.acFee || 0).toFixed(2)}</td>
              <td>¥ ${(item.roomFee || 0).toFixed(2)}</td>
              <td class="fw-bold text-primary">¥ ${(item.fee || 0).toFixed(2)}</td>
          `;
          tbody.appendChild(tr);
      });
  } else {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#999">无详细消费记录</td></tr>';
  }
}

function formatTime(isoStr) {
  if (!isoStr) return '--';
  const d = new Date(isoStr);
  return d.toLocaleString('zh-CN', { hour12: false });
}

function downloadCSV() {
  if (!currentCheckoutData) {
    alert("没有可导出的数据，请先办理退房");
    return;
  }

  const customer = currentCheckoutData.customer;
  const bill = currentCheckoutData.bill;
  const details = currentCheckoutData.detailBill;

  // 构建CSV内容
  let csvContent = "\uFEFF"; // BOM for UTF-8
  
  // 客户信息
  csvContent += "客户信息\n";
  if (customer) {
    csvContent += `客户姓名,${customer.name}\n`;
    csvContent += `身份证号,${customer.idCard || '--'}\n`;
    csvContent += `联系电话,${customer.phoneNumber || '--'}\n`;
  }
  csvContent += "\n";

  // 账单汇总
  csvContent += "账单汇总\n";
  if (bill) {
    csvContent += `房间号,${bill.roomId}\n`;
    csvContent += `入住时间,${bill.checkinTime}\n`;
    csvContent += `退房时间,${bill.checkoutTime}\n`;
    csvContent += `入住时长,${bill.duration} 天\n`;
    csvContent += `住宿费用,${bill.roomFee.toFixed(2)}\n`;
    csvContent += `空调费用,${bill.acFee.toFixed(2)}\n`;
    csvContent += `总费用,${(bill.roomFee + bill.acFee).toFixed(2)}\n`;
  }
  csvContent += "\n";

  // 详单
  csvContent += "消费明细\n";
  csvContent += "房间号,开始时间,结束时间,时长(分),风速,费率,空调费(元),房费(元),总费用(元)\n";
  
  if (details && details.length > 0) {
    details.forEach(item => {
      const startTime = formatTime(item.startTime);
      const endTime = formatTime(item.endTime);
      csvContent += `${item.roomId},${startTime},${endTime},${item.duration},${item.fanSpeed},${item.rate},${(item.acFee || 0).toFixed(2)},${(item.roomFee || 0).toFixed(2)},${(item.fee || 0).toFixed(2)}\n`;
    });
  }

  // 创建下载链接
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  
  // 生成文件名
  const roomId = bill ? bill.roomId : 'unknown';
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  link.setAttribute('download', `room_${roomId}_checkout_${timestamp}.csv`);
  
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}