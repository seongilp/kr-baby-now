import type { Metadata, Viewport } from 'next';
import Link from 'next/link';
import { Baby } from 'lucide-react';

import 'pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css';
import './globals.css';

const NAME = '육아나우';
const TITLE = `${NAME} — 지금 문 연 소아과부터 산후조리원·놀이터까지`;
const DESCRIPTION =
  '내 주변에서 지금 진료 중인 소아청소년과·산부인과, 야간·주말·공휴일 진료, 산후조리원, 어린이놀이시설, 아이돌봄 기관을 지도에서 찾습니다.';

export const metadata: Metadata = {
  metadataBase: new URL('https://kr-baby-now.vercel.app'),
  title: { default: TITLE, template: `%s — ${NAME}` },
  description: DESCRIPTION,
  applicationName: NAME,
  openGraph: { title: TITLE, description: DESCRIPTION, siteName: NAME, type: 'website', locale: 'ko_KR' },
};

export const viewport: Viewport = {
  themeColor: '#ffffff',
  colorScheme: 'light',
};

export default function RootLayout({ children }: LayoutProps<'/'>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-white font-sans text-[#191F28]">
        <header className="sticky top-0 z-20 border-b border-[#F2F4F6] bg-white/90 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-7xl items-center gap-2 px-4">
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <span className="grid size-7 place-items-center rounded-lg bg-primary text-white">
                <Baby className="size-4" aria-hidden />
              </span>
              {NAME}
            </Link>
            <nav className="ml-auto flex gap-4 text-sm text-muted-foreground">
              <Link href="/" className="hover:text-foreground">
                지도
              </Link>
              <Link href="/info" className="hover:text-foreground">
                돌봄·지원 정보
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-4">{children}</main>
        <footer className="border-t border-[#F2F4F6] bg-[#F9FAFB] py-6 text-center text-xs text-muted-foreground">
          데이터 출처: 국립중앙의료원·행정안전부·한국건강가정진흥원·부산광역시 (공공데이터포털). 진료시간은 기관이 신고한 정보라 실제와 다를 수 있으니 방문 전 전화로 확인하세요.
          <br />
          <a className="underline underline-offset-2" href="https://github.com/seongilp/kr-baby-now">
            GitHub
          </a>
        </footer>
      </body>
    </html>
  );
}
