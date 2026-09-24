/** 레이어 스냅샷 한 행. `scripts/collect.py` 가 `data/layers/<layer>.json` 에 이 모양의 배열로 쓴다. */
export interface Place {
  id: string;
  name: string;
  lat: number;
  lng: number;
  addr?: string;
  tel?: string;
  /** "1"=월 … "7"=일, "8"=공휴일 → [시작, 종료] 원문 HHmm. 없는 요일은 휴진. */
  hours?: Partial<Record<DayKey, readonly [string, string]>>;
  /** 야간·토요일·일요일·공휴일·우수시설·광역거점 등 */
  tags?: string[];
  /** 상세 패널용 한글 라벨 → 값 */
  info?: Record<string, string>;
}

export type DayKey = '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8';

export const LAYER_KEYS = [
  'peds',
  'obgyn',
  'postnatal',
  'playground',
  'indoor-play',
  'idolbom',
  'busan-daycare',
  'busan-nursing',
] as const;

export type LayerKey = (typeof LAYER_KEYS)[number];

export function isLayerKey(v: string | null | undefined): v is LayerKey {
  return !!v && (LAYER_KEYS as readonly string[]).includes(v);
}
