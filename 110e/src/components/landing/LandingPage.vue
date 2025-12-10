<template>
  <div class="landing-page">
    <!-- 动态背景 -->
    <div class="animated-background">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
    </div>

    <!-- 主要内容 -->
    <div class="landing-content">
      <!-- Logo 和标题 -->
      <div class="hero-section">
        <div class="logo-container">
          <div class="logo-icon">
            ❄️
          </div>
        </div>

        <h1 class="main-title">
          <span class="title-line">酒店中央</span>
          <span class="title-line highlight">温控系统</span>
        </h1>

        <p class="subtitle">
          智能调度 · 实时监控 · 精准计费
        </p>

        <!-- 特性标签 -->
        <div class="features-tags">
          <span class="feature-tag">
            <span class="tag-icon">🎯</span>
            优先级调度
          </span>
          <span class="feature-tag">
            <span class="tag-icon">⚡</span>
            实时响应
          </span>
          <span class="feature-tag">
            <span class="tag-icon">💰</span>
            自动计费
          </span>
        </div>

        <!-- 进入按钮 -->
        <button
          class="enter-button"
          @click="enterSystem"
        >
          <span class="button-text">进入系统</span>
          <span class="button-icon">→</span>
        </button>

        <!-- 系统信息 -->
        <div class="system-info">
          <div class="info-item">
            <span class="info-label">版本</span>
            <span class="info-value">v2.2.0</span>
          </div>
          <div class="info-divider"></div>
          <div class="info-item">
            <span class="info-label">房间数</span>
            <span class="info-value">5</span>
          </div>
          <div class="info-divider"></div>
          <div class="info-item">
            <span class="info-label">状态</span>
            <span class="info-value status-online">
              <span class="status-dot"></span>
              在线
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 装饰元素 -->
    <div class="decorative-elements">
      <div class="floating-card card-1">
        <div class="card-icon">
          🏠
        </div>
        <div class="card-text">
          客房控制
        </div>
      </div>
      <div class="floating-card card-2">
        <div class="card-icon">
          📊
        </div>
        <div class="card-text">
          数据统计
        </div>
      </div>
      <div class="floating-card card-3">
        <div class="card-icon">
          🎛️
        </div>
        <div class="card-text">
          智能调度
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';

const router = useRouter();

// 进入系统 - 跳转到角色选择页面
const enterSystem = () => {
  router.push('/home');
};
</script>

<style scoped>
.landing-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #0c4a6e 0%, #075985 25%, #0284c7 50%, #0ea5e9 75%, #38bdf8 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 动态背景 */
.animated-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  z-index: 1;
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.5;
  animation: float 20s infinite ease-in-out;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, #067ef5 0%, #0ea5e9 50%, transparent 100%);
  top: -250px;
  left: -250px;
  animation-delay: 0s;
}

.orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, #38bdf8 0%, #7dd3fc 50%, transparent 100%);
  bottom: -200px;
  right: -200px;
  animation-delay: -7s;
}

.orb-3 {
  width: 450px;
  height: 450px;
  background: radial-gradient(circle, #0284c7 0%, #0ea5e9 50%, transparent 100%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: -14s;
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(50px, -50px) scale(1.1);
  }
  66% {
    transform: translate(-50px, 50px) scale(0.9);
  }
}

/* 主要内容 */
.landing-content {
  position: relative;
  z-index: 2;
  text-align: center;
  padding: 40px 20px;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.hero-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 60px 0;
}

/* Logo */
.logo-container {
  margin-bottom: 32px;
  animation: fadeInDown 1s ease;
}

.logo-icon {
  font-size: 80px;
  margin: 0 auto;
  filter: drop-shadow(0 10px 30px rgba(56, 189, 248, 0.6)) drop-shadow(0 0 50px rgba(56, 189, 248, 0.4));
  animation: pulse 3s infinite ease-in-out;
  line-height: 1;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

/* 标题 */
.main-title {
  font-size: 56px;
  font-weight: 800;
  color: white;
  margin: 0 0 20px 0;
  line-height: 1.3;
  animation: fadeInUp 1s ease 0.2s both;
  text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.title-line {
  display: block;
  margin: 4px 0;
}

.title-line.highlight {
  background: linear-gradient(135deg, #38bdf8, #7dd3fc, #bae6fd, #38bdf8);
  background-size: 200% 200%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: gradientShift 3s ease infinite, fadeInUp 1s ease 0.3s both;
  filter: drop-shadow(0 0 20px rgba(56, 189, 248, 0.5));
}

@keyframes gradientShift {
  0%, 100% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
}

/* 副标题 */
.subtitle {
  font-size: 18px;
  color: #e0f2fe;
  margin: 0 0 36px 0;
  font-weight: 500;
  letter-spacing: 3px;
  animation: fadeInUp 1s ease 0.4s both;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}

/* 特性标签 */
.features-tags {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 40px;
  animation: fadeInUp 1s ease 0.5s both;
  max-width: 600px;
}

.feature-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(20px);
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.feature-tag:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(56, 189, 248, 0.4);
}

.tag-icon {
  font-size: 18px;
}

/* 进入按钮 */
.enter-button {
  position: relative;
  padding: 18px 48px;
  font-size: 18px;
  font-weight: 700;
  color: white;
  background: linear-gradient(135deg, #38bdf8, #0ea5e9);
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50px;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s ease;
  animation: fadeInUp 1s ease 0.6s both;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 10px 40px rgba(56, 189, 248, 0.5), 0 0 30px rgba(56, 189, 248, 0.3);
}

.enter-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.5s ease;
}

.enter-button:hover::before {
  left: 100%;
}

.enter-button:hover {
  transform: translateY(-3px) scale(1.05);
  box-shadow: 0 15px 50px rgba(56, 189, 248, 0.7), 0 0 50px rgba(56, 189, 248, 0.5);
  border-color: rgba(255, 255, 255, 0.5);
}

.enter-button:active {
  transform: translateY(-1px);
}

.button-icon {
  font-size: 24px;
  transition: transform 0.3s ease;
}

.enter-button:hover .button-icon {
  transform: translateX(5px);
}

/* 系统信息 */
.system-info {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-top: 48px;
  padding: 16px 28px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(20px);
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 16px;
  animation: fadeInUp 1s ease 0.7s both;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  cursor: default;
}

.system-info:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(56, 189, 248, 0.4);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: #bae6fd;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.info-value {
  font-size: 16px;
  color: white;
  font-weight: 700;
}

.info-divider {
  width: 1px;
  height: 30px;
  background: rgba(255, 255, 255, 0.3);
}

.status-online {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #ffffff;
  text-shadow: 0 0 10px rgba(56, 189, 248, 0.8);
}

.status-dot {
  width: 10px;
  height: 10px;
  background: #ffffff;
  border-radius: 50%;
  box-shadow: 0 0 15px rgba(255, 255, 255, 0.9), 0 0 25px rgba(56, 189, 248, 0.8), 0 0 35px rgba(56, 189, 248, 0.6);
  animation: blink 2s infinite;
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

/* 装饰元素 */
.decorative-elements {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.floating-card {
  position: absolute;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(20px);
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  color: white;
  display: flex;
  align-items: center;
  gap: 12px;
  animation: floatCard 6s infinite ease-in-out;
  opacity: 0.9;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.card-1 {
  top: 15%;
  left: 10%;
  animation-delay: 0s;
}

.card-2 {
  top: 60%;
  right: 10%;
  animation-delay: -2s;
}

.card-3 {
  bottom: 20%;
  left: 15%;
  animation-delay: -4s;
}

@keyframes floatCard {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(2deg);
  }
}

.card-icon {
  font-size: 24px;
}

.card-text {
  font-size: 14px;
  font-weight: 600;
}

/* 动画 */
@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .hero-section {
    padding: 40px 0;
  }

  .main-title {
    font-size: 36px;
  }

  .subtitle {
    font-size: 14px;
    letter-spacing: 2px;
  }

  .features-tags {
    gap: 8px;
    max-width: 100%;
  }

  .feature-tag {
    padding: 10px 18px;
    font-size: 13px;
  }

  .logo-icon {
    font-size: 60px;
  }

  .floating-card {
    display: none;
  }

  .enter-button {
    padding: 16px 40px;
    font-size: 16px;
  }

  .system-info {
    flex-wrap: wrap;
    gap: 12px;
    padding: 14px 20px;
  }

  .info-divider {
    display: none;
  }

  .info-item {
    min-width: 80px;
  }
}
</style>
