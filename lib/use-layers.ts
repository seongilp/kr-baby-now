'use client';

import { useEffect, useRef, useState } from 'react';

import type { LayerKey, Place } from '@/lib/types';

export type LayerState = { kind: 'loading' } | { kind: 'error' } | { kind: 'ready'; items: Place[] };

/**
 * 켜진 레이어만 `/layers/<key>.json`(정적 파일, CDN 캐시)에서 한 번씩 받아 둔다.
 * 끈 레이어도 메모리에 남겨 다시 켤 때 즉시 보인다. 결과가 아직 없으면 'loading' 이다.
 */
export function useLayers(enabled: ReadonlySet<LayerKey>): Partial<Record<LayerKey, LayerState>> {
  const [done, setDone] = useState<Partial<Record<LayerKey, LayerState>>>({});
  const requested = useRef(new Set<LayerKey>());

  useEffect(() => {
    for (const key of enabled) {
      if (requested.current.has(key)) continue;
      requested.current.add(key);
      fetch(`/layers/${key}.json`)
        .then((r) => (r.ok ? (r.json() as Promise<Place[]>) : Promise.reject(new Error(String(r.status)))))
        .then((items) => setDone((s) => ({ ...s, [key]: { kind: 'ready', items: Array.isArray(items) ? items : [] } })))
        .catch((err) => {
          console.error('[layers] load failed', key, err);
          // 실패한 레이어는 끄고 다시 켜면 재시도한다
          requested.current.delete(key);
          setDone((s) => ({ ...s, [key]: { kind: 'error' } }));
        });
    }
  }, [enabled]);

  const out: Partial<Record<LayerKey, LayerState>> = {};
  for (const key of enabled) out[key] = done[key] ?? { kind: 'loading' };
  return out;
}
