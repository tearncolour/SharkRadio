<template>
  <a-card title="实时频谱分析 (FFT) & 瀑布图" size="small" :bordered="false" class="spectrum-card">
    <div class="view-container">
      <div ref="chartRef" class="spectrum-chart"></div>
      <div class="waterfall-container">
        <canvas ref="waterfallCanvas" class="waterfall-canvas"></canvas>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';
import { useSDRStore } from '@/stores/sdrStore';

const chartRef = ref<HTMLElement | null>(null);
const waterfallCanvas = ref<HTMLCanvasElement | null>(null);
let chartInstance: echarts.ECharts | null = null;
const store = useSDRStore();

// Waterfall context
let ctx: CanvasRenderingContext2D | null = null;
let canvasWidth = 800;
let canvasHeight = 300;

const colorMap: Uint8ClampedArray[] = [];
const initColorMap = () => {
    for (let i = 0; i <= 255; i++) {
        const t = i / 255;
        // Turbo colormap style approximation or simple HSL
        // Blue(0) -> Cyan(.33) -> Green(.66) -> Yellow(.83) -> Red(1)
        let r=0, g=0, b=0;
        if (t < 0.33) { // Blue -> Cyan
             // 0 -> (0,0,255) to (0,255,255)
             const local = t / 0.33;
             r = 0; g = Math.floor(255 * local); b = 255;
        } else if (t < 0.66) { // Cyan -> Green -> Yellowish
             // .33 -> (0,255,255) to (0,255,0) ? No, typically Cyan to Green
             const local = (t - 0.33) / 0.33;
             r = 0; g = 255; b = Math.floor(255 * (1 - local));
        } else if (t < 0.9) { // Green -> Yellow -> Red
             const local = (t - 0.66) / 0.24;
             r = Math.floor(255 * local); g = 255; b = 0;
        } else { // Yellow -> Red
             const local = (t - 0.9) / 0.1;
             r = 255; g = Math.floor(255 * (1 - local)); b = 0;
        }
        colorMap[i] = new Uint8ClampedArray([r, g, b, 255]);
    }
};
initColorMap();

// Dynamic Range Params (Updated for better vis)
const MIN_DB = -100;
const MAX_DB = 10;

const stats = reactive({ min: 0, max: 0 });

const initChart = () => {
  if (!chartRef.value) return;
  
  if (chartRef.value.clientWidth === 0 || chartRef.value.clientHeight === 0) {
      setTimeout(initChart, 100);
      return;
  }
  
  chartInstance = echarts.init(chartRef.value);
  
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
          const pt = params[0];
          return `Freq: ${pt.axisValue} MHz<br/>Power: ${pt.data.toFixed(2)} dBm`;
      }
    },
    grid: {
      top: 30, right: 20, bottom: 20, left: 50,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: [],
      axisLabel: { show: true, interval: 'auto', color: '#666' }, 
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      min: null, // Auto-scale
      max: null, // Auto-scale
      name: 'dBm',
      nameTextStyle: { color: '#888' },
      axisLabel: { color: '#888', fontSize: 10 },
      splitLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    series: [
      {
        type: 'line',
        showSymbol: false,
        sampling: 'lttb', // Downsample for performance
        progressive: 0, // Force immediate draw
        hoverLayerThreshold: Infinity,
        itemStyle: { color: '#00f2ff' },
        lineStyle: { width: 1 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 242, 255, 0.2)' },
            { offset: 1, color: 'rgba(0, 242, 255, 0)' }
          ])
        },
        data: []
      }
    ],
    animation: false,
    graphic: [
        {
            type: 'text',
            right: 10,
            top: 5,
            style: {
                text: 'Waiting for data...',
                fill: '#666',
                fontSize: 11
            }
        }
    ]
  };
  
  chartInstance.setOption(option);
  
  // Create ResizeObserver
  const resizeObserver = new ResizeObserver(() => {
      chartInstance?.resize();
      // Reset waterfall ctx to force resize logic next frame
      ctx = null;
  });
  resizeObserver.observe(chartRef.value);
};

const updateWaterfall = (powerData: number[]) => {
    if (!waterfallCanvas.value) return;
    const container = waterfallCanvas.value.parentElement;
    
    if (!ctx && container) {
        // Match canvas internal resolution to FFT size for 1:1 pixel mapping
        waterfallCanvas.value.width = powerData.length; 
        waterfallCanvas.value.height = container.clientHeight;
        
        ctx = waterfallCanvas.value.getContext('2d', { willReadFrequently: true });
        if (!ctx) return;
        
        // Fill black initial
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, waterfallCanvas.value.width, waterfallCanvas.value.height);
    }
    
    if (!ctx) return;
    
    const w = waterfallCanvas.value.width;
    const h = waterfallCanvas.value.height;
    
    // 1. Shift existing content down by 1px
    ctx.drawImage(waterfallCanvas.value, 
                  0, 0, w, h - 1,
                  0, 1, w, h - 1);
                  
    // 2. Draw new top line
    const idata = ctx.createImageData(w, 1);
    const buffer = idata.data;
    
    // If powerData length != canvas width, we need to interpolation or stepping
    // Since we set width = powerData.length, it usually matches. 
    // But if FFT size changed dynamically, safe check:
    const step = powerData.length / w;
    
    for (let i = 0; i < w; i++) {
        const pIdx = Math.floor(i * step);
        const dbm = powerData[pIdx]; // raw dbm
        
        // Normalize to 0..1
        let val = (dbm - MIN_DB) / (MAX_DB - MIN_DB);
        val = Math.max(0, Math.min(1, val));
        
        const colorIdx = Math.floor(val * 255);
        const color = colorMap[colorIdx];
        
        const pixelIdx = i * 4;
        buffer[pixelIdx] = color[0];
        buffer[pixelIdx+1] = color[1];
        buffer[pixelIdx+2] = color[2];
        buffer[pixelIdx+3] = 255;
    }
    
    ctx.putImageData(idata, 0, 0);
};

watch(
  () => store.spectrum,
  (newVal) => {
    if (chartInstance && newVal.frequencies.length > 0) {
      // Don't subtract gain for display if we want to see absolute Rx power
      // Or subtract it to see "Input Power". 
      // Usually SDR waterfall shows "dBFS" or "Relative Power".
      // Let's stick to raw calculated power from backend for now to avoid confusion.
      const displayPower = newVal.power; 
       
      // Calc stats
      let minP = 9999;
      let maxP = -9999;
      for (let p of displayPower) {
          if (p < minP) minP = p;
          if (p > maxP) maxP = p;
      }
      stats.min = minP;
      stats.max = maxP;

      const freqStart = newVal.frequencies[0] / 1e6;
      const freqEnd = newVal.frequencies[newVal.frequencies.length - 1] / 1e6;
      
      chartInstance.setOption({
        xAxis: { 
            data: newVal.frequencies.map(f => (f/1e6).toFixed(2)) 
        },
        series: [{ data: displayPower }],
        graphic: [
            {
                type: 'text',
                right: 10,
                top: 5,
                style: {
                    text: `Range: ${minP.toFixed(1)} ~ ${maxP.toFixed(1)} dBm`,
                    fill: '#00f2ff',
                    fontSize: 11
                }
            }
        ]
      });
      
      updateWaterfall(displayPower);
    }
  }
);

onMounted(() => {
  initChart();
  // ResizeObserver handles resize now
});

onUnmounted(() => {
  chartInstance?.dispose();
});
</script>

<style scoped>
.spectrum-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}
:deep(.ant-card-body) {
  flex: 1;
  height: 0;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.view-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
}
.spectrum-chart {
  flex: 3;
  width: 100%;
  min-height: 0;
  border-radius: var(--border-radius);
  background: rgba(0,0,0,0.2);
  border: 1px solid var(--border-color);
}
.waterfall-container {
    flex: 2;
    width: 100%;
    min-height: 0;
    background: #000;
    overflow: hidden;
    border-radius: var(--border-radius);
    border: 1px solid var(--border-color);
    box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
}
.waterfall-canvas {
    width: 100%;
    height: 100%;
    display: block;
    /* Pixelated rendering for clearer waterfall bits */
    image-rendering: pixelated; 
}
</style>
