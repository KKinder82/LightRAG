/**
 * GraphFolderFilter — A popover button that lets users filter the knowledge graph by folder.
 * When a folder is selected, the graph shows only entities/relations from documents
 * in that folder (and optionally its sub-folders).
 */
import { useState, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { FolderIcon, XIcon } from 'lucide-react'
import { useSettingsStore } from '@/stores/settings'
import { useGraphStore } from '@/stores/graph'
import { getFolderTree, FolderTreeNode } from '@/api/lightrag'
import { controlButtonVariant } from '@/lib/constants'
import Button from '@/components/ui/Button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/Popover'

// Flatten a folder tree into a list of [indent level, node] pairs
function flattenTree(nodes: FolderTreeNode[], depth = 0): Array<{ node: FolderTreeNode; depth: number }> {
  const result: Array<{ node: FolderTreeNode; depth: number }> = []
  for (const n of nodes) {
    result.push({ node: n, depth })
    if (n.children.length > 0) {
      result.push(...flattenTree(n.children, depth + 1))
    }
  }
  return result
}

const GraphFolderFilter = () => {
  const { t } = useTranslation()
  const graphFolderId = useSettingsStore.use.graphFolderId()
  const setGraphFolderId = useSettingsStore.use.setGraphFolderId()

  const [folderTree, setFolderTree] = useState<FolderTreeNode[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [open, setOpen] = useState(false)

  const flatFolders = useMemo(() => flattenTree(folderTree), [folderTree])

  // Derive selected folder name from flat list (no extra effect needed)
  const selectedFolderName = useMemo(() => {
    if (!graphFolderId) return null
    return flatFolders.find((f) => f.node.folder.id === graphFolderId)?.node.folder.name ?? null
  }, [graphFolderId, flatFolders])

  // Load folder tree when popover opens for the first time
  const handleOpenChange = useCallback(async (nextOpen: boolean) => {
    setOpen(nextOpen)
    if (nextOpen && folderTree.length === 0) {
      setIsLoading(true)
      try {
        const tree = await getFolderTree()
        setFolderTree(tree)
      } catch (e) {
        console.error('Failed to load folder tree', e)
      } finally {
        setIsLoading(false)
      }
    }
  }, [folderTree.length])

  const handleSelectFolder = useCallback(
    (folderId: string) => {
      setOpen(false)
      useGraphStore.getState().setGraphDataFetchAttempted(false)
      useGraphStore.getState().incrementGraphDataVersion()
      setGraphFolderId(folderId)
    },
    [setGraphFolderId]
  )

  const handleClear = useCallback(() => {
    useGraphStore.getState().setGraphDataFetchAttempted(false)
    useGraphStore.getState().incrementGraphDataVersion()
    setGraphFolderId(null)
  }, [setGraphFolderId])

  return (
    <div className="flex items-center gap-1">
      <Popover open={open} onOpenChange={handleOpenChange}>
        <PopoverTrigger asChild>
          <Button
            size="icon"
            variant={graphFolderId ? 'default' : controlButtonVariant}
            tooltip={
              graphFolderId
                ? t('graphPanel.folderFilter.activeTooltip', { folder: selectedFolderName ?? graphFolderId })
                : t('graphPanel.folderFilter.selectTooltip')
            }
          >
            <FolderIcon className="h-4 w-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent align="start" className="p-1 max-h-80 overflow-y-auto min-w-[220px] w-auto">
          {isLoading ? (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              {t('graphPanel.folderFilter.loading')}
            </div>
          ) : flatFolders.length === 0 ? (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              {t('graphPanel.folderFilter.noFolders')}
            </div>
          ) : (
            <div className="flex flex-col gap-0.5">
              {flatFolders.map(({ node, depth }) => (
                <button
                  key={node.folder.id}
                  onClick={() => handleSelectFolder(node.folder.id)}
                  className={`flex w-full items-center gap-1 rounded-sm px-2 py-1.5 text-sm hover:bg-accent text-left truncate ${
                    graphFolderId === node.folder.id ? 'bg-accent font-medium' : ''
                  }`}
                  style={{ paddingLeft: `${8 + depth * 12}px` }}
                >
                  <FolderIcon className="h-3 w-3 shrink-0" />
                  <span className="truncate">{node.folder.name}</span>
                </button>
              ))}
            </div>
          )}
        </PopoverContent>
      </Popover>

      {/* Clear button when a folder is selected */}
      {graphFolderId && (
        <Button
          size="icon"
          variant="ghost"
          onClick={handleClear}
          tooltip={t('graphPanel.folderFilter.clearFolderFilter')}
          className="h-6 w-6"
        >
          <XIcon className="h-3 w-3" />
        </Button>
      )}
    </div>
  )
}

export default GraphFolderFilter
