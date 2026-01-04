<template>
  <a-modal
    :open="visible"
    title="广播数据配置 (协议 1.6 - 雷达电磁波)"
    @ok="handleOk"
    @cancel="handleCancel"
    width="800px"
  >
    <a-alert 
      message="参考《RoboMaster 2026 机甲大师高校系列赛通信协议 V1.1.0》第 1.6 节" 
      description="雷达无线通信协议：包括发送频率、带宽及 Payload 结构。"
      type="info" 
      show-icon 
      style="margin-bottom: 24px" 
    />
    
    <div class="protocol-section">
      <div class="section-title">物理层参数 (Physical Layer)</div>
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="发送频率 (Frequency)" help="红方: 433.20 MHz | 蓝方: 433.92 MHz">
            <a-select v-model:value="protocolConfig.frequency" style="width: 100%">
               <a-select-option value="433.20">433.20 MHz (Red)</a-select-option>
               <a-select-option value="433.92">433.92 MHz (Blue)</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="带宽 (Bandwidth)" help="标准: 500 kHz / 扩频因子: 7 / 编码率: 4/5">
             <a-input v-model:value="protocolConfig.bandwidth" readonly />
          </a-form-item>
        </a-col>
      </a-row>
    </div>

    <a-tabs v-model:activeKey="activeTab">
      <!-- 0x0A01: 对方机器人位置 -->
      <a-tab-pane key="0x0A01" tab="位置数据 (0x0A01)">
        <a-alert message="设置对方机器人在战场的坐标 (cm)" type="info" style="margin-bottom: 12px" />
        <a-form layout="vertical" :model="form0A01">
           <a-row :gutter="16">
             <a-col :span="6"><a-form-item label="英雄 X"><a-input-number v-model:value="form0A01.hero_x" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="6"><a-form-item label="英雄 Y"><a-input-number v-model:value="form0A01.hero_y" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="6"><a-form-item label="工程 X"><a-input-number v-model:value="form0A01.eng_x" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="6"><a-form-item label="工程 Y"><a-input-number v-model:value="form0A01.eng_y" :min="0" style="width:100%" /></a-form-item></a-col>
           </a-row>
           <a-row :gutter="16">
             <a-col :span="6"><a-form-item label="步兵3 X"><a-input-number v-model:value="form0A01.inf3_x" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="6"><a-form-item label="步兵3 Y"><a-input-number v-model:value="form0A01.inf3_y" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="6"><a-form-item label="步兵4 X"><a-input-number v-model:value="form0A01.inf4_x" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="6"><a-form-item label="步兵4 Y"><a-input-number v-model:value="form0A01.inf4_y" :min="0" style="width:100%" /></a-form-item></a-col>
           </a-row>
           <a-row :gutter="16">
             <a-col :span="6"><a-form-item label="空中 X"><a-input-number v-model:value="form0A01.air_x" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="6"><a-form-item label="空中 Y"><a-input-number v-model:value="form0A01.air_y" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="6"><a-form-item label="哨兵 X"><a-input-number v-model:value="form0A01.sentry_x" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="6"><a-form-item label="哨兵 Y"><a-input-number v-model:value="form0A01.sentry_y" :min="0" style="width:100%" /></a-form-item></a-col>
           </a-row>
        </a-form>
      </a-tab-pane>

      <!-- 0x0A02: 对方机器人血量 -->
      <a-tab-pane key="0x0A02" tab="血量数据 (0x0A02)">
         <a-alert message="设置对方机器人当前血量" type="info" style="margin-bottom: 12px" />
         <a-form layout="vertical" :model="form0A02">
           <a-row :gutter="16">
             <a-col :span="8"><a-form-item label="英雄(1) HP"><a-input-number v-model:value="form0A02.hero_hp" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="8"><a-form-item label="工程(2) HP"><a-input-number v-model:value="form0A02.eng_hp" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="8"><a-form-item label="哨兵(7) HP"><a-input-number v-model:value="form0A02.sentry_hp" :min="0" style="width:100%" /></a-form-item></a-col>
           </a-row>
           <a-row :gutter="16">
             <a-col :span="8"><a-form-item label="步兵(3) HP"><a-input-number v-model:value="form0A02.inf3_hp" :min="0" style="width:100%" /></a-form-item></a-col>
             <a-col :span="8"><a-form-item label="步兵(4) HP"><a-input-number v-model:value="form0A02.inf4_hp" :min="0" style="width:100%" /></a-form-item></a-col>
           </a-row>
        </a-form>
      </a-tab-pane>

      <!-- 0x0A04: 比赛状态 -->
      <a-tab-pane key="0x0A04" tab="比赛状态 (0x0A04)">
         <a-alert message="设置比赛经济与场地占领状态" type="info" style="margin-bottom: 12px" />
         <a-form layout="vertical" :model="form0A04">
           <a-row :gutter="16">
             <a-col :span="12"><a-form-item label="剩余金币"><a-input-number v-model:value="form0A04.gold" :min="0" style="width:100%" /></a-form-item></a-col>
           </a-row>
           <a-divider style="margin: 12px 0">场地状态 (Offset 4)</a-divider>
           <a-row :gutter="16">
             <a-col :span="12"><a-checkbox v-model:checked="form0A04.occupied_supply">补给区被占领 (Bit 0)</a-checkbox></a-col>
             <a-col :span="12"><a-checkbox v-model:checked="form0A04.occupied_base">基地增益点被占领 (Bit 8)</a-checkbox></a-col>
             <a-col :span="12" style="margin-top:8px"><a-checkbox v-model:checked="form0A04.occupied_highland">中央高地被占领 (Bit 1-2)</a-checkbox></a-col>
             <a-col :span="12" style="margin-top:8px"><a-checkbox v-model:checked="form0A04.occupied_fort">堡垒被占领 (Bit 4-5)</a-checkbox></a-col>
             <a-col :span="12" style="margin-top:8px"><a-checkbox v-model:checked="form0A04.tunnel_opp_pre">对方飞坡前隧道 (Bit 9)</a-checkbox></a-col>
             <a-col :span="12" style="margin-top:8px"><a-checkbox v-model:checked="form0A04.tunnel_opp_post">对方飞坡后隧道 (Bit 10)</a-checkbox></a-col>
             <a-col :span="12" style="margin-top:8px"><a-checkbox v-model:checked="form0A04.tunnel_self_pre">己方飞坡前隧道 (Bit 11)</a-checkbox></a-col>
             <a-col :span="12" style="margin-top:8px"><a-checkbox v-model:checked="form0A04.tunnel_self_post">己方飞坡后隧道 (Bit 12)</a-checkbox></a-col>
             <a-col :span="12" style="margin-top:8px"><a-checkbox v-model:checked="form0A04.card_highland">对方高地卡 (Bit 13)</a-checkbox></a-col>
             <a-col :span="12" style="margin-top:8px"><a-checkbox v-model:checked="form0A04.card_ramp">对方飞坡卡 (Bit 14)</a-checkbox></a-col>
             <a-col :span="12" style="margin-top:8px"><a-checkbox v-model:checked="form0A04.card_highway">对方公路卡 (Bit 15)</a-checkbox></a-col>
           </a-row>
        </a-form>
      </a-tab-pane>

      <!-- 0x0A05: 机器人增益 -->
      <a-tab-pane key="0x0A05" tab="增益数据 (0x0A05)">
         <a-alert message="设置对方机器人的增益属性 (Buffs)" type="info" style="margin-bottom: 12px" />
         <a-tabs size="small">
             <a-tab-pane key="hero" tab="英雄">
                 <a-form layout="vertical">
                    <a-row :gutter="8">
                        <a-col :span="8"><a-form-item label="回血%"><a-input-number v-model:value="form0A05.hero.hp_rec" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="冷却"><a-input-number v-model:value="form0A05.hero.cool" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="攻击%"><a-input-number v-model:value="form0A05.hero.att" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="防御%"><a-input-number v-model:value="form0A05.hero.def" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="负防%"><a-input-number v-model:value="form0A05.hero.neg_def" style="width:100%" /></a-form-item></a-col>
                    </a-row>
                 </a-form>
             </a-tab-pane>
             <a-tab-pane key="eng" tab="工程">
                 <a-form layout="vertical">
                    <a-row :gutter="8">
                        <a-col :span="8"><a-form-item label="回血%"><a-input-number v-model:value="form0A05.eng.hp_rec" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="冷却"><a-input-number v-model:value="form0A05.eng.cool" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="攻击%"><a-input-number v-model:value="form0A05.eng.att" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="防御%"><a-input-number v-model:value="form0A05.eng.def" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="负防%"><a-input-number v-model:value="form0A05.eng.neg_def" style="width:100%" /></a-form-item></a-col>
                    </a-row>
                 </a-form>
             </a-tab-pane>
             <a-tab-pane key="inf3" tab="步兵3">
                 <a-form layout="vertical">
                    <a-row :gutter="8">
                        <a-col :span="8"><a-form-item label="回血%"><a-input-number v-model:value="form0A05.inf3.hp_rec" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="冷却"><a-input-number v-model:value="form0A05.inf3.cool" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="攻击%"><a-input-number v-model:value="form0A05.inf3.att" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="防御%"><a-input-number v-model:value="form0A05.inf3.def" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="负防%"><a-input-number v-model:value="form0A05.inf3.neg_def" style="width:100%" /></a-form-item></a-col>
                    </a-row>
                 </a-form>
             </a-tab-pane>
             <a-tab-pane key="inf4" tab="步兵4">
                 <a-form layout="vertical">
                    <a-row :gutter="8">
                        <a-col :span="8"><a-form-item label="回血%"><a-input-number v-model:value="form0A05.inf4.hp_rec" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="冷却"><a-input-number v-model:value="form0A05.inf4.cool" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="攻击%"><a-input-number v-model:value="form0A05.inf4.att" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="防御%"><a-input-number v-model:value="form0A05.inf4.def" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="负防%"><a-input-number v-model:value="form0A05.inf4.neg_def" style="width:100%" /></a-form-item></a-col>
                    </a-row>
                 </a-form>
             </a-tab-pane>
             <a-tab-pane key="sentry" tab="哨兵">
                 <a-form layout="vertical">
                    <a-row :gutter="8">
                        <a-col :span="8"><a-form-item label="回血%"><a-input-number v-model:value="form0A05.sentry.hp_rec" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="冷却"><a-input-number v-model:value="form0A05.sentry.cool" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="攻击%"><a-input-number v-model:value="form0A05.sentry.att" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="防御%"><a-input-number v-model:value="form0A05.sentry.def" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="负防%"><a-input-number v-model:value="form0A05.sentry.neg_def" style="width:100%" /></a-form-item></a-col>
                        <a-col :span="8"><a-form-item label="姿态"><a-input-number v-model:value="form0A05.sentry.attitude" style="width:100%" /></a-form-item></a-col>
                    </a-row>
                 </a-form>
             </a-tab-pane>
         </a-tabs>
      </a-tab-pane>

      <!-- 原始 Hex -->
      <a-tab-pane key="raw" tab="原始 Hex">
        <a-form-item label="完整 Payload (Hex)">
           <a-textarea v-model:value="manualHex" :rows="6" placeholder="A1 B2 ..." />
           <div class="helper-text">长度: {{ manualHex.replace(/\s/g, '').length / 2 }} 字节</div>
        </a-form-item>
      </a-tab-pane>
    </a-tabs>
    
    <div class="generated-preview">
       <div class="label">Payload Preview (Hex):</div>
       <div class="value">{{ generatedPayload }}</div>
    </div>

  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';

const props = defineProps<{
  visible: boolean;
  modelValue?: string;
  signalType?: string;
}>();

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void;
  (e: 'update:modelValue', val: string): void;
  (e: 'confirm'): void;
}>();

const activeTab = ref('0x0A01');
const manualHex = ref('');

const protocolConfig = reactive({
  frequency: '433.20',
  bandwidth: '500 kHz (SF7, CR4/5)'
});

// Forms
const form0A01 = reactive({
  hero_x: 0, hero_y: 0,
  eng_x: 0, eng_y: 0,
  inf3_x: 0, inf3_y: 0,
  inf4_x: 0, inf4_y: 0,
  air_x: 0, air_y: 0,
  sentry_x: 0, sentry_y: 0
});

const form0A02 = reactive({
  hero_hp: 200, eng_hp: 400, sentry_hp: 600,
  inf3_hp: 150, inf4_hp: 150
});

const form0A04 = reactive({
  gold: 0,
  occupied_supply: false,
  occupied_highland: false,
  occupied_fort: false,
  occupied_base: false,
  tunnel_opp_pre: false,
  tunnel_opp_post: false,
  tunnel_self_pre: false,
  tunnel_self_post: false,
  card_highland: false,
  card_ramp: false,
  card_highway: false
});

const defaultBuffs = { hp_rec: 0, cool: 0, att: 0, def: 0, neg_def: 0, attitude: 0 };
const form0A05 = reactive({
    hero: { ...defaultBuffs },
    eng: { ...defaultBuffs },
    inf3: { ...defaultBuffs },
    inf4: { ...defaultBuffs },
    sentry: { ...defaultBuffs }
});

watch(() => props.signalType, (val) => {
  if (val === 'blue_broadcast') {
    protocolConfig.frequency = '433.92';
  } else {
    protocolConfig.frequency = '433.20';
  }
}, { immediate: true });

// Helper to pad hex
const toHex = (num: number, padding: number) => Math.floor(num || 0).toString(16).padStart(padding, '0');

const generatedPayload = computed(() => {
  if (activeTab.value === 'raw') return manualHex.value.replace(/\s/g, '').toUpperCase();
  
  let contentHex = '';
  // RoboMaster usually Little Endian for multi-byte types
  const toLEHex = (num: number, bytes: number) => {
      const hex = Math.floor(num || 0).toString(16).padStart(bytes * 2, '0');
      // Swap bytes for LE
      const pairs = hex.match(/.{1,2}/g) || [];
      return pairs.reverse().join('');
  };
  // Single Byte
  const toByte = (num: number) => Math.floor(num || 0).toString(16).padStart(2, '0');

  try {
    if (activeTab.value === '0x0A01') {
      contentHex += toLEHex(form0A01.hero_x, 2) + toLEHex(form0A01.hero_y, 2);
      contentHex += toLEHex(form0A01.eng_x, 2) + toLEHex(form0A01.eng_y, 2);
      contentHex += toLEHex(form0A01.inf3_x, 2) + toLEHex(form0A01.inf3_y, 2);
      contentHex += toLEHex(form0A01.inf4_x, 2) + toLEHex(form0A01.inf4_y, 2);
      contentHex += toLEHex(form0A01.air_x, 2) + toLEHex(form0A01.air_y, 2);
      contentHex += toLEHex(form0A01.sentry_x, 2) + toLEHex(form0A01.sentry_y, 2);
    } 
    else if (activeTab.value === '0x0A02') {
      contentHex += toLEHex(form0A02.hero_hp, 2);
      contentHex += toLEHex(form0A02.eng_hp, 2);
      contentHex += toLEHex(form0A02.inf3_hp, 2);
      contentHex += toLEHex(form0A02.inf4_hp, 2);
      contentHex += "0000"; // Reserve
      contentHex += toLEHex(form0A02.sentry_hp, 2);
    }
    else if (activeTab.value === '0x0A04') {
        contentHex += toLEHex(form0A04.gold, 2);
        contentHex += "0000"; // Total Gold placeholder
        
        let mask = 0;
        if (form0A04.occupied_supply) mask |= (1 << 0);
        if (form0A04.occupied_highland) mask |= (1 << 1); 
        if (form0A04.occupied_fort) mask |= (1 << 4);
        if (form0A04.occupied_base) mask |= (1 << 8);
        if (form0A04.tunnel_opp_pre) mask |= (1 << 9);
        if (form0A04.tunnel_opp_post) mask |= (1 << 10);
        if (form0A04.tunnel_self_pre) mask |= (1 << 11);
        if (form0A04.tunnel_self_post) mask |= (1 << 12);
        if (form0A04.card_highland) mask |= (1 << 13);
        if (form0A04.card_ramp) mask |= (1 << 14);
        if (form0A04.card_highway) mask |= (1 << 15);
        
        contentHex += toLEHex(mask, 4);
    }
    else if (activeTab.value === '0x0A05') {
        // Generates 7 bytes for Hero/Eng/Inf3/Inf4, 8 bytes for Sentry (Total 36 bytes)
        const genBuff = (b: any) => {
            return toByte(b.hp_rec) + 
                   toLEHex(b.cool, 2) + 
                   toByte(b.def) + 
                   toByte(b.neg_def) + 
                   toLEHex(b.att, 2);
        };
        contentHex += genBuff(form0A05.hero);
        contentHex += genBuff(form0A05.eng);
        contentHex += genBuff(form0A05.inf3);
        contentHex += genBuff(form0A05.inf4);
        contentHex += genBuff(form0A05.sentry) + toByte(form0A05.sentry.attitude);
    }
  } catch (e) {
      return "Error";
  }
  
  return contentHex.toUpperCase();
});

const handleOk = () => {
  emit('update:modelValue', generatedPayload.value);
  emit('confirm');
  emit('update:visible', false);
};

const handleCancel = () => {
  emit('update:visible', false);
};
</script>

<style scoped>
.helper-text {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.generated-preview {
    background: rgba(0,0,0,0.3);
    padding: 16px;
    border-radius: var(--border-radius);
    margin-top: 24px;
    border: 1px dashed var(--border-color);
}
.generated-preview .label {
    font-size: 11px;
    color: var(--text-dim);
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.generated-preview .value {
    font-family: 'JetBrains Mono', monospace;
    color: var(--primary-color);
    word-break: break-all;
    font-size: 14px;
    background: rgba(0, 242, 255, 0.05);
    padding: 8px;
    border-radius: 4px;
}
.protocol-section {
  margin-bottom: 24px;
  background: rgba(0,0,0,0.2);
  padding: 16px;
  border-radius: var(--border-radius);
  border: 1px solid var(--border-color);
}
.section-title {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-dim);
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
</style>
