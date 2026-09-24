'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Crosshair, Loader2, Search } from 'lucide-react';

import { FALLBACK_ORIGIN, formatDistance, haversineKm, nearest, type LatLon } from '@/lib/geo';
import { LAYERS, layerMeta, layerOf } from '@/lib/layers';
import { kstNow, openStatus, type KstNow } from '@/lib/open-now';
import type { LayerKey, Place } from '@/lib/types';
import { useLayers } from '@/lib/use-layers';
import { Input } from '@/components/ui/input';
import { PlaceDetail } from '@/components/place-detail';
import { StatusBadge } from '@/components/status-badge';
import type { FlyTarget, MapPoint } from '@/components/baby-map';

const BabyMap = dynamic(() => import('@/components/baby-map').then((m) => m.BabyMap), {
  ssr: false,
  loading: () => (
    <div className="flex size-full items-center justify-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" /> 지도 불러오는 중…
    </div>
  ),
});

type Filter = 'open' | '야간' | '토요일' | '일요일' | '공휴일' | '예방접종';
const FILTERS: readonly { key: Filter; label: string }[] = [
  { key: 'open', label: '지금 진료 중' },
  { key: '야간', label: '야간 진료' },
  { key: '토요일', label: '토요일' },
  { key: '일요일', label: '일요일' },
  { key: '공휴일', label: '공휴일' },
  { key: '예방접종', label: '국가예방접종' },
];
const LIST_LIMIT = 100;
const NOW_TICK_MS = 60_000;
const CLOSED_COLOR = '#B0B8C1';

type Tagged = Place & { layer: LayerKey };
type GeoState = 'idle' | 'locating' | 'granted' | 'denied';

export function BabyBrowser({ initialLayer }: { initialLayer: LayerKey }) {
  const [enabled, setEnabled] = useState<ReadonlySet<LayerKey>>(() => new Set([initialLayer]));
  const [filters, setFilters] = useState<ReadonlySet<Filter>>(() => new Set());
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [now, setNow] = useState<KstNow>(() => kstNow());
  const [geo, setGeo] = useState<GeoState>('idle');
  const [userAt, setUserAt] = useState<LatLon | null>(null);
  const [center, setCenter] = useState<LatLon>(FALLBACK_ORIGIN);
  const [flyTo, setFlyTo] = useState<FlyTarget | null>(null);
  const flyKey = useRef(0);
  const states = useLayers(enabled);

  useEffect(() => {
    const id = setInterval(() => setNow(kstNow()), NOW_TICK_MS);
    return () => clearInterval(id);
  }, []);

  /** 위치 요청. geolocation 이 있는 환경에서만 부른다. */
  const requestPosition = useCallback(() => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const at = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        setUserAt(at);
        setCenter(at);
        setGeo('granted');
        flyKey.current += 1;
        setFlyTo({ ...at, zoom: 14, key: flyKey.current });
      },
      () => setGeo('denied'),
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 60_000 },
    );
  }, []);

  const locate = useCallback(() => {
    if (!('geolocation' in navigator)) return setGeo('denied');
    setGeo('locating');
    requestPosition();
  }, [requestPosition]);

  // 첫 방문에 바로 위치를 묻는다 — '내 주변'이 이 앱의 본론이다
  useEffect(() => {
    if ('geolocation' in navigator) requestPosition();
  }, [requestPosition]);

  const medicalOn = [...enabled].some((k) => layerMeta(k).medical);

  const items = useMemo<Tagged[]>(() => {
    const q = query.trim();
    const out: Tagged[] = [];
    for (const key of enabled) {
      const st = states[key];
      if (st?.kind !== 'ready') continue;
      const medical = layerMeta(key).medical;
      for (const p of st.items) {
        if (q && !p.name.includes(q) && !p.addr?.includes(q)) continue;
        if (medical && filters.size > 0 && !passes(p, filters, now)) continue;
        out.push({ ...p, layer: key });
      }
    }
    return out;
  }, [enabled, states, query, filters, now]);

  const points = useMemo<MapPoint[]>(
    () =>
      items.map((p) => {
        const meta = layerMeta(p.layer);
        const status = meta.medical ? openStatus(p.hours, now) : null;
        const open = status === 'open' || status === 'closing';
        return {
          id: p.id,
          lon: p.lng,
          lat: p.lat,
          title: p.name,
          color: status && !open ? CLOSED_COLOR : meta.color,
          accent: open,
        };
      }),
    [items, now],
  );

  // 가까운 100곳 안에서 지금 진료 중인 곳을 위로 — 공휴일·야간엔 대부분 닫혀 있어 연 곳이 묻힌다
  const list = useMemo(() => {
    const near = nearest(items, center, LIST_LIMIT);
    const rank = (p: Tagged) => {
      if (!layerMeta(p.layer).medical) return 0;
      const s = openStatus(p.hours, now);
      return s === 'open' || s === 'closing' ? 0 : 1;
    };
    return near.map((w, i) => ({ w, i })).sort((a, b) => rank(a.w.item) - rank(b.w.item) || a.i - b.i).map(({ w }) => w);
  }, [items, center, now]);
  const selected = selectedId ? items.find((p) => p.id === selectedId) : undefined;
  const loading = [...enabled].some((k) => states[k]?.kind === 'loading');
  const failed = [...enabled].filter((k) => states[k]?.kind === 'error');

  const toggleLayer = (key: LayerKey) =>
    setEnabled((s) => {
      const next = new Set(s);
      if (next.has(key) && next.size > 1) next.delete(key);
      else next.add(key);
      return next;
    });
  const toggleFilter = (key: Filter) =>
    setFilters((s) => {
      const next = new Set(s);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    // 모바일: 조작부 → 지도 → 목록 세로 스택. 데스크톱: 왼쪽 조작부·목록, 오른쪽 지도. 지도는 하나만 만든다(WebGL 컨텍스트 절약).
    <div className="grid gap-3 lg:h-[calc(100dvh-7.5rem)] lg:grid-cols-[400px_1fr] lg:grid-rows-[auto_minmax(0,1fr)]">
      <div className="flex flex-col gap-3 lg:col-start-1 lg:row-start-1">
        <div className="flex flex-wrap gap-1.5">
          {LAYERS.map((l) => {
            const on = enabled.has(l.key);
            return (
              <button
                key={l.key}
                type="button"
                onClick={() => toggleLayer(l.key)}
                aria-pressed={on}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors ${
                  on ? 'border-transparent text-white' : 'border-[#E5E8EB] bg-white hover:border-primary/40'
                }`}
                style={on ? { backgroundColor: l.color } : undefined}
              >
                {!on && <span className="size-2 rounded-full" style={{ backgroundColor: l.color }} />}
                {l.name}
                {l.region && <span className={`text-xs ${on ? 'text-white/80' : 'text-muted-foreground'}`}>{l.region}</span>}
              </button>
            );
          })}
        </div>

        {medicalOn && (
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => toggleFilter(f.key)}
                aria-pressed={filters.has(f.key)}
                className={`rounded-lg border px-2.5 py-1 text-sm ${
                  filters.has(f.key) ? 'border-primary bg-accent font-medium text-accent-foreground' : 'border-[#E5E8EB] bg-white'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="이름·주소로 찾기" className="h-10 pl-9" aria-label="이름·주소 검색" />
          </div>
          <button
            type="button"
            onClick={locate}
            className="inline-flex h-10 items-center gap-1 rounded-lg border border-[#E5E8EB] bg-white px-3 text-sm hover:border-primary/40"
          >
            {geo === 'locating' ? <Loader2 className="size-4 animate-spin" /> : <Crosshair className="size-4" />}
            내 위치
          </button>
        </div>

        <p className="text-xs text-muted-foreground">
          {now.holiday ? '오늘은 공휴일 — 공휴일 진료시간 기준으로 판정합니다. ' : ''}
          {geo === 'granted' ? '지도 중심에서 가까운 순' : geo === 'denied' ? '위치 권한이 없어 지도 중심(처음엔 서울시청)에서 가까운 순' : '지도 중심에서 가까운 순'}
          {loading ? ' · 불러오는 중…' : ` · ${items.length.toLocaleString()}곳`}
          {failed.length > 0 && <span className="text-destructive"> · {failed.map((k) => layerMeta(k).name).join(', ')} 불러오기 실패</span>}
        </p>

      </div>

      <div className="h-[45dvh] overflow-hidden rounded-2xl border border-[#E5E8EB] lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:h-auto">
        <BabyMap points={points} center={center} isUserLocation={!!userAt} selectedId={selectedId} onSelect={setSelectedId} flyTo={flyTo} onMoveEnd={setCenter} />
      </div>

      <ul className="divide-y divide-[#F2F4F6] rounded-2xl border border-[#E5E8EB] bg-white lg:col-start-1 lg:row-start-2 lg:overflow-y-auto">
          {list.length === 0 && !loading && <li className="p-4 text-sm text-muted-foreground">조건에 맞는 곳이 없습니다.</li>}
          {list.map(({ item, distanceKm }) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => setSelectedId(item.id)}
                className={`flex w-full items-start gap-3 p-3 text-left hover:bg-accent/60 ${item.id === selectedId ? 'bg-accent' : ''}`}
              >
                <span className="mt-1.5 size-2.5 shrink-0 rounded-full" style={{ backgroundColor: layerMeta(item.layer).color }} />
                <span className="min-w-0 flex-1 space-y-0.5">
                  <span className="flex items-center gap-1.5">
                    <span className="truncate font-medium">{item.name}</span>
                    {layerMeta(item.layer).medical && <StatusBadge hours={item.hours} now={now} />}
                  </span>
                  <span className="block truncate text-xs text-muted-foreground">{item.addr}</span>
                </span>
                <span className="shrink-0 text-xs text-muted-foreground tabular-nums">{formatDistance(distanceKm)}</span>
              </button>
            </li>
          ))}
      </ul>

      {selected && (
        <div className="fixed inset-x-0 bottom-0 z-30 max-h-[75dvh] overflow-y-auto rounded-t-3xl border-t border-[#E5E8EB] bg-white p-5 shadow-[0_-8px_32px_rgba(0,0,0,0.12)] lg:inset-x-auto lg:right-6 lg:bottom-6 lg:w-[380px] lg:rounded-3xl lg:border">
          <PlaceDetail
            place={selected}
            layer={layerOf(selected.id) ?? selected.layer}
            distanceKm={haversineKm(userAt ?? center, { lat: selected.lat, lon: selected.lng })}
            now={now}
            onClose={() => setSelectedId(null)}
          />
        </div>
      )}
    </div>
  );
}

function passes(p: Place, filters: ReadonlySet<Filter>, now: KstNow): boolean {
  for (const f of filters) {
    if (f === 'open') {
      const s = openStatus(p.hours, now);
      if (s !== 'open' && s !== 'closing') return false;
    } else if (!p.tags?.includes(f)) return false;
  }
  return true;
}

