import type { Metadata } from 'next';
import Link from 'next/link';
import { ExternalLink } from 'lucide-react';

import { busanGrants, idolbomDocs } from '@/lib/info-data';

export const metadata: Metadata = { title: '돌봄·지원 정보' };

/** 구·군 출산지원금 1인당 상한 추정치. 이보다 큰 값(예: 4,210만원)은 총 지급액이 섞인 것으로 보고 숫자를 그대로 싣지 않는다. */
const PER_CHILD_MAX = 10_000_000;

export default function InfoPage() {
  const grants = busanGrants();
  const docs = idolbomDocs();
  const docYear = docs[0]?.year;

  return (
    <div className="mx-auto max-w-3xl space-y-10 py-2">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold">돌봄·지원 정보</h1>
        <p className="text-sm text-muted-foreground">
          공공데이터로 공개된 지원 정보입니다. 기준 연도가 지난 자료가 섞여 있어 연도를 함께 적었습니다. 신청 전에는 반드시 담당 기관에서 최신
          기준을 확인하세요.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">부산 구·군별 출산지원금</h2>
        <p className="text-sm text-muted-foreground">구·군마다 가장 최근 지급연도 항목만 보여 줍니다. 출처: 부산광역시 출산지원금 현황.</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {grants.map((g) => (
            <div key={g.gugun} className="rounded-2xl border border-[#E5E8EB] bg-white p-4">
              <div className="mb-2 flex items-baseline justify-between">
                <h3 className="font-semibold">{g.gugun}</h3>
                <span className="text-xs text-muted-foreground">{g.year} 기준</span>
              </div>
              <ul className="space-y-1 text-sm">
                {g.rows.map((r, i) => (
                  <li key={i} className="flex justify-between gap-3">
                    <span className="min-w-0 text-muted-foreground">
                      <span className="line-clamp-2">{r.division}</span>
                    </span>
                    <span className="shrink-0 font-medium tabular-nums">
                      {r.amount == null ? '—' : r.amount > PER_CHILD_MAX ? (
                        <span className="text-muted-foreground" title={`${r.amount.toLocaleString()}원 — 1인당 금액이 아니라 총 지급액일 수 있습니다`}>
                          기준 불명확
                        </span>
                      ) : (
                        `${r.amount.toLocaleString()}원`
                      )}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-muted-foreground">{g.rows[0]?.dept}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">아이돌봄 정부지원 — 가구별 증빙서류</h2>
        <p className="text-sm text-muted-foreground">
          {docYear}년 기준 자료입니다(원천 데이터가 갱신되지 않음). 최신 기준과 요금은{' '}
          <a href="https://idolbom.go.kr" target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-primary underline underline-offset-2">
            아이돌봄서비스 누리집 <ExternalLink className="size-3" />
          </a>
          에서 확인하세요. 가까운 제공기관은{' '}
          <Link href="/?layer=idolbom" className="text-primary underline underline-offset-2">
            지도
          </Link>
          에서 찾을 수 있습니다.
        </p>
        <div className="divide-y divide-[#F2F4F6] rounded-2xl border border-[#E5E8EB] bg-white">
          {docs.map((d, i) => (
            <details key={i} className="group p-4">
              <summary className="cursor-pointer font-medium">
                {d.group}
                {d.target && <span className="font-normal text-muted-foreground"> · {d.target}</span>}
              </summary>
              <div className="mt-2 space-y-2 text-sm">
                <p className="whitespace-pre-line">{d.documents}</p>
                <p className="whitespace-pre-line text-muted-foreground">확인 방법: {d.how}</p>
              </div>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
