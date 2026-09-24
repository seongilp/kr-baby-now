/**
 * 지리 계산. 좌표는 전부 WGS84(수집 스크립트가 변환해 둔다).
 * 서버 공간 필터 없이 브라우저가 레이어 스냅샷을 받아 거리정렬한다 — 수만 건 하버사인도 수 ms.
 */

const EARTH_RADIUS_KM = 6371;

export interface LatLon {
  lat: number;
  lon: number;
}

/** 위치 권한이 없을 때의 기준점. 화면에 '서울시청 기준'이라고 밝힌다. */
export const FALLBACK_ORIGIN: LatLon = { lat: 37.5663, lon: 126.9779 };

const toRad = (deg: number) => (deg * Math.PI) / 180;

export function haversineKm(a: LatLon, b: LatLon): number {
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.min(1, Math.sqrt(h)));
}

export interface WithDistance<T> {
  item: T;
  distanceKm: number;
}

/** origin 에서 가까운 순으로 최대 limit 개. */
export function nearest<T extends { lat: number; lng: number }>(
  items: readonly T[],
  origin: LatLon,
  limit: number,
): WithDistance<T>[] {
  const scored = items.map((item) => ({ item, distanceKm: haversineKm(origin, { lat: item.lat, lon: item.lng }) }));
  scored.sort((a, b) => a.distanceKm - b.distanceKm);
  return scored.slice(0, limit);
}

/** 1km 미만은 m 로 */
export function formatDistance(km: number): string {
  if (km < 1) return `${Math.max(10, Math.round(km * 100) * 10)}m`;
  return `${km < 10 ? km.toFixed(1) : Math.round(km)}km`;
}
