<template>
  <a-card title="实时频谱分析 (FFT)" size="small" :bordered="false" class="spectrum-card">
    <div ref="chartRef" class="spectrum-chart"></div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';
import { useSDRStore } from '@/stores/sdrStore';

const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;
const store = useSDRStore();

const initChart = () => {
  if (!chartRef.value) return;
  
  chartInstance = echarts.init(chartRef.value);
  
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(20, 20, 20, 0.8)',
      borderColor: 'rgba(0, 229, 255, 0.3)',
      textStyle: { color: '#fff' },
      axisPointer: {
        type: 'cross',
        lineStyle: { color: 'rgba(0, 229, 255, 0.5)', type: 'dashed' }
      }
    },
    grid: {
      top: 20, right: 20, bottom: 40, left: 50,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: [],
      name: '频率 (MHz)',
      nameLocation: 'middle',
      nameGap: 25,
      axisLabel: { color: '#888', fontSize: 10 },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      splitLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    yAxis: {
      type: 'value',
      min: -120,
      max: 0,
      name: '功率 (dBm)',
      nameLocation: 'middle',
      nameGap: 35,
      axisLabel: { color: '#888', fontSize: 10 },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      splitLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    series: [
      {
        name: '功率谱图',
        type: 'line',
        showSymbol: false,
        sampling: 'lttb',
        smooth: true,
        itemStyle: { color: '#00e5ff' },
        lineStyle: { width: 2, shadowBlur: 10, shadowColor: 'rgba(0, 229, 255, 0.5)' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 229, 255, 0.3)' },
            { offset: 1, color: 'rgba(0, 229, 255, 0)' }
          ])
        },
        data: []
      }
    ],
    animation: false // 禁用动画以提高实时性能
  };
  
  chartInstance.setOption(option);
};

watch(
  () => store.spectrum,
  (newVal) => {
    if (chartInstance && newVal.frequencies.length > 0) {
      const freqLabels = newVal.frequencies.map(f => (f/1e6).toFixed(3));
      
      chartInstance.setOption({
        xAxis: { data: freqLabels },
        series: [{ data: newVal.power }]
      });
    }
  },
  { deep: true }
);

const handleResize = () => {
  chartInstance?.resize();
};

onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  chartInstance?.dispose();
});
</script>

<style scoped>
.spectrum-card {
  height: 100%;
}
.spectrum-chart {
  width: 100%;
  height: 400px;
}
</style>
