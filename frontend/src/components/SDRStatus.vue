<template>
  <a-card title="SDR 运行状态" size="small" :bordered="false" class="sdr-status-card">
    <template #extra>
      <div class="status-tags">
        <a-tag :color="wsConnected ? 'success' : 'error'">
          {{ wsConnected ? '后台在线' : '后台离线' }}
        </a-tag>
        <a-tag :color="store.status.streaming ? 'processing' : 'default'" :class="{ 'streaming-active': store.status.streaming }">
          {{ store.status.streaming ? '正在串流' : '待机中' }}
        </a-tag>
      </div>
    </template>
    
    <a-descriptions size="small" :column="1" :colon="false">
      <a-descriptions-item label="硬件状态">
        <a-tag :color="store.status.connected ? 'green' : 'orange'" size="small">
          {{ store.status.connected ? 'SDR 已连接' : '模拟模式' }}
        </a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="中心频率">
        <span class="value">{{ (store.status.centerFreq / 1e6).toFixed(3) }}</span> <span class="unit">MHz</span>
      </a-descriptions-item>
      <a-descriptions-item label="采样率">
        <span class="value">{{ (store.status.sampleRate / 1e6).toFixed(1) }}</span> <span class="unit">Msps</span>
      </a-descriptions-item>
      <a-descriptions-item label="当前增益">
        <span class="value">{{ store.status.gain }}</span> <span class="unit">dB</span>
      </a-descriptions-item>
    </a-descriptions>
    
    <div class="controls">
      <a-button type="primary" block @click="toggleStream">
        <template #icon><component :is="store.status.streaming ? 'PauseOutlined' : 'CaretRightOutlined'" /></template>
        {{ store.status.streaming ? '停止串流' : '开启串流' }}
      </a-button>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useSDRStore } from '@/stores/sdrStore';
import { CaretRightOutlined, PauseOutlined } from '@ant-design/icons-vue';

const store = useSDRStore();

// WebSocket 连接状态（后台在线）
const wsConnected = computed(() => store.isConnected);

const toggleStream = async () => {
  const cmd = store.status.streaming ? 'stop_streaming' : 'start_streaming';
  await store.sendCommand(cmd, {});
  console.log('Toggle stream:', cmd);
};
</script>

<style scoped>
.sdr-status-card {
  height: 100%;
}
.status-tags {
  display: flex;
  gap: 4px;
}
.value {
  font-family: 'JetBrains Mono', monospace;
  font-weight: bold;
  font-size: 1.1em;
  color: var(--primary-color);
}
.unit {
  font-size: 0.8em;
  color: var(--text-secondary);
  margin-left: 4px;
}
.controls {
  margin-top: 16px;
}
:deep(.ant-descriptions-item-label) {
  width: 80px;
}
</style>
