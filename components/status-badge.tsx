import { openStatus, type KstNow } from '@/lib/open-now';
import type { Place } from '@/lib/types';

const STYLE = {
  open: ['진료 중', 'bg-[#E8F3FF] text-[#1B64DA]'],
  closing: ['곧 마감', 'bg-[#FFF4E5] text-[#C2620A]'],
  closed: ['진료 종료', 'bg-[#F2F4F6] text-[#6B7684]'],
  unknown: ['시간 정보 없음', 'bg-[#F2F4F6] text-[#6B7684]'],
} as const;

export function StatusBadge({ hours, now }: { hours: Place['hours']; now: KstNow }) {
  const [label, cls] = STYLE[openStatus(hours, now)];
  return <span className={`inline-flex rounded-md px-1.5 py-0.5 text-xs font-medium ${cls}`}>{label}</span>;
}
