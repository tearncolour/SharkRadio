export type TxSignalType = 
  'red_broadcast' | 'red_jam_1' | 'red_jam_2' | 'red_jam_3' |
  'blue_broadcast' | 'blue_jam_1' | 'blue_jam_2' | 'blue_jam_3' | 
  'custom';
export type RxSignalType = 'red_parse' | 'blue_parse' | 'custom';
export type WorkMode = 'tx' | 'rx' | 'txrx';

export interface SDRConfig {
  centerFreq: number;       // Hz
  sampleRate: number;       // Hz
  gain: number;             // dB (rx positive, tx negative)
  bandwidth: number;        // Hz
  gainMode?: string;        // for RX
}

export interface SDRTab {
  id: string;               // Unique ID (e.g., device URI + timestamp)
  deviceId: string;         // Associated device ID / URI
  name: string;             // User defined name
  mode: WorkMode;
  txSignalType?: TxSignalType;
  rxSignalType?: RxSignalType;
  rxConfig: SDRConfig;
  txConfig: SDRConfig;
  isActive: boolean;
  isStreaming: boolean;
  jammingPayload?: string; // 6-char ASCII
  broadcastPayload?: string; // Hex string for protocol 1.6
}
