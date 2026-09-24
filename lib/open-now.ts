import { isHoliday } from '@/lib/holidays';
import type { DayKey, Place } from '@/lib/types';

/**
 * 병·의원 "지금 진료 중" 판정. KST 벽시계 기준(실행 환경 시간대와 무관하게 UTC+9 로 고정).
 * 요일 키는 국립중앙의료원 규격: 1=월 … 7=일, 8=공휴일. 공휴일이면 8 만 본다(요일 시간표로 폴백하지 않는다).
 * 자정 넘김(종료 ≤ 시작, 또는 2400 초과 표기)은 다음날까지로 본다.
 */
export type OpenStatus = 'open' | 'closing' | 'closed' | 'unknown';

export const CLOSING_SOON_MIN = 30;
const KST_OFFSET_MS = 9 * 60 * 60 * 1000;

export interface KstNow {
  ymd: string;
  day: DayKey;
  holiday: boolean;
  minutes: number;
}

export function kstNow(date: Date = new Date()): KstNow {
  const k = new Date(date.getTime() + KST_OFFSET_MS);
  const ymd = k.toISOString().slice(0, 10);
  const holiday = isHoliday(ymd);
  const weekday = k.getUTCDay(); // 0=일
  const day = (holiday ? '8' : String(weekday === 0 ? 7 : weekday)) as DayKey;
  return { ymd, day, holiday, minutes: k.getUTCHours() * 60 + k.getUTCMinutes() };
}

/** "HHmm" → 분. 2400 초과(예: 2530 = 다음날 01:30) 표기도 받는다. */
export function parseHHmm(s: string | null | undefined): number | null {
  const m = /^(\d{1,2})(\d{2})$/.exec((s ?? '').trim());
  if (!m) return null;
  const h = Number(m[1]);
  const mm = Number(m[2]);
  if (h > 36 || mm > 59) return null;
  return h * 60 + mm;
}

export function formatHHmm(s: string): string {
  const v = parseHHmm(s);
  if (v == null) return s;
  const h = Math.floor(v / 60) % 24;
  return `${String(h).padStart(2, '0')}:${String(v % 60).padStart(2, '0')}`;
}

export function openStatus(hours: Place['hours'], now: KstNow = kstNow()): OpenStatus {
  if (!hours || Object.keys(hours).length === 0) return 'unknown';
  const slot = hours[now.day];
  if (!slot) return 'closed';
  const start = parseHHmm(slot[0]);
  let end = parseHHmm(slot[1]);
  if (start == null || end == null) return 'unknown';
  if (end <= start) end += 24 * 60;
  const t = now.minutes;
  if (t >= start && t < end) return end - t <= CLOSING_SOON_MIN ? 'closing' : 'open';
  return 'closed';
}

export const DAY_LABELS: Record<DayKey, string> = {
  '1': '월', '2': '화', '3': '수', '4': '목', '5': '금', '6': '토', '7': '일', '8': '공휴일',
};
