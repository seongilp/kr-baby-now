import { ExternalLink, MapPin, Navigation, Phone, X } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatDistance } from '@/lib/geo';
import { layerMeta } from '@/lib/layers';
import { DAY_LABELS, formatHHmm, type KstNow } from '@/lib/open-now';
import type { DayKey, LayerKey, Place } from '@/lib/types';
import { StatusBadge } from '@/components/status-badge';

const DAYS: readonly DayKey[] = ['1', '2', '3', '4', '5', '6', '7', '8'];

export function PlaceDetail({
  place,
  layer,
  distanceKm,
  now,
  onClose,
}: {
  place: Place;
  layer: LayerKey;
  distanceKm: number;
  now: KstNow;
  onClose: () => void;
}) {
  const meta = layerMeta(layer);
  const q = encodeURIComponent(place.name);
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge style={{ backgroundColor: meta.color }} className="text-white">
              {meta.name}
            </Badge>
            {meta.medical && <StatusBadge hours={place.hours} now={now} />}
            {place.tags?.map((t) => (
              <Badge key={t} variant="outline">
                {t}
              </Badge>
            ))}
          </div>
          <h2 className="text-lg font-bold leading-snug">{place.name}</h2>
          <p className="text-sm text-muted-foreground">{formatDistance(distanceKm)}</p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="닫기">
          <X className="size-4" />
        </Button>
      </div>

      {place.addr && (
        <p className="flex gap-2 text-sm">
          <MapPin className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          {place.addr}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {place.tel && (
          <Button asChild size="sm">
            <a href={`tel:${place.tel.replace(/[^\d+]/g, '')}`}>
              <Phone className="size-4" /> {place.tel}
            </a>
          </Button>
        )}
        <Button asChild size="sm" variant="outline">
          <a href={`https://map.kakao.com/link/to/${q},${place.lat},${place.lng}`} target="_blank" rel="noreferrer">
            <Navigation className="size-4" /> 카카오맵 길찾기
          </a>
        </Button>
        <Button asChild size="sm" variant="outline">
          <a href={`https://map.naver.com/p/search/${q}`} target="_blank" rel="noreferrer">
            <ExternalLink className="size-4" /> 네이버 지도
          </a>
        </Button>
      </div>

      {meta.medical && place.hours && (
        <section className="space-y-2">
          <h3 className="text-sm font-semibold">진료시간</h3>
          <table className="w-full text-sm">
            <tbody className="divide-y divide-[#F2F4F6]">
              {DAYS.map((d) => {
                const slot = place.hours?.[d];
                const today = d === now.day;
                return (
                  <tr key={d} className={today ? 'font-semibold text-primary' : undefined}>
                    <td className="w-16 py-1.5">
                      {DAY_LABELS[d]}
                      {today && <span className="ml-1 text-xs">오늘</span>}
                    </td>
                    <td className="py-1.5 tabular-nums">
                      {slot ? `${formatHHmm(slot[0])} – ${formatHHmm(slot[1])}` : <span className="text-muted-foreground">휴진</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="text-xs text-muted-foreground">
            병원이 신고한 시간표입니다. 명절·임시 휴진은 반영되지 않을 수 있으니 방문 전 전화로 확인하세요.
          </p>
        </section>
      )}

      {place.info && Object.keys(place.info).length > 0 && (
        <dl className="grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1.5 text-sm">
          {Object.entries(place.info).map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-muted-foreground">{k}</dt>
              <dd className="break-words">{v}</dd>
            </div>
          ))}
        </dl>
      )}

      <p className="text-xs text-muted-foreground">출처: {meta.source} (공공데이터포털)</p>
    </div>
  );
}
