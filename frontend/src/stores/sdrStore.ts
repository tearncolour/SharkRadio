import { defineStore } from 'pinia';
import { ref, computed, shallowRef } from 'vue';
import type { SDRStatus, SpectrumData, RadarTarget } from '@/types';
import type { SDRTab, SDRConfig, TxSignalType, RxSignalType } from '@/types/sdrTypes';

export interface SDRDevice {
  id: string;
  name: string;
  uri: string;
  serial: string;
  product: string;
  is_available: boolean;
}

export interface CommandResponse {
  cmd: string;
  success: boolean;
  data: any;
  error: string | null;
}

const DEFAULT_CONFIG: SDRConfig = {
  centerFreq: 433.5e6,
  sampleRate: 2e6,
  gain: 50,
  bandwidth: 4e6,
  gainMode: 'manual'
};

export const useSDRStore = defineStore('sdr', () => {
  // ============ 状态 ============
  
  // 标签页管理
  const tabs = ref<SDRTab[]>([]);
  const activeTabId = ref<string | null>(null);

  // 频谱数据 (使用 shallowRef 提升性能，避免大数组深度响应式)
  // Map: deviceId -> SpectrumData
  const spectrums = shallowRef<Record<string, SpectrumData>>({});
  // Compatibility computed for single-device views (returns data for active tab)
  const spectrum = computed(() => {
    if (activeTab.value && spectrums.value[activeTab.value.deviceId]) {
      return spectrums.value[activeTab.value.deviceId];
    }
    return { frequencies: [], power: [] };
  });

  // 运行时状态 (OVR/UND)
  // Map: deviceId -> Status
  const runtimeStatus = ref<Record<string, { overflow: boolean, underflow: boolean }>>({});
  
  // 雷达目标
  const targets = ref<RadarTarget[]>([]);
  
  // 多设备支持
  const devices = ref<SDRDevice[]>([]);
  const connectedDeviceIds = ref<string[]>([]);
  
  // WebSocket 相关
  const wsSocket = ref<WebSocket | null>(null);
  const isWsConnected = ref(false); // WebSocket 连接状态
  const pendingCommands = ref<Map<string, (response: CommandResponse) => void>>(new Map());
  
  // ============ 计算属性 ============
  
  const activeTab = computed(() => {
    return tabs.value.find(t => t.id === activeTabId.value) || null;
  });
  
  // 兼容旧代码的 status 对象
  const status = computed<SDRStatus>(() => {
    if (activeTab.value) {
      const mode = activeTab.value.mode;
      const config = mode === 'tx' ? activeTab.value.txConfig : activeTab.value.rxConfig;
      const devId = activeTab.value.deviceId;
      const rtStatus = runtimeStatus.value[devId] || { overflow: false, underflow: false };
      
      return {
        connected: true, // 如果有 tab 说明已连接
        streaming: activeTab.value.isStreaming, 
        centerFreq: config.centerFreq,
        sampleRate: config.sampleRate,
        gain: config.gain,
        overflow: rtStatus.overflow,
        underflow: rtStatus.underflow
      };
    }
    return {
      connected: false,
      streaming: false,
      centerFreq: 433.5e6,
      sampleRate: 2e6,
      gain: 50
    };
  });
  
  const isConnected = computed(() => isWsConnected.value);
  
  // ============ Actions ============
  
  function updateStatus(newStatus: Partial<SDRStatus>) {
    // 收到 WS 状态更新时的处理，暂时保留兼容
    if (newStatus.connected !== undefined) {
      // isWsConnected.value = newStatus.connected; // 这应该是 WS 连接状态
    }
  }
  
  function updateSpectrum(data: any) {
    // data should contain device_id
    const deviceId = data.device_id;
    if (!deviceId) return; // Ignore updates without device ID to prevent mixup
    
    // Update Spectrum
    if (data.frequencies && data.power) {
       // Create a copy or update reactive object
       const newSpectrums = { ...spectrums.value };
       newSpectrums[deviceId] = {
        frequencies: data.frequencies,
        power: data.power
       };
       spectrums.value = newSpectrums;
    }
    
    // Update Runtime Status
    if (typeof data.overflow === 'boolean' || typeof data.underflow === 'boolean') {
        const current = runtimeStatus.value[deviceId] || { overflow: false, underflow: false };
        if (typeof data.overflow === 'boolean') current.overflow = data.overflow;
        if (typeof data.underflow === 'boolean') current.underflow = data.underflow;
        runtimeStatus.value[deviceId] = current;
    }
  }
  
  function updateTargets(newTargets: RadarTarget[]) {
    targets.value = newTargets;
  }
  
  function setDevices(deviceList: SDRDevice[]) {
    devices.value = deviceList;
  }
  
  function createTab(device: SDRDevice, customName?: string) {
    const newTab: SDRTab = {
      id: `${device.id}_${Date.now()}`,
      deviceId: device.id,
      name: customName || device.name,
      mode: 'rx',
      rxConfig: { ...DEFAULT_CONFIG },
      txConfig: { ...DEFAULT_CONFIG, gain: -10 },
      isActive: true,
      isStreaming: false
    };
    
    tabs.value.push(newTab);
    activeTabId.value = newTab.id;
    
    if (!connectedDeviceIds.value.includes(device.id)) {
      connectedDeviceIds.value.push(device.id);
    }
  }
  
  function removeTab(tabId: string) {
    const index = tabs.value.findIndex(t => t.id === tabId);
    if (index > -1) {
      const tab = tabs.value[index];
      tabs.value.splice(index, 1);
      
      // 如果没有其他 tab 使用该设备，则移除已连接状态
      if (!tabs.value.some(t => t.deviceId === tab.deviceId)) {
        const devIndex = connectedDeviceIds.value.indexOf(tab.deviceId);
        if (devIndex > -1) connectedDeviceIds.value.splice(devIndex, 1);
      }
      
      // 更新活动 tab
      if (activeTabId.value === tabId) {
        activeTabId.value = tabs.value.length > 0 ? tabs.value[0].id : null;
      }
    }
  }
  
  function setActiveTab(tabId: string) {
    activeTabId.value = tabId;
  }
  
  function updateTabConfig(tabId: string, updates: Partial<SDRTab>) {
    const tab = tabs.value.find(t => t.id === tabId);
    if (tab) {
      Object.assign(tab, updates);
    }
  }

  
  // ============ WebSocket 通信 ============
  
  function setWebSocket(ws: WebSocket) {
    wsSocket.value = ws;
    
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        
        // 1. 检查是否是对某个命令的响应 (has cmd field)
        if (msg.cmd) {
            const cmdKey = msg.cmd;
            const resolver = pendingCommands.value.get(cmdKey);
            if (resolver) {
              resolver(msg as CommandResponse);
              pendingCommands.value.delete(cmdKey);
            }
        }
        
        // 2. 处理特殊消息类型 (broadcast messages)
        // 后端直接发送 { type: 'spectrum', frequencies: [], power: [] }
        if (msg.type === 'spectrum') {
          // DEBUG LOG
          // console.log('Store received spectrum:', msg.frequencies.length, 'points');
          updateSpectrum({
              frequencies: msg.frequencies, 
              power: msg.power
          });
        } else if (msg.type === 'status') {
          updateStatus(msg); // 假设 status 也是直接在 root
        } 
        
        // 兼容旧逻辑: { cmd: 'spectrum', data: ... }
        if (msg.cmd === 'spectrum' && msg.data) {
          updateSpectrum(msg.data);
        } else if (msg.cmd === 'status' && msg.data) {
          updateStatus(msg.data);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };
  }
  
  async function sendCommand(cmd: string, params: Record<string, any> = {}): Promise<CommandResponse> {
    return new Promise((resolve, reject) => {
      if (!wsSocket.value || wsSocket.value.readyState !== WebSocket.OPEN) {
        resolve({
          cmd,
          success: false,
          data: null,
          error: 'WebSocket 未连接'
        });
        return;
      }
      
      const message = JSON.stringify({ cmd, params });
      
      // 设置超时
      const timeout = setTimeout(() => {
        pendingCommands.value.delete(cmd);
        resolve({
          cmd,
          success: false,
          data: null,
          error: '命令超时'
        });
      }, 10000);
      
      // 注册响应处理器
      pendingCommands.value.set(cmd, (response) => {
        clearTimeout(timeout);
        resolve(response);
      });
      
      wsSocket.value.send(message);
    });
  }

  return {
    // 状态
    tabs,
    activeTabId,
    status,
    spectrum,
    targets,
    devices,
    connectedDeviceIds,
    
    // 计算属性
    activeTab,
    isConnected,
    
    // Actions
    createTab,
    removeTab,
    setActiveTab,
    updateTabConfig,
    updateStatus,
    updateSpectrum,
    updateTargets,
    setDevices,
    
    // WebSocket
    setWebSocket,
    sendCommand,
    isWsConnected
  };
});
