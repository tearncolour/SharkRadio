<template>
  <div class="config-container">
    <div class="device-header">
      <div class="device-info">
        <span class="device-name">{{ config.name || currentDevice?.name || 'Unknown Device' }}</span>
        <a-tag v-if="isConnected" color="success">已连接</a-tag>
        <a-tag v-else color="error">未连接</a-tag>
        <a-tag :color="store.status.streaming ? 'processing' : 'default'" class="status-tag">
          {{ store.status.streaming ? '串流中' : '待机' }}
        </a-tag>
      </div>
      <div class="header-actions">
        <a-button type="link" size="small" @click="renameDevice">重命名</a-button>
        <a-button type="primary" size="small" :danger="store.status.streaming" @click="toggleStream">
           {{ store.status.streaming ? '停止' : '启动' }}
        </a-button>
      </div>
    </div>
    
    <!-- 实时状态信息 -->
    <div class="status-grid" v-if="isConnected">
       <div class="status-item">
         <span class="label">采样率</span>
         <span class="value">{{ (store.status.sampleRate / 1e6).toFixed(1) }} M</span>
       </div>
       <div class="status-item">
         <span class="label">实际频率</span>
         <span class="value">{{ (store.status.centerFreq / 1e6).toFixed(3) }} MHz</span>
       </div>
       <div class="status-item">
         <span class="label">RSSI</span>
         <span class="value">-</span>
       </div>
    </div>

    <!-- 工作模式选择 -->
    <div class="mode-selector">
      <a-radio-group v-model:value="config.mode" button-style="solid" size="small" @change="updateConfig">
        <a-radio-button value="rx">仅接收</a-radio-button>
        <a-radio-button value="tx">仅发射</a-radio-button>
        <a-radio-button value="txrx">收发模式</a-radio-button>
      </a-radio-group>
    </div>

    <a-divider style="margin: 12px 0" />

    <!-- 接收配置 -->
    <div v-if="config.mode !== 'tx'" class="section">
      <div class="section-title">接收 (RX) 设置</div>
      
      <a-form layout="vertical" size="small">
        <a-form-item label="信号类型">
          <a-select v-model:value="config.rxSignalType" @change="onRxSignalTypeChange">
            <a-select-option value="custom">自定义</a-select-option>
            <a-select-opt-group label="红方信号">
              <a-select-option value="red_broadcast">红方广播 (433.20 MHz, 250k)</a-select-option>
              <a-select-option value="red_jam_1">红方干扰1 (432.20 MHz, 500k)</a-select-option>
              <a-select-option value="red_jam_2">红方干扰2 (432.60 MHz, 285k)</a-select-option>
              <a-select-option value="red_jam_3">红方干扰3 (433.20 MHz, 200k)</a-select-option>
            </a-select-opt-group>
            <a-select-opt-group label="蓝方信号">
              <a-select-option value="blue_broadcast">蓝方广播 (433.92 MHz, 250k)</a-select-option>
              <a-select-option value="blue_jam_1">蓝方干扰1 (434.92 MHz, 500k)</a-select-option>
              <a-select-option value="blue_jam_2">蓝方干扰2 (434.52 MHz, 285k)</a-select-option>
              <a-select-option value="blue_jam_3">蓝方干扰3 (433.92 MHz, 200k)</a-select-option>
            </a-select-opt-group>
          </a-select>
        </a-form-item>

        <a-row :gutter="8">
          <a-col :span="12">
            <a-form-item label="中心频率 (MHz)">
              <a-input-number 
                v-model:value="rxFreqDisplay" 
                :min="70" :max="6000" :step="0.1"
                style="width: 100%"
                :disabled="config.rxSignalType !== 'custom'"
                @change="onFreqChange('rx')"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="增益 (dB)">
              <a-input-number 
                v-model:value="config.rxConfig.gain" 
                :min="0" :max="73"
                style="width: 100%"
                @change="updateConfig"
              />
            </a-form-item>
          </a-col>
        </a-row>
        
        <a-form-item label="RF 带宽">
          <a-select v-model:value="config.rxConfig.bandwidth" @change="updateConfig">
            <a-select-option :value="200000">0.2 MHz</a-select-option>
            <a-select-option :value="1000000">1.0 MHz</a-select-option>
            <a-select-option :value="2000000">2.0 MHz</a-select-option>
            <a-select-option :value="4000000">4.0 MHz</a-select-option>
          </a-select>
        </a-form-item>
        
        <div class="action-buttons">
          <a-button type="primary" size="small" block @click="applyRxConfig">应用 RX 配置</a-button>
        </div>
      </a-form>
    </div>

    <!-- 发射配置 -->
    <div v-if="config.mode !== 'rx'" class="section">
      <a-divider style="margin: 12px 0" />
      <div class="section-title">发射 (TX) 设置</div>

      <a-form layout="vertical" size="small">
        <a-form-item label="信号类型">
          <a-select v-model:value="config.txSignalType" @change="onTxSignalTypeChange">
            <a-select-option value="custom">自定义</a-select-option>
            <a-select-option value="red_broadcast">红方广播源</a-select-option>
            <a-select-option value="red_jam_1">红方一级干扰源</a-select-option>
            <a-select-option value="red_jam_2">红方二级干扰源</a-select-option>
            <a-select-option value="red_jam_3">红方三级干扰源</a-select-option>
            <a-select-option value="blue_broadcast">蓝方广播源</a-select-option>
            <a-select-option value="blue_jam_1">蓝方一级干扰源</a-select-option>
            <a-select-option value="blue_jam_2">蓝方二级干扰源</a-select-option>
            <a-select-option value="blue_jam_3">蓝方三级干扰源</a-select-option>
          </a-select>
        </a-form-item>

        <!-- 干扰源配置 -->
        <a-form-item label="干扰字符 (6位 ASCII)" v-if="isJamming">
           <a-input 
             v-model:value="config.jammingPayload" 
             :maxlength="6"
             placeholder="例如: ABCDEF"
             @change="updateConfig"
           >
             <template #suffix>
               <span style="font-size: 10px; color: #666">{{ (config.jammingPayload || '').length }}/6</span>
             </template>
           </a-input>
        </a-form-item>

        <!-- 广播源配置 -->
        <a-form-item label="广播数据配置" v-if="isBroadcast">
            <a-button size="small" block @click="openBroadcastConfig" style="margin-bottom: 8px">
                设置 Payload ({{ (config.broadcastPayload || '').length / 2 }} 字节)
            </a-button>
            <div v-if="config.broadcastPayload" class="payload-display">
                <div class="label">当前 Payload (Hex):</div>
                <div class="value">{{ config.broadcastPayload }}</div>
            </div>
        </a-form-item>

        <a-row :gutter="8">
          <a-col :span="12">
            <a-form-item label="发射频率 (MHz)">
              <a-input-number 
                v-model:value="txFreqDisplay" 
                :min="70" :max="6000" :step="0.1"
                style="width: 100%"
                :disabled="config.txSignalType !== 'custom'"
                @change="onFreqChange('tx')"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="发射功率 (dB)">
              <a-input-number 
                v-model:value="config.txConfig.gain" 
                :min="-89" :max="0"
                style="width: 100%"
                @change="updateConfig"
                :disabled="config.txSignalType !== 'custom'"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="发射带宽 (MHz)">
          <a-input-number 
            v-model:value="txBwDisplay" 
            :min="0.2" :max="6.0" :step="0.01"
            style="width: 100%"
            :disabled="config.txSignalType !== 'custom'"
            @change="onBwChange"
          />
        </a-form-item>
        
        <a-space style="width: 100%">
          <a-button 
            type="primary" 
            danger 
            block 
            size="small"
            @click="enableTx" 
            :disabled="txEnabled"
          >
            启用 TX
          </a-button>
          <a-button 
            block 
            size="small"
            @click="disableTx" 
            :disabled="!txEnabled"
          >
            停止 TX
          </a-button>
        </a-space>
      </a-form>
    </div>
    <a-modal
      v-model:open="renameModalVisible"
      title="重命名设备"
      @ok="handleRename"
    >
      <a-input v-model:value="newDeviceName" placeholder="请输入新的设备名称" @pressEnter="handleRename" />
    </a-modal>

    <BroadcastConfigModal 
      v-model:visible="broadcastModalVisible"
      v-model:modelValue="config.broadcastPayload"
      :signalType="config.signalType"
      @confirm="updateConfig"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useSDRStore } from '@/stores/sdrStore';
import { message } from 'ant-design-vue';
import type { SDRTab, TxSignalType, RxSignalType } from '@/types/sdrTypes';
import BroadcastConfigModal from './BroadcastConfigModal.vue';

const props = defineProps<{
  tabId: string;
}>();

const store = useSDRStore();
const txEnabled = ref(false);

const renameModalVisible = ref(false);
const broadcastModalVisible = ref(false);
const newDeviceName = ref('');

// 直接从 store 获取 tab 数据引用
const config = computed(() => store.tabs.find(t => t.id === props.tabId)!);
const currentDevice = computed(() => store.devices.find(d => d.id === config.value?.deviceId));
const isConnected = computed(() => store.connectedDeviceIds.includes(config.value?.deviceId || ''));
const isStreaming = computed(() => store.status.streaming); // 暂用全局状态，后续应改为 tab 独立状态

const isJamming = computed(() => config.value?.txSignalType?.includes('jam'));
const isBroadcast = computed(() => config.value?.txSignalType?.includes('broadcast'));

const openBroadcastConfig = () => {
    broadcastModalVisible.value = true;
};

// 显示用的频率变量 (MHz)
// ... existing refs
const rxFreqDisplay = ref(433.5);
const txFreqDisplay = ref(433.5);
const txBwDisplay = ref(2.0);

// 监听 config 变化更新显示频率
watch(() => config.value?.rxConfig.centerFreq, (val) => {
  if (val) rxFreqDisplay.value = val / 1e6;
}, { immediate: true });

watch(() => config.value?.txConfig.centerFreq, (val) => {
  if (val) txFreqDisplay.value = val / 1e6;
}, { immediate: true });

watch(() => config.value?.txConfig.bandwidth, (val) => {
  if (val) txBwDisplay.value = val / 1e6;
}, { immediate: true });

const renameDevice = () => {
  if (config.value) {
    newDeviceName.value = config.value.name;
    renameModalVisible.value = true;
  }
};

const handleRename = () => {
  if (newDeviceName.value && config.value) {
    config.value.name = newDeviceName.value;
    updateConfig();
    renameModalVisible.value = false;
    message.success('重命名成功');
  }
};

const onFreqChange = (type: 'rx' | 'tx') => {
  if (!config.value) return;
  if (type === 'rx') {
    config.value.rxConfig.centerFreq = rxFreqDisplay.value * 1e6;
  } else {
    config.value.txConfig.centerFreq = txFreqDisplay.value * 1e6;
  }
  updateConfig();
};

const onBwChange = () => {
    if (!config.value) return;
    config.value.txConfig.bandwidth = txBwDisplay.value * 1e6;
    updateConfig();
};

const updateConfig = () => {
  store.updateTabConfig(props.tabId, { ...config.value });
};

const onRxSignalTypeChange = (val: RxSignalType) => {
  if (!config.value) return;
  
  // 信号参数: 频率 (MHz), 带宽 (MHz)
  const signalParams: Record<string, { freq: number; bw: number }> = {
    'red_broadcast':  { freq: 433.20, bw: 0.54 },
    'red_jam_1':      { freq: 432.20, bw: 1.04 },
    'red_jam_2':      { freq: 432.60, bw: 0.61 },
    'red_jam_3':      { freq: 433.20, bw: 0.44 },
    'blue_broadcast': { freq: 433.92, bw: 0.54 },
    'blue_jam_1':     { freq: 434.92, bw: 1.04 },
    'blue_jam_2':     { freq: 434.52, bw: 0.61 },
    'blue_jam_3':     { freq: 433.92, bw: 0.44 },
  };
  
  const params = signalParams[val];
  if (params) {
    config.value.rxConfig.centerFreq = params.freq * 1e6;
    config.value.rxConfig.bandwidth = Math.max(params.bw * 1e6, 1e6); // 最小 1MHz 带宽确保信号可见
  }
  updateConfig();
};

const onTxSignalTypeChange = (val: TxSignalType) => {
  if (!config.value) return;
  // ... parameters logic ... 
  const setParams = (freq: number, bw: number, gain: number) => {
      config.value.txConfig.centerFreq = freq * 1e6;
      config.value.txConfig.bandwidth = bw * 1e6;
      
      let finalGain = gain;
      if (finalGain > 0) finalGain = 0;
      if (finalGain < -89) finalGain = -89;
      config.value.txConfig.gain = finalGain;
  };

  switch (val) {
      case 'red_broadcast': setParams(433.2, 0.54, -60); break;
      case 'red_jam_1': setParams(432.2, 1.04, -10); break;
      case 'red_jam_2': setParams(432.6, 0.61, 0); break;
      case 'red_jam_3': setParams(433.2, 0.44, -10); break;
      case 'blue_broadcast': setParams(433.92, 0.54, -60); break;
      case 'blue_jam_1': setParams(434.92, 1.04, -10); break;
      case 'blue_jam_2': setParams(434.52, 0.61, 0); break;
      case 'blue_jam_3': setParams(433.92, 0.44, -10); break;
  }
  updateConfig();
};

const applyRxConfig = async () => {
  if (!config.value) return;
  const result = await store.sendCommand('configure_device', {
    device_id: config.value.deviceId,
    rx_config: {
      center_freq: config.value.rxConfig.centerFreq,
      gain: config.value.rxConfig.gain,
      bandwidth: config.value.rxConfig.bandwidth,
      gain_mode: config.value.rxConfig.gainMode || 'manual'
    }
  });

  if (result.success) {
    message.success('RX 配置已应用');
  } else {
    message.error(result.error || '配置失败');
  }
};

const enableTx = async () => {
  if (!config.value) return;
  await store.sendCommand('configure_device', {
    device_id: config.value.deviceId,
    tx_config: {
      center_freq: config.value.txConfig.centerFreq,
      gain: config.value.txConfig.gain,
      bandwidth: config.value.txConfig.bandwidth
    }
  });
  const result = await store.sendCommand('enable_tx', {
    device_id: config.value.deviceId
  });
  if (result.success) {
    txEnabled.value = true;
    message.success('TX 已启用');
    if (config.value.txSignalType !== 'custom') {
        // 根据信号类型选择正确的载荷
        let payload: string | undefined;
        if (config.value.txSignalType.includes('broadcast')) {
            payload = config.value.broadcastPayload;
        } else if (config.value.txSignalType.includes('jam')) {
            payload = config.value.jammingPayload;
        }
            
        store.startTxSignal(
            config.value.deviceId, 
            config.value.txSignalType,
            payload
        );
    }
  } else {
    message.error(result.error || '启用 TX 失败');
  }
};

const disableTx = async () => {
  if (!config.value) return;
  const result = await store.sendCommand('disable_tx', {
    device_id: config.value.deviceId
  });
  if (result.success) {
    txEnabled.value = false;
    message.success('TX 已禁用');
  } else {
    message.error(result.error || '禁用 TX 失败');
  }
};

const toggleStream = async () => {
    if (!config.value) return;
    const currentState = config.value.isStreaming;
    const cmd = currentState ? 'stop_streaming' : 'start_streaming';
    
    // 构建命令参数
    const params: Record<string, any> = {
        device_id: config.value.deviceId
    };
    
    // 启动时传递信号类型
    if (!currentState && config.value.rxSignalType && config.value.rxSignalType !== 'custom') {
        params.signal_type = config.value.rxSignalType;
    }
    
    const result = await store.sendCommand(cmd, params);
    
    if (result.success) {
        store.updateTabConfig(props.tabId, { isStreaming: !currentState });
        message.success(currentState ? '已停止串流' : '开始串流');
    } else {
        message.error(result.error || '操作失败');
    }
};
</script>

<style scoped>
.config-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 4px;
}
.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}
.device-info {
    display: flex;
    align-items: center;
    gap: 8px;
}
.device-name {
  font-weight: 700;
  font-size: 14px;
  color: var(--text-main);
}
.status-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 16px;
    background: rgba(0,0,0,0.2);
    padding: 12px;
    border-radius: var(--border-radius);
    border: 1px solid var(--border-color);
}
.status-item {
    display: flex;
    flex-direction: column;
    align-items: center;
}
.status-item .label {
    font-size: 10px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.status-item .value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: var(--primary-color);
    font-weight: 600;
}
.section {
    animation: fadeIn 0.3s ease-out;
}
.section-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-dim);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border-color);
    margin-left: 8px;
}
.mode-selector {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}
:deep(.ant-radio-button-wrapper) {
    background: transparent;
    border-color: var(--border-color);
    color: var(--text-secondary);
}
:deep(.ant-radio-button-wrapper-checked) {
    background: rgba(0, 242, 255, 0.1) !important;
    border-color: var(--primary-color) !important;
    color: var(--primary-color) !important;
    box-shadow: none !important;
}
:deep(.ant-form-item) {
  margin-bottom: 12px;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}

.payload-display {
    background: rgba(0, 0, 0, 0.3);
    padding: 8px;
    border-radius: var(--border-radius);
    border: 1px dashed var(--border-color);
}
.payload-display .label {
    font-size: 10px;
    color: var(--text-dim);
    margin-bottom: 4px;
}
.payload-display .value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--primary-color);
    word-break: break-all;
    line-height: 1.4;
}
</style>
