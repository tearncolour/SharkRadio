<template>
  <a-config-provider
    :theme="{
      token: {
        colorPrimary: '#00e5ff',
        borderRadius: 8,
        colorBgBase: '#0a0a0c',
        colorTextBase: '#f0f0f2',
      }
    }"
  >
    <a-layout class="layout">
      <a-layout-header class="header">
        <div class="logo-wrapper">
          <span class="logo-icon"><wifi-outlined /></span>
          <span class="logo-text">SharkRadio</span>
        </div>
        <div class="header-divider"></div>
        <div class="subtitle">RoboMaster 2026 雷达站无线桌面客户端</div>
        <div class="header-status">
          <a-badge :status="isConnected ? 'processing' : 'default'" :text="isConnected ? '后台已连接' : '后台未连接'" />
        </div>
      </a-layout-header>
      
      <a-layout-content class="content-wrapper">
        <div class="main-container">
          <!-- 左侧: 标签页式设备管理 -->
          <div class="left-panel">
             <div class="status-section">
               <SDRStatus />
             </div>
             <div class="tabs-section">
               <SDRTabs />
             </div>
          </div>
          
          <!-- 右侧: 频谱视图 & 解码数据 -->
          <div class="right-panel">
            <a-space direction="vertical" style="width: 100%" size="middle">
              <SpectrumView />
              
              <a-card title="收到的原始解码包 (Raw Packets)" class="panel-card" style="min-height: 250px">
                <template #extra>
                  <a-button type="link" size="small">清除日志</a-button>
                </template>
                <div class="packet-log">
                  <a-empty v-if="packets.length === 0" description="暂未接收到符合 4-RRC-FSK 协议的数据包" />
                  <div v-else v-for="(p, i) in packets" :key="i" class="packet-row">
                    <span class="timestamp">[{{ p.time }}]</span>
                    <span class="hex">{{ p.data }}</span>
                  </div>
                </div>
              </a-card>
            </a-space>
          </div>
        </div>
      </a-layout-content>
      
      <a-layout-footer class="footer">
        SharkRadio &copy;2026 基于 ADI PLUTO SDR 的 RoboMaster 解决方案
      </a-layout-footer>
    </a-layout>
  </a-config-provider>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useWebSocket } from '@/composables/useWebSocket';
import { WifiOutlined } from '@ant-design/icons-vue';
import SDRStatus from '@/components/SDRStatus.vue';
import SDRTabs from '@/components/SDRTabs.vue';
import SpectrumView from '@/components/SpectrumView.vue';

// 初始化 WebSocket 连接
const { isConnected } = useWebSocket();

const packets = ref<{time: string, data: string}[]>([]);

onMounted(() => {
  console.log('SharkRadio 系统启动...');
});
</script>

<style scoped>
.layout {
  min-height: 100vh;
  background: var(--bg-color);
}

.header {
  height: 64px;
  background: rgba(10, 10, 12, 0.95);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
  display: flex;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 4px 20px rgba(0, 229, 255, 0.1);
  z-index: 10;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 24px;
  color: var(--primary-color);
  animation: rotate 10s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.logo-text {
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #fff, var(--primary-color));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-divider {
  width: 1px;
  height: 24px;
  background: rgba(255, 255, 255, 0.1);
  margin: 0 20px;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  flex: 1;
}

.header-status {
  margin-left: auto;
}

.content-wrapper {
  padding: 16px;
  height: calc(100vh - 64px - 40px);
  overflow-y: auto;
}

.footer {
  text-align: center;
  padding: 10px;
  background: rgba(0,0,0,0.2);
  color: var(--text-secondary);
  font-size: 12px;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.info-item .label {
  color: var(--text-secondary);
}

.info-item .value {
  color: var(--primary-color);
  font-family: 'JetBrains Mono', monospace;
}

.packet-log {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
}

.packet-row {
  display: flex;
  gap: 12px;
  padding: 4px 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

.packet-row .timestamp {
  color: #555;
}

.packet-row .hex {
  color: var(--success-color);
}
</style>

<style scoped>
.main-container {
  display: flex;
  height: 100%;
  gap: 16px;
}

.left-panel {
  width: 380px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.right-panel {
  flex: 1;
  overflow-y: auto;
}

.status-section {
  flex-shrink: 0;
}

.tabs-section {
  flex: 1;
  background: var(--component-background);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
}

