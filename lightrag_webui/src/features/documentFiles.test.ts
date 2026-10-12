import { expect, test } from 'bun:test'
import type { DocStatusResponse } from '@/api/lightrag'
import { getOriginalFileName, getDocumentElapsed, formatDocumentElapsed } from './documentFiles'

const doc = (metadata: Record<string, unknown> = {}): DocStatusResponse => ({
  id: 'doc-1', status: 'processed', content_summary: '', content_length: 0,
  file_path: 'report__rev_123.pdf', created_at: '2026-01-01T00:00:10Z',
  updated_at: '2026-01-01T00:01:00Z', metadata
})

test('original upload name survives internal file renaming', () => {
  expect(getOriginalFileName(doc({ upload_name: '报告.pdf' }))).toBe('报告.pdf')
  expect(getOriginalFileName(doc({ source_file_name: 'dir/report.pdf' }))).toBe('report.pdf')
})

test('elapsed includes upload, queue and KG stages', () => {
  const start = Date.parse('2026-01-01T00:00:00Z') / 1000
  expect(getDocumentElapsed(doc({ uploaded_at: start, processing_end_time: start + 20, kg_end_time: start + 60, kg_status: 'completed' }))).toEqual({ seconds: 60, complete: true })
  expect(getDocumentElapsed(doc({ uploaded_at: start, processing_end_time: start + 20, kg_status: 'running' }), (start + 40) * 1000)).toEqual({ seconds: 40, complete: false })
})

test('fast indexing completes without KG; legacy records use creation time', () => {
  const start = Date.parse('2026-01-01T00:00:00Z') / 1000
  expect(getDocumentElapsed(doc({ uploaded_at: start, processing_end_time: start + 20, kg_status: 'skipped' }))).toEqual({ seconds: 20, complete: true })
  expect(getDocumentElapsed(doc())).toEqual({ seconds: 50, complete: true })
})

test('failed and invalid timestamps do not report successful elapsed time', () => {
  expect(getDocumentElapsed(doc({ kg_status: 'failed' }))).toBeNull()
  expect(getDocumentElapsed({ ...doc(), status: 'failed' })).toBeNull()
  expect(getDocumentElapsed({ ...doc(), created_at: 'bad' })).toBeNull()
})

test('duration formatting', () => {
  expect(formatDocumentElapsed(0)).toBe('0s')
  expect(formatDocumentElapsed(61)).toBe('1m 1s')
  expect(formatDocumentElapsed(3661)).toBe('1h 1m 1s')
})
