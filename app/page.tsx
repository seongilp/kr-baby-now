import { BabyBrowser } from '@/components/baby-browser';
import { isLayerKey } from '@/lib/types';

export default async function Home({ searchParams }: PageProps<'/'>) {
  const layer = (await searchParams).layer;
  const first = Array.isArray(layer) ? layer[0] : layer;
  return <BabyBrowser initialLayer={isLayerKey(first) ? first : 'peds'} />;
}
