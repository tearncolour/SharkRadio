<template>
  <a-card title="发射数据监控 (TX Monitor)" size="small" :bordered="false" class="tx-card">
    <div class="tx-container">
      
      <!-- TX Status Header -->
      <div class="status-row">
        <div class="status-indicator" :class="{ active: isTxActive }">
            <div class="led"></div>
            <span>{{ isTxActive ? 'TRANSMITTING' : 'TX STANDBY' }}</span>
        </div>
        <div class="param-tags">
             <a-tag color="red">{{ (config?.txConfig.centerFreq / 1e6).toFixed(3) }} MHz</a-tag>
             <a-tag color="orange">{{ (config?.txConfig.bandwidth / 1e6).toFixed(1) }} MHz BW</a-tag>
             <a-tag color="purple">{{ config?.txConfig.gain }} dB</a-tag>
        </div>
      </div>

      <a-divider style="margin: 12px 0" />

      <!-- Payload Display -->
      <div class="payload-section">
        <div class="section-label">正在发送的数据 (Current Payload):</div>
        
        <div v-if="currentSignalType === 'custom'" class="payload-box custom">
             <div class="empty-text">自定义信号模式 (CW/Tone) - 无数字 Payload</div>
        </div>

        <div v-else-if="payloadHex" class="payload-box">
             <div class="hex-grid">
               <span v-for="(byte, index) in payloadBytes" :key="index" class="byte" :class="{ 'highlight': index < 4 }">
                  {{ byte }}
               </span>
             </div>
             <div class="ascii-preview" v-if="payloadAscii">
                ASCII: {{ payloadAscii }}
             </div>
        </div>

        <div v-else class="payload-box empty">
             <div class="empty-text">暂无有效载荷配置</div>
        </div>
      </div>

    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useSDRStore } from '@/stores/sdrStore';

const store = useSDRStore();

// Get active tab config
const config = computed(() => store.activeTab);

// Determine if TX is ostensibly active (basic check based on streaming/mode)
// Ideally we need a specific 'isTxEmitting' flag from backend, 
// but 'isStreaming' + 'mode != rx' is a good proxy for now.
const isTxActive = computed(() => {
    return store.status.streaming && config.value?.mode !== 'rx';
});

const currentSignalType = computed(() => config.value?.txSignalType || 'custom');

const payloadHex = computed(() => {
    if (!config.value) return '';
    if (currentSignalType.value === 'custom') return '';
    
    // Broadcast Payload
    if (currentSignalType.value.includes('broadcast')) {
        return config.value.broadcastPayload || '';
    } 
    // Jamming Payload (convert ASCII to Hex for display consistency)
    else if (currentSignalType.value.includes('jam')) {
        const ascii = config.value.jammingPayload || '';
        let hex = '';
        for (let i = 0; i < ascii.length; i++) {
            hex += ascii.charCodeAt(i).toString(16).padStart(2, '0').toUpperCase();
        }
        return hex;
    }
    return '';
});

const payloadBytes = computed(() => {
    const hex = payloadHex.value;
    if (!hex) return [];
    return hex.match(/.{1,2}/g) || [];
});

const payloadAscii = computed(() => {
     if (currentSignalType.value.includes('jam')) {
         return config.value?.jammingPayload;
     }
     return null;
});

</script>

<style scoped>
.tx-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}
:deep(.ant-card-body) {
  flex: 1;
  padding: 16px;
  overflow: hidden;
}

.tx-container {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 700;
    color: var(--text-dim);
    background: rgba(255, 255, 255, 0.05);
    padding: 6px 12px;
    border-radius: 4px;
    transition: all 0.3s;
}

.status-indicator.active {
    background: rgba(255, 0, 0, 0.1);
    color: #ff4d4f;
    box-shadow: 0 0 10px rgba(255, 0, 0, 0.2);
}

.led {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #444;
}

.active .led {
    background: #ff4d4f;
    box-shadow: 0 0 8px #ff4d4f;
    animation: pulse 1s infinite;
}

.payload-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 0;
}

.section-label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.payload-box {
    flex: 1;
    background: #000;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 12px;
    font-family: 'JetBrains Mono', monospace;
    overflow-y: auto;
}

.payload-box.empty, .payload-box.custom {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
    font-size: 12px;
    font-style: italic;
}

.hex-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-content: flex-start;
}

.byte {
    display: inline-block;
    padding: 2px 4px;
    font-size: 13px;
    color: var(--primary-color);
    background: rgba(0, 242, 255, 0.05);
    border-radius: 2px;
}

.byte.highlight {
    color: #ffca28; /* Highlight header/important bytes */
    background: rgba(255, 202, 40, 0.1);
}

.ascii-preview {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px dashed var(--border-color);
    font-size: 12px;
    color: #ffd700;
}

@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}
</style>
