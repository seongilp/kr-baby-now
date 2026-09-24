import type { LayerKey } from '@/lib/types';

export interface LayerMeta {
  key: LayerKey;
  name: string;
  /** 칩 아래 한 줄 설명 */
  blurb: string;
  color: string;
  /** 진료시간이 있는 의료 레이어 — '지금 진료 중'·야간·주말 필터를 켠다 */
  medical?: boolean;
  /** 특정 지역만 있는 데이터. 칩에 지역 배지를 단다. */
  region?: string;
  source: string;
}

export const LAYERS: readonly LayerMeta[] = [
  { key: 'peds', name: '소아청소년과', blurb: '지금 진료·야간·주말', color: '#3182F6', medical: true, source: '국립중앙의료원 전국 병·의원 찾기' },
  { key: 'obgyn', name: '산부인과', blurb: '임신·출산 진료', color: '#E5467A', medical: true, source: '국립중앙의료원 전국 병·의원 찾기' },
  { key: 'postnatal', name: '산후조리원', blurb: '영업 중인 곳', color: '#8B5CF6', source: '행정안전부 산후조리업' },
  { key: 'playground', name: '놀이터', blurb: '공원·휴양림 등 누구나 쓰는 곳', color: '#10B981', source: '행정안전부 전국어린이놀이시설정보' },
  { key: 'indoor-play', name: '실내놀이터·키즈카페', blurb: '놀이제공영업소·키즈 레스토랑', color: '#F97316', source: '행정안전부 전국어린이놀이시설정보' },
  { key: 'idolbom', name: '아이돌봄 기관', blurb: '아이돌보미 신청 창구', color: '#F59E0B', source: '한국건강가정진흥원 아이돌봄서비스' },
  { key: 'busan-daycare', name: '어린이집', blurb: '부산 16개 구·군', color: '#0EA5E9', region: '부산', source: '부산광역시 구·군 어린이집 현황' },
  { key: 'busan-nursing', name: '수유실', blurb: '부산 수유시설', color: '#EC4899', region: '부산', source: '부산광역시 수유실 보유 시설' },
];

const BY_KEY = new Map(LAYERS.map((l) => [l.key, l]));

export function layerMeta(key: LayerKey): LayerMeta {
  return BY_KEY.get(key)!;
}

/** id 는 '<layer>-<원천키>' — 레이어 키에 '-' 가 들어 있어 가장 긴 접두어로 찾는다. */
export function layerOf(id: string): LayerKey | undefined {
  return [...LAYERS]
    .sort((a, b) => b.key.length - a.key.length)
    .find((l) => id.startsWith(`${l.key}-`))?.key;
}
