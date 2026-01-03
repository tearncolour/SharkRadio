<template>
  <div class="config-container">
    <div class="device-header">
      <div class="device-info">
        <span class="device-name">{{ config.name || currentDevice?.name || 'Unknown Device' }}</span>
        <a-tag v-if="isConnected" color="success">已连接</a-tag>
        <a-tag v-else color="error">未连接</a-tag>
      </div>
      <a-button type="link" size="small" @click="renameDevice">重命名</a-button>
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
            <a-select-option value="red_parse">红方广播解析 (433.2 MHz)</a-select-option>
            <a-select-option value="blue_parse">蓝方广播解析 (433.92 MHz)</a-select-option>
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
            <a-select-option value="red_broadcast">红方标记广播</a-select-option>
            <a-select-option value="blue_broadcast">蓝方标记广播</a-select-option>
            <a-select-option value="jam_1">一类干扰波</a-select-option>
            <a-select-option value="jam_2">二类干扰波</a-select-option>
            <a-select-option value="jam_3">三类干扰波</a-select-option>
          </a-select>
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
              />
            </a-form-item>
          </a-col>
        </a-row>
        
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
            停止
          </a-button>
        </a-space>
      </a-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useSDRStore } from '@/stores/sdrStore';
import { message } from 'ant-design-vue';
import type { SDRTab, TxSignalType, RxSignalType } from '@/types/sdrTypes';

const props = defineProps<{
  tabId: string;
}>();

const store = useSDRStore();
const txEnabled = ref(false);

// 直接从 store 获取 tab 数据引用
const config = computed(() => store.tabs.find(t => t.id === props.tabId)!);
const currentDevice = computed(() => store.devices.find(d => d.id === config.value?.deviceId));
const isConnected = computed(() => store.connectedDeviceIds.includes(config.value?.deviceId || ''));

// 显示用的频率变量 (MHz)
const rxFreqDisplay = ref(433.5);
const txFreqDisplay = ref(433.5);

// 监听 config 变化更新显示频率
watch(() => config.value?.rxConfig.centerFreq, (val) => {
  if (val) rxFreqDisplay.value = val / 1e6;
}, { immediate: true });

watch(() => config.value?.txConfig.centerFreq, (val) => {
  if (val) txFreqDisplay.value = val / 1e6;
}, { immediate: true });

const onFreqChange = (type: 'rx' | 'tx') => {
  if (!config.value) return;
  if (type === 'rx') {
    config.value.rxConfig.centerFreq = rxFreqDisplay.value * 1e6;
  } else {
    config.value.txConfig.centerFreq = txFreqDisplay.value * 1e6;
  }
  updateConfig();
};

const updateConfig = () => {
  store.updateTabConfig(props.tabId, { ...config.value });
};

const renameDevice = () => {
  const newName = prompt('输入新名称', config.value.name);
  if (newName) {
    config.value.name = newName;
    updateConfig();
  }
};

const onRxSignalTypeChange = (val: RxSignalType) => {
  if (!config.value) return;
  
  if (val === 'red_parse') {
    config.value.rxConfig.centerFreq = 433.2e6;
    config.value.rxConfig.bandwidth = 2e6;
  } else if (val === 'blue_parse') {
    config.value.rxConfig.centerFreq = 433.92e6;
    config.value.rxConfig.bandwidth = 2e6;
  }
  updateConfig();
};

const onTxSignalTypeChange = (val: TxSignalType) => {
  if (!config.value) return;
  
  if (val === 'red_broadcast') {
    config.value.txConfig.centerFreq = 433.2e6;
  } else if (val === 'blue_broadcast') {
    config.value.txConfig.centerFreq = 433.92e6;
  }
  // 干扰波频率根据规则设定，暂时设为默认
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
  
  // 先应用 TX 配置
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
    // 如果是广播模式，可以在这里给后端发指令开始发送特定序列
    if (config.value.txSignalType !== 'custom') {
        store.sendCommand('start_tx_signal', {
            device_id: config.value.deviceId,
            signal_type: config.value.txSignalType
        });
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
</script>

<style scoped>
.config-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.device-name {
  font-weight: bold;
  font-size: 14px;
  margin-right: 8px;
}
.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
}
.mode-selector {
  display: flex;
  justify-content: center;
}
:deep(.ant-form-item) {
  margin-bottom: 8px;
}
</style>
