export interface SpectrumData {
  frequencies: number[];
  power: number[];
}

export interface SDRStatus {
  connected: boolean;
  streaming: boolean;
  centerFreq: number;
  sampleRate: number;
  gain: number;
  overflow?: boolean;
  underflow?: boolean;
}

export interface RadarTarget {
  id: number;
  x: number;
  y: number;
  progress: number; // 0-150
  type: 'friendly' | 'enemy' | 'unknown';
}

export type MessageType = 'spectrum' | 'status' | 'radar_data';

export interface WebSocketMessage {
  type: MessageType;
  [key: string]: any;
}
