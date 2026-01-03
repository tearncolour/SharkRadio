export type TxSignalType = 'red_broadcast' | 'blue_broadcast' | 'jam_1' | 'jam_2' | 'jam_3' | 'custom';
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
}
