<template>
  <a-card title="SDR 设备选择" size="small" class="selector-card">
    <template #extra>
      <a-button type="link" size="small" @click="scanDevices" :loading="scanning">
        <template #icon><reload-outlined /></template>
        刷新设备
      </a-button>
    </template>
    
    <a-spin :spinning="scanning" tip="正在扫描设备...">
      <a-list 
        v-if="devices.length > 0"
        item-layout="horizontal" 
        :data-source="devices"
        size="small"
      >
        <template #renderItem="{ item }">
          <a-list-item 
            class="device-item"
            :class="{ 'selected': item.id === selectedDeviceId, 'unavailable': !item.is_available }"
          >
            <a-list-item-meta>
              <template #title>
                <div class="device-header">
                  <span class="device-name">{{ item.name }}</span>
                  <a-tag v-if="connectedDeviceIds.includes(item.id)" color="success">已连接</a-tag>
                  <a-tag v-else-if="!item.is_available" color="error">不可用</a-tag>
                </div>
              </template>
              <template #description>
                <span class="device-uri">{{ item.uri }}</span>
                <span v-if="item.serial" class="device-serial"> | SN: {{ item.serial }}</span>
              </template>
              <template #avatar>
                <a-avatar :style="{ background: getDeviceColor(item) }">
                  <template #icon><wifi-outlined /></template>
                </a-avatar>
              </template>
            </a-list-item-meta>
            <template #actions>
              <a-button 
                v-if="!connectedDeviceIds.includes(item.id)"
                type="primary" 
                size="small"
                :disabled="!item.is_available"
                @click="connectDevice(item.id)"
              >
                连接
              </a-button>
              <a-button 
                v-else
                danger 
                size="small"
                @click="disconnectDevice(item.id)"
              >
                断开
              </a-button>
              <a-button 
                v-if="connectedDeviceIds.includes(item.id)"
                type="link" 
                size="small"
                @click="selectDevice(item.id)"
              >
                选为活动
              </a-button>
            </template>
          </a-list-item>
        </template>
      </a-list>
      
      <a-empty v-else description="未检测到 SDR 设备">
        <a-button type="primary" @click="scanDevices">扫描设备</a-button>
      </a-empty>
    </a-spin>
  </a-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { WifiOutlined, ReloadOutlined } from '@ant-design/icons-vue';
import { useSDRStore } from '@/stores/sdrStore';

interface SDRDevice {
  id: string;
  name: string;
  uri: string;
  serial: string;
  product: string;
  is_available: boolean;
}

const store = useSDRStore();
const devices = ref<SDRDevice[]>([]);
const scanning = ref(false);
const selectedDeviceId = computed(() => store.activeDeviceId);
const connectedDeviceIds = computed(() => store.connectedDeviceIds);

const getDeviceColor = (device: SDRDevice) => {
  if (connectedDeviceIds.value.includes(device.id)) {
    return 'linear-gradient(135deg, #52c41a 0%, #95de64 100%)';
  }
  if (!device.is_available) {
    return 'linear-gradient(135deg, #434343 0%, #666666 100%)';
  }
  return 'linear-gradient(135deg, #1890ff 0%, #69c0ff 100%)';
};

const scanDevices = async () => {
  scanning.value = true;
  console.log('Scanning devices...');
  try {
    const result = await store.sendCommand('scan_devices', {});
    console.log('Scan result:', result);
    if (result.success && result.data) {
      devices.value = result.data;
    } else {
      console.error('Scan failed:', result.error);
    }
  } catch (e) {
    console.error('Scan exception:', e);
  } finally {
    scanning.value = false;
  }
};

const emit = defineEmits(['select']);

const connectDevice = async (deviceId: string) => {
  const result = await store.sendCommand('connect_device', { device_id: deviceId });
  if (result.success) {
    await scanDevices();
    // 自动为新连接的设备创建 tab
    const device = devices.value.find(d => d.id === deviceId);
    if (device) {
      store.createTab(device);
      emit('select', device);
    }
  }
};

const disconnectDevice = async (deviceId: string) => {
  const result = await store.sendCommand('disconnect_device', { device_id: deviceId });
  if (result.success) {
    await scanDevices();
    // 移除对应的 tab
    const tab = store.tabs.find(t => t.deviceId === deviceId);
    if (tab) {
      store.removeTab(tab.id);
    }
  }
};

const selectDevice = async (deviceId: string) => {
  // 旧逻辑保留，但在新UI中可能不常用了
  await store.sendCommand('select_device', { device_id: deviceId });
  // store.setActiveDevice(deviceId); // 已移除
};

onMounted(() => {
  scanDevices();
});
</script>

<style scoped>
.selector-card {
  margin-bottom: 16px;
}
.device-item {
  padding: 12px !important;
  border-radius: 8px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.3s ease;
}
.device-item:hover {
  background: rgba(255, 255, 255, 0.05);
}
.device-item.selected {
  border-left: 3px solid var(--primary-color);
}
.device-item.unavailable {
  opacity: 0.5;
}
.device-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.device-name {
  font-weight: 600;
  color: var(--text-color);
}
.device-uri {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text-secondary);
}
.device-serial {
  font-size: 11px;
  color: var(--text-secondary);
}
</style>
