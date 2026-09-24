import 'server-only';

import grants from '@/data/lists/busan-birth-grant.json';
import docs from '@/data/lists/idolbom-docs.json';

interface GrantRow {
  gugun: string;
  pay_year: string;
  subsidy_type: string;
  division: string;
  subsidy: string;
  department_name: string;
}

export interface GuGrants {
  gugun: string;
  year: string;
  rows: { type: string; division: string; amount: number | null; dept: string }[];
}

const clean = (s: string) => s.replace(/\s+/g, ' ').trim();
/** '2025', '2017년~계속' 같은 연도 표기에서 비교용 숫자를 뽑는다. '~계속'은 현재 진행형이라 가장 최근으로 본다. */
const yearRank = (y: string) => (y.includes('계속') ? 9999 : Number(y.slice(0, 4)) || 0);

/** 부산 구·군별로 가장 최근 지급연도 항목만 */
export function busanGrants(): GuGrants[] {
  const byGu = new Map<string, GrantRow[]>();
  for (const r of grants as GrantRow[]) byGu.set(r.gugun, [...(byGu.get(r.gugun) ?? []), r]);
  return [...byGu.entries()]
    .map(([gugun, rows]) => {
      const top = Math.max(...rows.map((r) => yearRank(r.pay_year)));
      const latest = rows.filter((r) => yearRank(r.pay_year) === top);
      return {
        gugun,
        year: latest[0].pay_year,
        rows: latest.map((r) => ({
          type: clean(r.subsidy_type),
          division: clean(r.division),
          amount: /^\d+$/.test(r.subsidy) ? Number(r.subsidy) : null,
          dept: clean(r.department_name),
        })),
      };
    })
    .sort((a, b) => a.gugun.localeCompare(b.gugun, 'ko'));
}

interface DocRow {
  crtrYr: string;
  gvmtSprtDvsnNm: string;
  sprtTrgtNm: string;
  flfllDcmntCn: string;
  idntyAndIssuMeanCn: string;
}

export function idolbomDocs() {
  return (docs as DocRow[]).map((d) => ({
    year: d.crtrYr,
    group: clean(d.gvmtSprtDvsnNm),
    target: clean(d.sprtTrgtNm),
    documents: d.flfllDcmntCn.trim(),
    how: d.idntyAndIssuMeanCn.trim(),
  }));
}
