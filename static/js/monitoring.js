/**
 * Monitoring Page Logic (监控端)
 * 负责显示所有房间的实时监控信息
 */

document.addEventListener('DOMContentLoaded', () => {
    // 初始化
    loadMonitoringData();

    // 每2秒刷新一次数据
    setInterval(loadMonitoringData, 2000);
});

function loadMonitoringData() {
    // 并行获取房间数据和队列数据
    Promise.all([
        axios.get('/manager/monitoring/data'),
        axios.get('/monitor/status')
    ])
    .then(([roomResponse, queueResponse]) => {
        renderMonitoringData(roomResponse.data);
        renderQueueData(queueResponse.data);
        updateLastUpdateTime();
    })
    .catch(error => {
        console.error('获取监控数据失败:', error);
        showErrorState();
    });
}

function renderMonitoringData(rooms) {
    const grid = document.getElementById('rooms-grid');

    if (!rooms || rooms.length === 0) {
        grid.innerHTML = '<div class="room-card-loading"><i class="fa-solid fa-spinner fa-spin"></i> 正在加载房间数据...</div>';
        return;
    }

    // 检查是否需要重新渲染（房间数量发生变化）
    const existingCards = grid.querySelectorAll('.room-monitor-card');
    const needsReRender = existingCards.length !== rooms.length;

    if (needsReRender) {
        // 完全重新渲染
        grid.innerHTML = rooms.map(room => createRoomCard(room)).join('');
    } else {
        // 只更新数据，避免DOM跳动
        rooms.forEach((room, index) => {
            const card = existingCards[index];
            if (card) {
                updateRoomCard(card, room);
            }
        });
    }
}

function createRoomCard(room) {
    const acOn = room.ac_on;
    const queueState = room.queue_state || 'OFF';

    // 状态徽章
    let statusBadgeClass = 'ac-off';
    let statusText = '关闭';

    if (acOn) {
        statusBadgeClass = 'ac-on';
        statusText = '开启';

        if (queueState === 'SERVING') {
            statusBadgeClass = 'serving';
            statusText = '服务中';
        } else if (queueState === 'WAITING') {
            statusBadgeClass = 'waiting';
            statusText = '等待中';
        } else if (queueState === 'PAUSED') {
            statusBadgeClass = 'paused';
            statusText = '暂停';
        }
    }

    // 风速显示
    const fanSpeedMap = {
        'HIGH': '高风',
        'MEDIUM': '中风',
        'LOW': '低风'
    };
    const fanSpeedText = fanSpeedMap[room.fan_speed] || room.fan_speed || '中风';

    // 模式显示
    const modeMap = {
        'COOLING': '制冷',
        'HEATING': '制热'
    };
    const modeText = modeMap[room.ac_mode] || room.ac_mode || '制冷';

    return `
        <div class="room-monitor-card ${acOn ? 'ac-on' : 'ac-off'}">
            <div class="room-card-header">
                <div class="room-number">
                    <i class="fa-solid fa-bed"></i> 房间 ${room.room_id}
                </div>
                <div class="room-status">
                    <span class="status-badge ${statusBadgeClass}">${statusText}</span>
                </div>
            </div>

            <div class="room-card-content">
                <div class="temp-info">
                    <div class="temp-item">
                        <span class="temp-label">当前温度</span>
                        <span class="temp-value current">${room.current_temp}°C</span>
                    </div>
                    <div class="temp-item">
                        <span class="temp-label">目标温度</span>
                        <span class="temp-value target">${room.target_temp}°C</span>
                    </div>
                </div>

                <div class="ac-settings">
                    <div class="setting-item">
                        <span class="setting-label">风速</span>
                        <span class="setting-value">${fanSpeedText}</span>
                    </div>
                    <div class="setting-item">
                        <span class="setting-label">模式</span>
                        <span class="setting-value">${modeText}</span>
                    </div>
                </div>
            </div>

            <div class="room-card-footer">
                <div class="fee-info">
                    <div class="fee-item">
                        <div class="fee-label">当前费用</div>
                        <div class="fee-value">¥${room.current_fee.toFixed(2)}</div>
                    </div>
                    <div class="fee-item">
                        <div class="fee-label">累计费用</div>
                        <div class="fee-value total">¥${room.total_fee.toFixed(2)}</div>
                    </div>
                    <div class="schedule-count">
                        <div class="fee-label">调度次数</div>
                        <div class="fee-value">${room.schedule_count}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function updateLastUpdateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('zh-CN', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById('last-update-time').textContent = timeString;
}

function updateRoomCard(card, room) {
    const acOn = room.ac_on;
    const queueState = room.queue_state || 'OFF';

    // 更新卡片样式类
    card.className = `room-monitor-card ${acOn ? 'ac-on' : 'ac-off'}`;

    // 更新状态徽章
    let statusBadgeClass = 'ac-off';
    let statusText = '关闭';

    if (acOn) {
        statusBadgeClass = 'ac-on';
        statusText = '开启';

        if (queueState === 'SERVING') {
            statusBadgeClass = 'serving';
            statusText = '服务中';
        } else if (queueState === 'WAITING') {
            statusBadgeClass = 'waiting';
            statusText = '等待中';
        } else if (queueState === 'PAUSED') {
            statusBadgeClass = 'paused';
            statusText = '暂停';
        }
    }

    // 更新房间号
    const roomNumber = card.querySelector('.room-number');
    if (roomNumber) {
        roomNumber.innerHTML = `<i class="fa-solid fa-bed"></i> 房间 ${room.room_id}`;
    }

    // 更新状态徽章
    const statusBadge = card.querySelector('.status-badge');
    if (statusBadge) {
        statusBadge.className = `status-badge ${statusBadgeClass}`;
        statusBadge.textContent = statusText;
    }

    // 更新温度信息
    const currentTemp = card.querySelector('.temp-value.current');
    if (currentTemp) {
        currentTemp.textContent = `${room.current_temp}°C`;
    }

    const targetTemp = card.querySelector('.temp-value.target');
    if (targetTemp) {
        targetTemp.textContent = `${room.target_temp}°C`;
    }

    // 更新空调设置
    const fanSpeedMap = {
        'HIGH': '高风',
        'MEDIUM': '中风',
        'LOW': '低风'
    };
    const fanSpeedText = fanSpeedMap[room.fan_speed] || room.fan_speed || '中风';

    const modeMap = {
        'COOLING': '制冷',
        'HEATING': '制热'
    };
    const modeText = modeMap[room.ac_mode] || room.ac_mode || '制冷';

    const fanSpeedValue = card.querySelector('.ac-settings .setting-item:nth-child(1) .setting-value');
    if (fanSpeedValue) {
        fanSpeedValue.textContent = fanSpeedText;
    }

    const modeValue = card.querySelector('.ac-settings .setting-item:nth-child(2) .setting-value');
    if (modeValue) {
        modeValue.textContent = modeText;
    }

    // 更新费用信息
    const currentFee = card.querySelector('.fee-value:not(.total)');
    if (currentFee) {
        currentFee.textContent = `¥${room.current_fee.toFixed(2)}`;
    }

    const totalFee = card.querySelector('.fee-value.total');
    if (totalFee) {
        totalFee.textContent = `¥${room.total_fee.toFixed(2)}`;
    }

    // 更新调度次数
    const scheduleCount = card.querySelector('.schedule-count .fee-value');
    if (scheduleCount) {
        scheduleCount.textContent = room.schedule_count;
    }
}

function renderQueueData(data) {
    // 更新服务队列
    const sList = document.getElementById('serving-list');
    const servingCount = document.getElementById('serving-count');

    if (servingCount) {
        servingCount.innerText = data.servingQueue.length;
    }

    if (sList) {
        sList.innerHTML = data.servingQueue.length ? data.servingQueue.map(item => `
            <div class="mini-card serving">
                <div class="mc-top">Room ${item.roomId}</div>
                <div class="mc-btm">
                    <span>${item.fanSpeed}</span>
                    <span>${item.servingSeconds.toFixed(0)}s</span>
                </div>
            </div>
        `).join('') : '<div style="color:#bdc3c7;font-size:0.8rem;">空闲</div>';
    }

    // 更新等待队列
    const wList = document.getElementById('waiting-list');
    const waitingCount = document.getElementById('waiting-count');

    if (waitingCount) {
        waitingCount.innerText = data.waitingQueue.length;
    }

    if (wList) {
        wList.innerHTML = data.waitingQueue.length ? data.waitingQueue.map(item => `
            <div class="mini-card waiting">
                <div class="mc-top">Room ${item.roomId}</div>
                <div class="mc-btm">
                    <span>${item.fanSpeed}</span>
                    <span>${item.waitingSeconds.toFixed(0)}s</span>
                </div>
            </div>
        `).join('') : '<div style="color:#bdc3c7;font-size:0.8rem;">无等待</div>';
    }
}

function showErrorState() {
    const grid = document.getElementById('rooms-grid');
    grid.innerHTML = `
        <div class="room-card-error">
            <i class="fa-solid fa-exclamation-triangle"></i>
            <div class="error-message">
                <strong>数据加载失败</strong><br>
                <small>请检查网络连接或刷新页面重试</small>
            </div>
        </div>
    `;
}

function resetDatabase() {
    if (!confirm('⚠️ 警告：此操作将清空所有数据并重新初始化数据库！\n\n确定要继续吗？')) {
        return;
    }

    if (!confirm('⚠️ 再次确认：这将删除所有房间、客户、账单和详单数据！\n\n确定要重置吗？')) {
        return;
    }

    axios.post('/admin/reset-database')
        .then(res => {
            alert('✅ ' + res.data.message);
            // 重置后刷新页面数据
            setTimeout(() => {
                loadMonitoringData();
            }, 500);
        })
        .catch(err => {
            alert('❌ 重置失败: ' + (err.response?.data?.error || err.message));
        });
}

function exportMonitoringDetails() {
    // 显示加载提示
    const originalText = event.target.innerHTML;
    event.target.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 导出中...';
    event.target.disabled = true;

    // 创建一个临时的a标签来触发下载
    const link = document.createElement('a');
    link.href = '/manager/monitoring/export';
    link.download = 'monitoring_details.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // 恢复按钮状态
    setTimeout(() => {
        event.target.innerHTML = originalText;
        event.target.disabled = false;
    }, 1000);
}

// 添加一些动画效果
document.addEventListener('DOMContentLoaded', () => {
    // 为房间卡片添加淡入动画
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    });

    // 只在页面初次加载时添加动画效果
    const grid = document.getElementById('rooms-grid');
    const observerConfig = { childList: true, subtree: false }; // 只监听直接子元素变化

    const mutationObserver = new MutationObserver(() => {
        const cards = document.querySelectorAll('.room-monitor-card');
        cards.forEach((card, index) => {
            // 只对新添加的卡片应用动画
            if (!card.style.opacity || card.style.opacity === '') {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                card.style.transition = `opacity 0.5s ease ${index * 0.1}s, transform 0.5s ease ${index * 0.1}s`;
                observer.observe(card);
            }
        });
    });

    mutationObserver.observe(grid, observerConfig);
});
