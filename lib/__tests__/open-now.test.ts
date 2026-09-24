import assert from 'node:assert/strict';
import { test } from 'node:test';

import { formatHHmm, kstNow, openStatus, type KstNow } from '../open-now';

const at = (day: KstNow['day'], hhmm: string): KstNow => ({
  ymd: '2026-09-22',
  day,
  holiday: day === '8',
  minutes: Number(hhmm.slice(0, 2)) * 60 + Number(hhmm.slice(2)),
});

const weekday = { '1': ['0900', '1800'], '6': ['0900', '1300'] } as const;

test('KST 벽시계: UTC 15:30 은 다음날 00:30, 추석(2026-09-24)은 공휴일 키 8', () => {
  const n = kstNow(new Date('2026-09-23T15:30:00Z'));
  assert.equal(n.ymd, '2026-09-24');
  assert.equal(n.day, '8');
  assert.equal(n.minutes, 30);
});

test('평일 월요일: 진료 중·마감 임박·마감 후', () => {
  assert.equal(openStatus({ ...weekday }, at('1', '1000')), 'open');
  assert.equal(openStatus({ ...weekday }, at('1', '1745')), 'closing');
  assert.equal(openStatus({ ...weekday }, at('1', '1800')), 'closed');
});

test('해당 요일 시간표가 없으면 휴진, 시간표 자체가 없으면 알 수 없음', () => {
  assert.equal(openStatus({ ...weekday }, at('7', '1100')), 'closed');
  assert.equal(openStatus(undefined, at('1', '1100')), 'unknown');
});

test('공휴일은 공휴일 시간표(8)만 본다', () => {
  assert.equal(openStatus({ ...weekday }, at('8', '1000')), 'closed');
  assert.equal(openStatus({ '8': ['0900', '1800'] }, at('8', '1000')), 'open');
});

test('자정 넘김: 1900~0100 은 23:30 에 진료 중', () => {
  assert.equal(openStatus({ '2': ['1900', '0100'] }, at('2', '2330')), 'open');
  assert.equal(openStatus({ '2': ['1900', '2500'] }, at('2', '2330')), 'open');
});

test('2400 초과 표기는 시계 시각으로 보여 준다', () => {
  assert.equal(formatHHmm('2530'), '01:30');
  assert.equal(formatHHmm('0830'), '08:30');
});
