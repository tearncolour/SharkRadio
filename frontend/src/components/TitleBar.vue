<template>
  <div class="title-bar">
    <div class="title-drag-region">
      <div class="app-icon">
        <wifi-outlined />
      </div>
      <span class="app-title">SharkRadio</span>
    </div>
    
    <div class="window-controls">
      <div class="control-btn minimize" @click="minimize">
        <minus-outlined />
      </div>
      <div class="control-btn maximize" @click="maximize">
        <border-outlined v-if="!isMaximized" />
        <switcher-outlined v-else />
      </div>
      <div class="control-btn close" @click="close">
        <close-outlined />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { 
  WifiOutlined, 
  MinusOutlined, 
  BorderOutlined, 
  SwitcherOutlined, 
  CloseOutlined 
} from '@ant-design/icons-vue';

const isMaximized = ref(false);

const minimize = () => {
  (window as any).electronAPI?.minimize();
};

const maximize = () => {
  (window as any).electronAPI?.maximize();
  // We can't synchronously successfully know the state here without IPC roundtrip,
  // but usually simple toggle logic update happens via event listener
};

const close = () => {
  (window as any).electronAPI?.close();
};

onMounted(() => {
  if ((window as any).electronAPI?.onMaximizeStatusChange) {
      (window as any).electronAPI.onMaximizeStatusChange((status: boolean) => {
          isMaximized.value = status;
      });
  }
});
</script>

<style scoped>
.title-bar {
  height: 32px;
  background: #141414;
  display: flex;
  justify-content: space-between;
  align-items: center;
  user-select: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.title-drag-region {
  flex: 1;
  height: 100%;
  display: flex;
  align-items: center;
  -webkit-app-region: drag; /* Electron drag property */
  padding-left: 12px;
  gap: 8px;
}

.app-icon {
  color: var(--primary-color);
  font-size: 14px;
  display: flex;
  align-items: center;
}

.app-title {
  color: #ccc;
  font-size: 12px;
  font-family: 'Inter', sans-serif;
  font-weight: 500;
}

.window-controls {
  display: flex;
  height: 100%;
  -webkit-app-region: no-drag; /* Ensure buttons are clickable */
}

.control-btn {
  width: 46px;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #ccc;
  font-size: 10px;
  cursor: pointer;
  transition: background 0.2s;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.control-btn.close:hover {
  background: #e81123;
  color: white;
}
</style>
