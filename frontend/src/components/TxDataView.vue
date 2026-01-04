<template>
  <a-card title="发射数据监控 (TX Monitor)" size="small" :bordered="false" class="tx-card">
    <template #extra>
      <div class="status-indicators">
        <!-- TX 模式下不显示 RX 溢出，只显示 TX 欠载 -->
        <a-tag :color="store.status.underflow ? '#faad14' : '#333'">UND</a-tag>
      </div>
    </template>
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
      <!-- TX Spectrum Preview -->
      <div class="spectrum-preview-section" v-if="hasTxData">
        <div class="section-label">发送信号预览 (TX Spectrum Expected):</div>
        <div class="chart-container">
           <v-chart class="chart" :option="chartOption" autoresize />
        </div>
      </div>
      <div v-else class="spectrum-preview-section empty">
         <div class="empty-text">等待发送... (启动 TX 后显示预览)</div>
      </div>

    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue';
import { useSDRStore } from '@/stores/sdrStore';

// ECharts
import VChart from 'vue-echarts';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, TitleComponent, DataZoomComponent } from 'echarts/components';

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, TitleComponent, DataZoomComponent]);


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

// TX Spectrum Chart Logic
const hasTxData = computed(() => {
    return store.txSpectrum.frequencies && store.txSpectrum.frequencies.length > 0;
});

const chartOption = computed(() => {
    const data = store.txSpectrum;
    if (!data.frequencies || data.frequencies.length === 0) return {};
    
    // Convert to Absolute Frequency (MHz)
    const centerFreqMHz = (config.value?.txConfig.centerFreq || 433.5e6) / 1e6;
    
    // X-Axis: Absolute Frequency
    const xData = data.frequencies.map(f => ((f / 1e6) + centerFreqMHz).toFixed(3));
    
    // Y-Axis: Adaptive Scale
    // Find peak power to set reasonable range
    const maxPower = Math.max(...data.power);
    const minPower = Math.max(maxPower - 80, -100); // Show dynamic range of 80dB or floor at -100

    return {
        animation: false,
        grid: {
            top: 30, right: 20, bottom: 25, left: 50,
            containLabel: true
        },
        tooltip: { 
            trigger: 'axis',
            formatter: (params: any) => {
                const pt = params[0];
                return `${pt.name} MHz<br/>Power: ${pt.value.toFixed(1)} dB`;
            }
        },
        xAxis: {
            type: 'category', 
            data: xData,
            name: 'Freq (MHz)',
            nameLocation: 'middle',
            nameGap: 25,
            axisLabel: { 
                showMaxLabel: true,
                interval: 'auto' 
            },
            axisTick: { alignWithLabel: true }
        },
        yAxis: {
            type: 'value',
            name: 'dB',
            min: Math.floor(minPower / 10) * 10,
            max: Math.ceil((maxPower + 5) / 10) * 10, // Add headroom
            splitLine: { lineStyle: { color: '#333' } }
        },
        series: [{
            type: 'line',
            data: data.power,
            smooth: true,
            symbol: 'none',
            lineStyle: { width: 1, color: '#00ff00' },
            areaStyle: { color: 'rgba(0, 255, 0, 0.1)' },
            markLine: {
                symbol: 'none',
                label: { formatter: 'CF', position: 'end' },
                lineStyle: { type: 'dashed', color: '#faad14' },
                data: [
                    { xAxis: xData.find(f => Math.abs(parseFloat(f) - centerFreqMHz) < 0.001) || '0' }
                ]
            }
        }]
    };
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
  display: flex;
  flex-direction: column;
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
    flex-shrink: 0;
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
    margin-top: 12px;
    flex-shrink: 0;
    max-height: 40%;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.spectrum-preview-section {
    flex: 1;
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 0;
    border-top: 1px dashed var(--border-color);
    padding-top: 12px;
}
.spectrum-preview-section.empty {
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
    font-style: italic;
}

.chart-container {
    flex: 1;
    min-height: 0;
    background: #000;
    border-radius: 4px;
    position: relative;
    overflow: hidden;
}

.chart {
    width: 100%;
    height: 100%;
}

.section-label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.payload-box {
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
    padding: 24px;
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
