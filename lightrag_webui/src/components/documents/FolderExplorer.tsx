/**
 * FolderExplorer — Left-side collapsible folder tree panel (Windows Explorer / VS Code sidebar style).
 */
import { useState, useCallback, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronRightIcon,
  FolderIcon,
  FolderOpenIcon,
  FolderPlusIcon,
  PencilIcon,
  Trash2Icon,
  RefreshCwIcon,
  PanelLeftCloseIcon,
  PanelLeftOpenIcon,
  FilesIcon,
  CheckIcon,
  XIcon,
  AlertTriangleIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/Tooltip'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog'
import {
  FolderTreeNode,
  createFolder,
  deleteFolder,
  updateFolder,
  getDocumentsPaginatedWithTimeout,
} from '@/api/lightrag'
import { errorMessage } from '@/lib/utils'
import { toast } from 'sonner'

export interface FolderExplorerProps {
  foldersTree: FolderTreeNode[]
  selectedFolderId: string | null
  includeSubfolders: boolean
  isLoading: boolean
  isOpen: boolean
  onToggleOpen: () => void
  onSelectFolder: (folderId: string | null) => void
  onIncludeSubfoldersChange: (include: boolean) => void
  onTreeChanged: () => void
}

interface FolderStats {
  directFileCount: number | null
  totalFileCount: number | null
}

function countAllDescendants(node: FolderTreeNode): number {
  return node.children.reduce((sum, child) => sum + 1 + countAllDescendants(child), 0)
}

function findNode(tree: FolderTreeNode[], id: string): FolderTreeNode | null {
  for (const node of tree) {
    if (node.folder.id === id) return node
    const found = findNode(node.children, id)
    if (found) return found
  }
  return null
}

function collectDescendantIds(node: FolderTreeNode): string[] {
  const ids: string[] = []
  const visit = (n: FolderTreeNode) => { ids.push(n.folder.id); n.children.forEach(visit) }
  node.children.forEach(visit)
  return ids
}

interface FolderNodeProps {
  node: FolderTreeNode
  depth: number
  isSelected: boolean
  isExpanded: boolean
  onToggleExpand: (id: string) => void
  onSelect: (id: string) => void
  onStartCreate: (parentId: string) => void
  onStartRename: (id: string, currentName: string) => void
  onDelete: (id: string, name: string, hasChildren: boolean) => void
  onDragStart: (e: React.DragEvent, id: string) => void
  onDragOver: (e: React.DragEvent, id: string) => void
  onDragLeave: (e: React.DragEvent, id: string) => void
  onDrop: (e: React.DragEvent, targetId: string | null) => void
  dragOverId: string | null
  draggedId: string | null
  children?: React.ReactNode
  statsCache: Map<string, FolderStats>
  onFetchStats: (folderId: string) => void
}

function FolderNode({
  node, depth, isSelected, isExpanded, onToggleExpand, onSelect,
  onStartCreate, onStartRename, onDelete,
  onDragStart, onDragOver, onDragLeave, onDrop,
  dragOverId, draggedId, children, statsCache, onFetchStats,
}: FolderNodeProps) {
  const { t } = useTranslation()
  const folderId = node.folder.id
  const isDragOver = dragOverId === folderId
  const isDragged = draggedId === folderId
  const hasChildren = node.children.length > 0
  const subfolderCount = node.children.length
  const totalSubfolderCount = countAllDescendants(node)
  const stats = statsCache.get(folderId)

  const handleMouseEnter = useCallback(() => {
    if (!statsCache.has(folderId)) onFetchStats(folderId)
  }, [folderId, statsCache, onFetchStats])

  const tooltipContent = (
    <div className="space-y-1 text-xs">
      <div className="font-medium">{node.folder.name}</div>
      {node.folder.description && (
        <div className="text-muted-foreground">{node.folder.description}</div>
      )}
      <div className="pt-1 border-t border-border/50 space-y-0.5">
        <div>
          {t('documentPanel.folderExplorer.tooltip.subfolders')}: {subfolderCount}
          {totalSubfolderCount > subfolderCount
            ? ` (${t('documentPanel.folderExplorer.tooltip.total')}: ${totalSubfolderCount})`
            : ''}
        </div>
        {stats ? (
          <>
            <div>{t('documentPanel.folderExplorer.tooltip.directFiles')}: {stats.directFileCount ?? '…'}</div>
            <div>{t('documentPanel.folderExplorer.tooltip.totalFiles')}: {stats.totalFileCount ?? '…'}</div>
          </>
        ) : (
          <div className="text-muted-foreground">{t('documentPanel.folderExplorer.tooltip.loading')}</div>
        )}
      </div>
    </div>
  )

  return (
    <div>
      <TooltipProvider delayDuration={600}>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              draggable
              onDragStart={(e) => onDragStart(e, folderId)}
              onDragOver={(e) => onDragOver(e, folderId)}
              onDragLeave={(e) => onDragLeave(e, folderId)}
              onDrop={(e) => onDrop(e, folderId)}
              onMouseEnter={handleMouseEnter}
              style={{ paddingLeft: `${depth * 16 + 4}px` }}
              className={cn(
                'group flex items-center gap-1 py-0.5 pr-1 rounded cursor-pointer select-none text-sm mx-1',
                'hover:bg-accent hover:text-accent-foreground',
                isSelected && 'bg-accent text-accent-foreground font-medium',
                isDragOver && !isDragged && 'bg-blue-100 dark:bg-blue-900/30 outline outline-1 outline-blue-400',
                isDragged && 'opacity-40'
              )}
              onClick={() => onSelect(folderId)}
            >
              <button
                type="button"
                className={cn(
                  'flex-none p-0.5 rounded hover:bg-accent/50 transition-transform duration-150',
                  !hasChildren && 'invisible'
                )}
                onClick={(e) => { e.stopPropagation(); onToggleExpand(folderId) }}
                tabIndex={-1}
                aria-label={isExpanded ? t('documentPanel.folderExplorer.collapse') : t('documentPanel.folderExplorer.expand')}
              >
                <ChevronRightIcon className={cn('h-3.5 w-3.5 transition-transform duration-150', isExpanded && 'rotate-90')} />
              </button>
              <span className="flex-none text-yellow-500">
                {isExpanded && hasChildren
                  ? <FolderOpenIcon className="h-4 w-4" />
                  : <FolderIcon className="h-4 w-4" />}
              </span>
              <span className="flex-1 truncate min-w-0" title={node.folder.name}>{node.folder.name}</span>
              <span className="flex-none flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                <button type="button" className="p-0.5 rounded hover:bg-accent/80 text-muted-foreground hover:text-foreground"
                  onClick={(e) => { e.stopPropagation(); onStartCreate(folderId) }}
                  title={t('documentPanel.folderExplorer.addSubfolder')} tabIndex={-1}>
                  <FolderPlusIcon className="h-3.5 w-3.5" />
                </button>
                <button type="button" className="p-0.5 rounded hover:bg-accent/80 text-muted-foreground hover:text-foreground"
                  onClick={(e) => { e.stopPropagation(); onStartRename(folderId, node.folder.name) }}
                  title={t('documentPanel.folderExplorer.rename')} tabIndex={-1}>
                  <PencilIcon className="h-3.5 w-3.5" />
                </button>
                <button type="button" className="p-0.5 rounded hover:bg-accent/80 text-muted-foreground hover:text-red-500"
                  onClick={(e) => { e.stopPropagation(); onDelete(folderId, node.folder.name, hasChildren) }}
                  title={t('documentPanel.folderExplorer.delete')} tabIndex={-1}>
                  <Trash2Icon className="h-3.5 w-3.5" />
                </button>
              </span>
            </div>
          </TooltipTrigger>
          <TooltipContent side="right" className="max-w-[220px]">{tooltipContent}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
      {isExpanded && hasChildren && <div>{children}</div>}
    </div>
  )
}

interface InlineInputProps {
  depth: number
  initialValue: string
  placeholder: string
  onConfirm: (value: string) => void
  onCancel: () => void
}

function InlineInput({ depth, initialValue, placeholder, onConfirm, onCancel }: InlineInputProps) {
  const [value, setValue] = useState(initialValue)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus(); inputRef.current?.select() }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); if (value.trim()) onConfirm(value.trim()) }
    else if (e.key === 'Escape') { e.preventDefault(); onCancel() }
  }

  return (
    <div style={{ paddingLeft: `${depth * 16 + 24}px` }} className="flex items-center gap-1 py-0.5 pr-1 mx-1">
      <FolderIcon className="h-4 w-4 flex-none text-yellow-500" />
      <Input
        ref={inputRef} value={value} onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => { if (value.trim()) onConfirm(value.trim()); else onCancel() }}
        placeholder={placeholder} className="h-6 text-sm px-1 py-0 flex-1 min-w-0"
      />
      <button type="button" className="p-0.5 rounded hover:bg-accent/80 text-green-600"
        onMouseDown={(e) => { e.preventDefault(); if (value.trim()) onConfirm(value.trim()) }} tabIndex={-1}>
        <CheckIcon className="h-3.5 w-3.5" />
      </button>
      <button type="button" className="p-0.5 rounded hover:bg-accent/80 text-muted-foreground"
        onMouseDown={(e) => { e.preventDefault(); onCancel() }} tabIndex={-1}>
        <XIcon className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

interface DeleteConfirmDialogProps {
  open: boolean; folderName: string; hasChildren: boolean; isDeleting: boolean
  onConfirm: (recursive: boolean) => void; onCancel: () => void
}

function DeleteConfirmDialog({ open, folderName, hasChildren, isDeleting, onConfirm, onCancel }: DeleteConfirmDialogProps) {
  const { t } = useTranslation()
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent className="sm:max-w-md" onCloseAutoFocus={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangleIcon className="h-5 w-5 text-yellow-500" />
            {t('documentPanel.folderExplorer.deleteDialog.title')}
          </DialogTitle>
          <DialogDescription>
            {hasChildren
              ? t('documentPanel.folderExplorer.deleteDialog.descriptionWithChildren', { name: folderName })
              : t('documentPanel.folderExplorer.deleteDialog.description', { name: folderName })}
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onCancel} disabled={isDeleting}>{t('common.cancel')}</Button>
          {hasChildren && (
            <Button variant="outline" onClick={() => onConfirm(false)} disabled={isDeleting}
              className="text-red-600 border-red-300 hover:bg-red-50 dark:hover:bg-red-900/20">
              {isDeleting ? t('common.deleting') : t('documentPanel.folderExplorer.deleteDialog.deleteFolderOnly')}
            </Button>
          )}
          <Button variant="destructive" onClick={() => onConfirm(hasChildren)} disabled={isDeleting}>
            {isDeleting ? t('common.deleting') : (
              hasChildren
                ? t('documentPanel.folderExplorer.deleteDialog.deleteRecursive')
                : t('documentPanel.folderExplorer.deleteDialog.confirm')
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default function FolderExplorer({
  foldersTree, selectedFolderId, includeSubfolders, isLoading, isOpen,
  onToggleOpen, onSelectFolder, onIncludeSubfoldersChange, onTreeChanged,
}: FolderExplorerProps) {
  const { t } = useTranslation()

  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const handleToggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }, [])

  useEffect(() => {
    if (!selectedFolderId) return
    const expandAncestors = (tree: FolderTreeNode[], targetId: string, path: string[]): boolean => {
      for (const node of tree) {
        if (node.folder.id === targetId) return true
        if (expandAncestors(node.children, targetId, [...path, node.folder.id])) {
          setExpandedIds((prev) => {
            const next = new Set(prev)
            path.forEach((id) => next.add(id))
            next.add(node.folder.id)
            return next
          })
          return true
        }
      }
      return false
    }
    expandAncestors(foldersTree, selectedFolderId, [])
  }, [selectedFolderId, foldersTree])

  const [creatingUnder, setCreatingUnder] = useState<string | null | '__none__'>('__none__')
  const [isCreating, setIsCreating] = useState(false)

  const handleStartCreate = useCallback((parentId: string | null) => {
    setCreatingUnder(parentId)
    if (parentId) setExpandedIds((prev) => new Set([...prev, parentId]))
  }, [])

  const handleConfirmCreate = useCallback(async (name: string) => {
    const parentId = creatingUnder === '__none__' ? null : creatingUnder
    setIsCreating(true)
    try {
      await createFolder({ name, parent_id: parentId ?? undefined })
      toast.success(t('documentPanel.folderExplorer.createSuccess', { name }))
      setCreatingUnder('__none__')
      onTreeChanged()
    } catch (err) {
      toast.error(t('documentPanel.folderExplorer.createFailed', { error: errorMessage(err) }))
    } finally {
      setIsCreating(false)
    }
  }, [creatingUnder, onTreeChanged, t])

  const handleCancelCreate = useCallback(() => setCreatingUnder('__none__'), [])

  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renamingInitialName, setRenamingInitialName] = useState('')

  const handleStartRename = useCallback((id: string, currentName: string) => {
    setRenamingId(id); setRenamingInitialName(currentName)
  }, [])

  const handleConfirmRename = useCallback(async (newName: string) => {
    if (!renamingId || !newName.trim()) return
    try {
      await updateFolder(renamingId, { name: newName.trim() })
      toast.success(t('documentPanel.folderExplorer.renameSuccess', { name: newName.trim() }))
      setRenamingId(null)
      onTreeChanged()
    } catch (err) {
      toast.error(t('documentPanel.folderExplorer.renameFailed', { error: errorMessage(err) }))
    }
  }, [renamingId, onTreeChanged, t])

  const handleCancelRename = useCallback(() => setRenamingId(null), [])

  const [deletingFolder, setDeletingFolder] = useState<{ id: string; name: string; hasChildren: boolean } | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const handleStartDelete = useCallback((id: string, name: string, hasChildren: boolean) => {
    setDeletingFolder({ id, name, hasChildren })
  }, [])

  const handleConfirmDelete = useCallback(async (recursive: boolean) => {
    if (!deletingFolder) return
    setIsDeleting(true)
    try {
      await deleteFolder(deletingFolder.id, recursive)
      toast.success(t('documentPanel.folderExplorer.deleteSuccess', { name: deletingFolder.name }))
      if (selectedFolderId === deletingFolder.id) onSelectFolder(null)
      setDeletingFolder(null)
      onTreeChanged()
    } catch (err) {
      toast.error(t('documentPanel.folderExplorer.deleteFailed', { error: errorMessage(err) }))
    } finally {
      setIsDeleting(false)
    }
  }, [deletingFolder, selectedFolderId, onSelectFolder, onTreeChanged, t])

  const [draggedId, setDraggedId] = useState<string | null>(null)
  const [dragOverId, setDragOverId] = useState<string | null>(null)
  const foldersTreeRef = useRef(foldersTree)
  useEffect(() => { foldersTreeRef.current = foldersTree }, [foldersTree])

  const handleDragStart = useCallback((e: React.DragEvent, id: string) => {
    setDraggedId(id); e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', id)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent, id: string) => {
    e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setDragOverId(id)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent, id: string) => {
    if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node))
      setDragOverId((prev) => (prev === id ? null : prev))
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent, targetId: string | null) => {
    e.preventDefault()
    const sourceId = draggedId ?? e.dataTransfer.getData('text/plain')
    setDraggedId(null); setDragOverId(null)
    if (!sourceId || sourceId === targetId) return
    if (targetId) {
      const sourceNode = findNode(foldersTreeRef.current, sourceId)
      if (sourceNode && collectDescendantIds(sourceNode).includes(targetId)) {
        toast.error(t('documentPanel.folderExplorer.moveIntoDescendantError'))
        return
      }
    }
    try {
      await updateFolder(sourceId, { parent_id: targetId })
      toast.success(t('documentPanel.folderExplorer.moveSuccess'))
      onTreeChanged()
    } catch (err) {
      toast.error(t('documentPanel.folderExplorer.moveFailed', { error: errorMessage(err) }))
    }
  }, [draggedId, onTreeChanged, t])

  const handleRootDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setDragOverId('__root__')
  }, [])
  const handleRootDragLeave = useCallback((e: React.DragEvent) => {
    if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node))
      setDragOverId((prev) => (prev === '__root__' ? null : prev))
  }, [])
  const handleRootDrop = useCallback((e: React.DragEvent) => handleDrop(e, null), [handleDrop])

  const [statsCache, setStatsCache] = useState<Map<string, FolderStats>>(new Map())

  // Render-time comparison: clear stats when tree reference changes
  const [prevFoldersTree, setPrevFoldersTree] = useState(foldersTree)
  if (prevFoldersTree !== foldersTree) {
    setPrevFoldersTree(foldersTree)
    setStatsCache(new Map())
  }

  const handleFetchStats = useCallback(async (folderId: string) => {
    setStatsCache((prev) => {
      if (prev.has(folderId)) return prev
      const next = new Map(prev)
      next.set(folderId, { directFileCount: null, totalFileCount: null })
      return next
    })
    try {
      const [directResp, totalResp] = await Promise.all([
        getDocumentsPaginatedWithTimeout({
          folder_id: folderId, include_subfolders: false,
          page: 1, page_size: 1, sort_field: 'updated_at', sort_direction: 'desc',
        }),
        getDocumentsPaginatedWithTimeout({
          folder_id: folderId, include_subfolders: true,
          page: 1, page_size: 1, sort_field: 'updated_at', sort_direction: 'desc',
        }),
      ])
      setStatsCache((prev) => {
        const next = new Map(prev)
        next.set(folderId, {
          directFileCount: directResp.pagination?.total_count ?? 0,
          totalFileCount: totalResp.pagination?.total_count ?? 0,
        })
        return next
      })
    } catch { /* leave nulls */ }
  }, [])

  // Plain (non-memoized) recursive render function — safe for self-reference
  const renderTree = (nodes: FolderTreeNode[], depth: number): React.ReactNode =>
    nodes.map((node) => {
      const id = node.folder.id
      const isExpanded = expandedIds.has(id)
      const isSelected = selectedFolderId === id

      if (renamingId === id) {
        return (
          <InlineInput key={id} depth={depth} initialValue={renamingInitialName}
            placeholder={t('documentPanel.folderExplorer.namePlaceholder')}
            onConfirm={handleConfirmRename} onCancel={handleCancelRename} />
        )
      }

      return (
        <div key={id}>
          <FolderNode
            node={node} depth={depth} isSelected={isSelected} isExpanded={isExpanded}
            onToggleExpand={handleToggleExpand} onSelect={onSelectFolder}
            onStartCreate={handleStartCreate} onStartRename={handleStartRename} onDelete={handleStartDelete}
            onDragStart={handleDragStart} onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}
            dragOverId={dragOverId} draggedId={draggedId}
            statsCache={statsCache} onFetchStats={handleFetchStats}
          >
            {renderTree(node.children, depth + 1)}
          </FolderNode>
          {creatingUnder === id && isExpanded && (
            <InlineInput key={`create-under-${id}`} depth={depth + 1} initialValue=""
              placeholder={t('documentPanel.folderExplorer.namePlaceholder')}
              onConfirm={handleConfirmCreate} onCancel={handleCancelCreate} />
          )}
        </div>
      )
    })

  if (!isOpen) {
    return (
      <div className="flex flex-col items-center w-8 flex-none border-r border-border/50 bg-card py-2">
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onToggleOpen}
          tooltip={t('documentPanel.folderExplorer.showPanel')} side="right">
          <PanelLeftOpenIcon className="h-4 w-4" />
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-none w-56 border-r border-border/50 bg-card min-h-0">
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-border/50">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground select-none">
          {t('documentPanel.folderExplorer.title')}
        </span>
        <div className="flex items-center gap-0.5">
          <Button variant="ghost" size="icon" className="h-6 w-6"
            onClick={() => handleStartCreate(null)} disabled={isLoading || isCreating}
            tooltip={t('documentPanel.folderExplorer.newRootFolder')} side="bottom">
            <FolderPlusIcon className="h-3.5 w-3.5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-6 w-6"
            onClick={onTreeChanged} disabled={isLoading}
            tooltip={t('documentPanel.folderExplorer.refresh')} side="bottom">
            <RefreshCwIcon className={cn('h-3.5 w-3.5', isLoading && 'animate-spin')} />
          </Button>
          <Button variant="ghost" size="icon" className="h-6 w-6"
            onClick={onToggleOpen} tooltip={t('documentPanel.folderExplorer.hidePanel')} side="bottom">
            <PanelLeftCloseIcon className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden py-1 min-h-0"
        onDragOver={handleRootDragOver} onDragLeave={handleRootDragLeave} onDrop={handleRootDrop}>
        <div
          className={cn(
            'flex items-center gap-1.5 px-2 py-0.5 rounded cursor-pointer select-none text-sm mx-1',
            'hover:bg-accent hover:text-accent-foreground',
            selectedFolderId === null && 'bg-accent text-accent-foreground font-medium'
          )}
          onClick={() => onSelectFolder(null)}
        >
          <FilesIcon className="h-4 w-4 flex-none text-blue-500" />
          <span className="flex-1 truncate">{t('documentPanel.folderExplorer.allDocuments')}</span>
        </div>

        {creatingUnder === null && (
          <InlineInput depth={0} initialValue=""
            placeholder={t('documentPanel.folderExplorer.namePlaceholder')}
            onConfirm={handleConfirmCreate} onCancel={handleCancelCreate} />
        )}

        {isLoading ? (
          <div className="px-3 py-2 text-xs text-muted-foreground">{t('documentPanel.folderExplorer.loading')}</div>
        ) : foldersTree.length === 0 ? (
          <div className="px-3 py-2 text-xs text-muted-foreground">{t('documentPanel.folderExplorer.empty')}</div>
        ) : (
          renderTree(foldersTree, 0)
        )}
      </div>

      {selectedFolderId !== null && (
        <div className="border-t border-border/50 px-2 py-1.5">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-muted-foreground select-none">
            <input type="checkbox" className="h-3.5 w-3.5 rounded" checked={includeSubfolders}
              onChange={(e) => onIncludeSubfoldersChange(e.target.checked)} />
            {t('documentPanel.folderExplorer.includeSubfolders')}
          </label>
        </div>
      )}

      <DeleteConfirmDialog
        open={deletingFolder !== null}
        folderName={deletingFolder?.name ?? ''} hasChildren={deletingFolder?.hasChildren ?? false}
        isDeleting={isDeleting} onConfirm={handleConfirmDelete} onCancel={() => setDeletingFolder(null)}
      />
    </div>
  )
}
