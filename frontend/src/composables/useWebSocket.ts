import { ref, onMounted, onUnmounted } from 'vue';
import { useSDRStore } from '@/stores/sdrStore';

export function useWebSocket() {
  const store = useSDRStore();
  const socket = ref<WebSocket | null>(null);
  const isConnected = ref(false);
  
  let reconnectTimer: any = null;
  let pingInterval: any = null;

  function connect() {
    // 使用 Vite 代理配置的路径，或者直接指向后端端口
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    // 开发环境下通常是 8000，但在 Vite 代理下可以用相对路径 /ws/sdr
    // 为了简单起见，这里假设开发环境代理生效
    const wsUrl = `${protocol}//${host}:${window.location.port}/ws/sdr`; 
    // 注意: 如果通过 Vite dev server 访问，端口是 5173，/ws/sdr会被代理到 8000
    
    console.log(`Connecting to WebSocket: ${wsUrl}`);
    
    try {
      socket.value = new WebSocket(wsUrl);
      
      socket.value.onopen = () => {
        console.log('WebSocket connected');
        isConnected.value = true;
        store.updateStatus({ connected: true });
        // 将 WebSocket 实例注册到 store 以支持命令发送
        if (socket.value) {
          store.setWebSocket(socket.value);
        }
        
        // 启动心跳
        clearInterval(pingInterval);
        pingInterval = setInterval(() => {
          if (socket.value && socket.value.readyState === WebSocket.OPEN) {
            socket.value.send('{"type":"ping"}');
          }
        }, 25000);
      };
      
      socket.value.onclose = () => {
        console.log('WebSocket disconnected');
        isConnected.value = false;
        store.updateStatus({ connected: false, streaming: false });
        clearInterval(pingInterval);
        
        // 自动重连
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(() => {
          connect();
        }, 3000);
      };
      
      socket.value.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      socket.value.onmessage = (event) => {
        try {
          // 如果是二进制数据，可能需要特殊处理
          if (event.data instanceof Blob) {
             // 处理二进制流
             return;
          }
          
          const msg = JSON.parse(event.data);
          
          // 忽略心跳响应
          if (msg.type === 'pong' || msg.type === 'ping') {
            return;
          }

          if (msg.type !== 'spectrum') {
             console.log('[DEBUG Frontend] Received:', msg.type, msg);
          }
          
          switch (msg.type) {
            case 'spectrum':
              store.updateSpectrum({
                frequencies: msg.frequencies,
                power: msg.power
              });
              break;
            case 'packet':
              // 处理解码的数据包
              // console.log('DEBUG Packet:', msg);
              store.addDecodedPacket({
                timestamp: msg.timestamp,
                hex: msg.hex,
                packetType: msg.packet_type,
                isValid: msg.is_valid,
                deviceId: msg.device_id
              });
              break;
            case 'status':
              store.updateStatus(msg.data);
              break;
            case 'radar_data':
              // 更新雷达目标...
              break;
            default:
              // console.log('Unknown message type:', msg.type);
          }
        } catch (e) {
          console.error('Error parsing message:', e, event.data);
        }
      };
      
    } catch (e) {
      console.error('Connection factory failed:', e);
    }
  }
  
  function send(data: any) {
    if (socket.value && socket.value.readyState === WebSocket.OPEN) {
      socket.value.send(JSON.stringify(data));
    }
  }

  onMounted(() => {
    connect();
  });

  onUnmounted(() => {
    clearInterval(pingInterval);
    if (socket.value) {
      socket.value.close();
    }
    clearTimeout(reconnectTimer);
  });

  return {
    isConnected,
    send
  };
}

