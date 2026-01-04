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
      <!-- 自定义标题栏 -->
      <TitleBar />
      
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
             <div class="tabs-section">
               <SDRTabs />
             </div>
          </div>
          
          <!-- 右侧: 动态视图 (频谱 / TX监控 / 分屏) -->
          <div class="right-panel">
            <component :is="activeViewComponent" class="dynamic-view" :class="{ 'split-view': viewMode === 'txrx' }">
              <template v-if="viewMode === 'txrx'">
                  <SpectrumView class="split-top" />
                  <TxDataView class="split-bottom" />
              </template>
            </component>
              
            <!-- 原始数据包日志 (仅在非纯TX模式下显示，或者一直显示？用户可能想看接收包) -->
            <!-- 逻辑: TX模式通常不看接收包，但如果只想看TX数据监控，也可以。 -->
            <!-- 为了保持界面整洁，TX模式下如果有 TXDataView 占据全屏，可能不需要这个 log，除非有分屏 -->
            <!-- 原始数据包日志 (始终显示，方便监控) -->
            <a-card :title="`收到的原始解码包 (Raw Packets) [${store.decodedPackets.length}]`" class="panel-card" style="min-height: 250px">
              <template #extra>
                <a-button type="link" size="small" @click="store.clearDecodedPackets()">清除日志</a-button>
              </template>
              <div class="packet-log">
                <a-empty v-if="store.decodedPackets.length === 0" description="暂未接收到符合 4-RRC-FSK 协议的数据包" />
                <div v-else v-for="(p, i) in store.decodedPackets" :key="i" class="packet-row">
                  <span class="timestamp">[{{ p.timestamp }}]</span>
                  <span class="hex">{{ p.hex }}</span>
                  <span class="packet-type" v-if="p.packetType !== 'unknown'">({{ p.packetType }})</span>
                </div>
              </div>
            </a-card>
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
import { ref, onMounted, computed } from 'vue';
import { useWebSocket } from '@/composables/useWebSocket';
import { WifiOutlined } from '@ant-design/icons-vue';
import { useSDRStore } from '@/stores/sdrStore';
import SDRTabs from '@/components/SDRTabs.vue';
import SpectrumView from '@/components/SpectrumView.vue';
import TxDataView from '@/components/TxDataView.vue';
import TitleBar from '@/components/TitleBar.vue';

const store = useSDRStore();
const { isConnected } = useWebSocket();
const packets = ref<{time: string, data: string}[]>([]);

// Dynamic View Logic
const viewMode = computed(() => {
    return store.activeTab?.mode || 'rx'; 
});

const activeViewComponent = computed(() => {
    if (viewMode.value === 'tx') return TxDataView;
    if (viewMode.value === 'rx') return SpectrumView;
    return 'div'; // Container for split view
});

onMounted(() => {
  console.log('SharkRadio 系统启动...');
});
</script>

<style scoped>
.layout {
  min-height: 100vh;
  background: var(--bg-color);
  font-family: 'Inter', sans-serif;
}

.header {
  height: 56px;
  background: rgba(10, 10, 12, 0.4);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  padding: 0 24px;
  z-index: 10;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 20px;
  color: var(--primary-color);
  filter: drop-shadow(0 0 8px var(--primary-glow));
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.header-divider {
  width: 1px;
  height: 20px;
  background: var(--border-color);
  margin: 0 20px;
}

.subtitle {
  color: var(--text-dim);
  font-size: 12px;
  letter-spacing: 0.5px;
  flex: 1;
}

.header-status {
  margin-left: auto;
}

.content-wrapper {
  padding: 16px;
  height: calc(100vh - 56px - 32px);
  overflow: hidden;
}

.footer {
  text-align: center;
  padding: 8px;
  background: transparent;
  color: var(--text-dim);
  font-size: 10px;
  border-top: 1px solid var(--border-color);
}

.packet-log {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  height: 200px;
  overflow-y: auto;
  background: rgba(0,0,0,0.2);
  padding: 8px;
  border-radius: 4px;
}

.packet-row {
  display: flex;
  gap: 12px;
  padding: 2px 0;
  border-bottom: 1px solid rgba(255,255,255,0.02);
}

.packet-row:last-child { border-bottom: none; }

.packet-row .timestamp {
  color: var(--text-dim);
}

.packet-row .hex {
  color: var(--success-color);
}

.main-container {
  display: flex;
  height: 100%;
  gap: 16px;
}

.left-panel {
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 350px;
  max-width: 450px;
  overflow-y: auto;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
  min-width: 0;
}

.tabs-section {
  flex: 1;
  background: var(--panel-bg);
  border-radius: var(--border-radius);
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(16px);
  overflow-y: auto;
  min-height: 0;
}


/* Dynamic View Styles */
.dynamic-view {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.split-view {
    flex-direction: row !important; /* Force horizontal split */
    gap: 12px;
}

.split-top, .split-bottom {
    flex: 1;
    min-height: 0;
    min-width: 0; /* Important for flex children scrolling */
}

:deep(.spectrum-card), :deep(.tx-card) {
    height: 100%;
}
</style>
