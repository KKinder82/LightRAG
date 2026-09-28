import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { activeProjectId, createProject, getDeletionJobs, listProjects, type ProjectDataset } from '@/api/lightrag'
import { useSettingsStore } from '@/stores/settings'
import { errorMessage } from '@/lib/utils'

export default function ProjectSelector() {
  const { t } = useTranslation()
  const [projects, setProjects] = useState<ProjectDataset[]>([])
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const selected = activeProjectId
  const [jobs, setJobs] = useState({ queued: 0, failed: 0 })
  useEffect(() => {
    let active = true
    const refresh = () => getDeletionJobs().then(result => {
      if (!active) return
      const values = Object.values(result)
      setJobs({ queued: values.filter(job => job.status === 'queued').length, failed: values.filter(job => job.status === 'failed').length })
    }).catch(() => {})
    void refresh()
    const timer = setInterval(refresh, 5000)
    return () => { active = false; clearInterval(timer) }
  }, [])
  useEffect(() => { listProjects().then(setProjects).catch(e => setError(errorMessage(e))) }, [])

  const select = (id: string) => {
    const settings = useSettingsStore.getState()
    localStorage.setItem(`project-history:${selected}`, JSON.stringify(settings.retrievalHistory))
    const history = JSON.parse(localStorage.getItem(`project-history:${id}`) || '[]')
    settings.setRetrievalHistory(history)
    settings.setGraphFolderId(null)
    settings.setQueryLabel('*')
    settings.updateQuerySettings({ folder_id: undefined })
    localStorage.setItem('LIGHTRAG-PROJECT', id)
    window.location.reload()
  }

  return <form className="flex flex-wrap items-center gap-2 border-b px-4 py-2 text-sm" onSubmit={async e => {
    e.preventDefault()
    if (!name.trim() || saving) return
    setSaving(true)
    try { select((await createProject(name.trim())).id) }
    catch (err) { setError(errorMessage(err)); setSaving(false) }
  }}>
    <label htmlFor="project-dataset">{t('dataset.label')}</label>
    <select id="project-dataset" className="rounded border bg-background p-1" value={selected} onChange={e => select(e.target.value)}>
      <option value="">{t('dataset.default')}</option>
      {projects.map(project => <option key={project.id} value={project.id}>{project.name}</option>)}
    </select>
    <input className="rounded border bg-background p-1" aria-label={t('dataset.name')} placeholder={t('dataset.name')} value={name} maxLength={100} onChange={e => setName(e.target.value)} />
    <button type="submit" className="rounded border px-2 py-1" disabled={saving || !name.trim()}>{t('dataset.create')}</button>
    {(jobs.queued > 0 || jobs.failed > 0) && <span role="status">{t('dataset.deletionStatus', jobs)}</span>}
    {error && <span role="alert" className="text-red-500">{error}</span>}
  </form>
}
