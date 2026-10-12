import type { DocStatusResponse } from '@/api/lightrag'

export const getOriginalFileName = (doc: DocStatusResponse): string => {
  const name = doc.metadata?.upload_name || doc.metadata?.source_file_name || doc.file_path
  return typeof name === 'string' ? name.replace(/\\/g, '/').split('/').pop() || '-' : '-'
}

export const getDocumentElapsed = (doc: DocStatusResponse, now = Date.now()): { seconds: number, complete: boolean } | null => {
  const metadata = doc.metadata || {}
  const start = typeof metadata.uploaded_at === 'number'
    ? metadata.uploaded_at * 1000
    : Date.parse(doc.created_at)
  const complete = doc.status === 'processed' && (
    !metadata.kg_status || metadata.kg_status === 'completed' || metadata.kg_status === 'skipped'
  )
  // Failed KG extraction is not successful completion.
  if (doc.status === 'failed' || metadata.kg_status === 'failed') return null
  const endTime = metadata.kg_end_time ?? metadata.processing_end_time
  const end = complete
    ? typeof endTime === 'number' ? endTime * 1000 : Date.parse(doc.updated_at)
    : now
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return null
  return { seconds: Math.floor((end - start) / 1000), complete }
}

export const formatDocumentElapsed = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor(seconds % 3600 / 60)
  const remainder = seconds % 60
  return hours > 0 ? `${hours}h ${minutes}m ${remainder}s` : minutes > 0 ? `${minutes}m ${remainder}s` : `${remainder}s`
}
