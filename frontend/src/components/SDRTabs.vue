<template>
  <div class="sdr-tabs-container">
    <a-tabs 
      v-if="store.tabs.length > 0"
      v-model:activeKey="activeKey" 
      type="editable-card" 
      size="small"
      @edit="onEdit"
      @change="onTabChange"
      class="sdr-tabs"
    >
      <a-tab-pane 
        v-for="tab in store.tabs" 
        :key="tab.id" 
        :tab="tab.name" 
        :closable="true"
      >
        <div class="tab-content">
          <SDRConfig :tabId="tab.id" />
        </div>
      </a-tab-pane>
      
      <template #addIcon>
        <a-button type="link" size="small" @click="showAddDevice">
          <plus-outlined /> 添加设备
        </a-button>
      </template>
    </a-tabs>
    
    <div v-if="store.tabs.length === 0" class="empty-state">
      <a-empty description="未连接 SDR 设备">
        <a-button type="primary" @click="showAddDevice">添加设备</a-button>
      </a-empty>
    </div>
    
    <!-- 添加设备弹窗 -->
    <a-modal
      v-model:open="isAddDeviceVisible"
      title="添加 SDR 设备"
      :footer="null"
      width="600px"
    >
      <SDRSelector @select="onDeviceSelected" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { useSDRStore } from '@/stores/sdrStore';
import { PlusOutlined } from '@ant-design/icons-vue';
import SDRSelector from './SDRSelector.vue';
import SDRConfig from './SDRConfig.vue';

const store = useSDRStore();
const activeKey = ref<string>(store.activeTabId || '');
const isAddDeviceVisible = ref(false);

watch(() => store.activeTabId, (val) => {
  if (val) activeKey.value = val;
});

const onEdit = (targetKey: string | MouseEvent, action: 'add' | 'remove') => {
  if (action === 'add') {
    showAddDevice();
  } else {
    removeTab(targetKey as string);
  }
};

const onTabChange = (key: string) => {
  store.setActiveTab(key);
};

const showAddDevice = () => {
  isAddDeviceVisible.value = true;
};

const removeTab = async (key: string) => {
  const tab = store.tabs.find(t => t.id === key);
  if (tab) {
    // 发送断开命令
    // 这里需要注意：如果是最后一个使用该设备的 tab，才断开物理连接
    // 现阶段简化处理，直接断开
    await store.sendCommand('disconnect_device', { device_id: tab.deviceId });
    store.removeTab(key);
  }
};

const onDeviceSelected = (device: any) => {
  // SDRSelector 会触发事件，我们在那里处理连接
  isAddDeviceVisible.value = false;
};

// 初始加载
onMounted(() => {
  if (store.tabs.length > 0 && !activeKey.value) {
    activeKey.value = store.tabs[0].id;
  }
});
</script>

<style scoped>
.sdr-tabs-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.sdr-tabs {
  flex: 1;
}
.empty-state {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: var(--glass-bg);
  border-radius: var(--border-radius);
  border: 1px dashed var(--border-color);
  min-height: 400px;
  margin: 16px;
}
/* Customize Tabs for Dark Theme */
:deep(.ant-tabs-nav) {
  margin-bottom: 0 !important;
  border-bottom: 1px solid var(--border-color);
}
:deep(.ant-tabs-tab) {
  background: transparent !important;
  border: none !important;
  border-right: 1px solid var(--border-color) !important;
  margin: 0 !important;
  color: var(--text-secondary) !important;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  border-radius: 0 !important;
  transition: all 0.3s;
}
:deep(.ant-tabs-tab-active) {
  background: rgba(0, 242, 255, 0.05) !important;
  color: var(--primary-color) !important;
  border-bottom: 2px solid var(--primary-color) !important;
}
:deep(.ant-tabs-content-holder) {
  padding: 0;
  border-left: 1px solid var(--border-color);
  border-right: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
  border-radius: 0 0 var(--border-radius) var(--border-radius);
  background: rgba(0,0,0,0.2);
}
:deep(.ant-tabs-nav-add) {
    border: none !important;
    color: var(--primary-color) !important;
}
</style>
