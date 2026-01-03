<template>
  <a-card title="雷达标记进度" size="small" class="progress-card">
    <a-list item-layout="horizontal" :data-source="store.targets">
      <template #renderItem="{ item }">
        <a-list-item class="target-item">
          <a-list-item-meta>
            <template #title>
              <div class="progress-header">
                <span class="target-id">目标 #{{ item.id }}</span>
                <span class="target-type" :class="item.type">
                  {{ item.type === 'enemy' ? '敌方单位' : '我方单位' }}
                </span>
              </div>
            </template>
            <template #description>
              <div class="progress-content">
                <a-progress 
                  :percent="Math.min(100, (item.progress / 150) * 100)" 
                  :format="() => `${item.progress.toFixed(1)} / 150`"
                  :status="getProgressStatus(item.progress)"
                  stroke-color="#00e5ff"
                  trail-color="rgba(255,255,255,0.05)"
                />
              </div>
            </template>
            <template #avatar>
              <a-avatar 
                :size="40" 
                :style="{ background: getAvatarColor(item.type) }"
                class="target-avatar"
              >
                {{ item.type === 'enemy' ? '敌' : '我' }}
              </a-avatar>
            </template>
          </a-list-item-meta>
        </a-list-item>
      </template>
      <template #emptyText>
        <div class="empty-state">
          <wifi-outlined style="font-size: 32px; opacity: 0.2; margin-bottom: 8px" />
          <p>未检测到目标信号</p>
        </div>
      </template>
    </a-list>
  </a-card>
</template>

<script setup lang="ts">
import { useSDRStore } from '@/stores/sdrStore';
import { WifiOutlined } from '@ant-design/icons-vue';

const store = useSDRStore();

const getAvatarColor = (type: string) => {
  return type === 'enemy' 
    ? 'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)' 
    : 'linear-gradient(135deg, #52c41a 0%, #95de64 100%)';
};

const getProgressStatus = (progress: number) => {
  if (progress >= 135) return 'exception'; // 近乎标记完成
  if (progress >= 100) return 'active';
  return 'normal';
};
</script>

<style scoped>
.progress-card {
  margin-top: 16px;
  max-height: 485px;
  overflow-y: auto;
}
.target-item {
  padding: 12px !important;
  border-bottom: 1px solid rgba(255,255,255,0.05) !important;
}
.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.target-id {
  font-weight: bold;
  color: var(--text-color);
}
.target-type {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
}
.target-type.enemy {
  background: rgba(255, 77, 79, 0.15);
  color: #ff4d4f;
}
.target-type.ally {
  background: rgba(82, 196, 26, 0.15);
  color: #52c41a;
}
.target-avatar {
  border: 1px solid rgba(255,255,255,0.1);
}
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}
:deep(.ant-progress-text) {
  color: var(--text-color) !important;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}
</style>
