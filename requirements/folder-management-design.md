# 文档目录管理功能 — 详细设计说明

> 版本: v1.0  
> 日期: 2026-05-30  
> 作者: GitHub Copilot  
> 状态: 设计草稿

---

## 1. 需求概述

在现有 LightRAG API 服务基础上，增加多级文档目录（Folder）管理能力，并将目录与文档关联，支持按目录范围进行上传、查询、删除等操作。

| # | 需求 |
|---|------|
| R1 | 支持多级目录管理（树形结构） |
| R2 | 目录的增删改查 API |
| R3 | 上传文件/文本时必须指定目录 ID |
| R4 | 查询（RAG query）和文档状态查询支持按目录范围过滤；不指定则查全部 |
| R5 | 删除文档、查询处理进度也支持按目录范围过滤 |

---

## 2. 现有架构分析

### 2.1 文档存储机制

LightRAG 将文档处理状态保存在 `DocStatusStorage`（`BaseKVStorage` 子类）中，每条记录对应一个 `DocProcessingStatus` 数据类：

```
DocProcessingStatus {
    content_summary: str
    content_length: int
    file_path: str
    status: DocStatus          # PENDING/PROCESSING/PREPROCESSED/PROCESSED/FAILED
    created_at: str
    updated_at: str
    track_id: str | None
    chunks_count: int | None
    chunks_list: list[str]
    error_msg: str | None
    metadata: dict             # 现有扩展字段
    multimodal_processed: bool | None
}
```

`metadata` 字段是一个开放 `dict`，已用于存储附加信息，**可利用该字段存储 `folder_id`**，保持向后兼容。

### 2.2 知识图谱存储机制

所有文档的实体（Entity）和关系（Relation）被合并存储在同一个 `BaseGraphStorage` 和 `BaseVectorStorage` 实例中。Chunk 在向量存储中有 `full_doc_id` 字段，通过该字段可反向找到所属文档，进而找到目录。

### 2.3 关键代码位置

| 文件 | 作用 |
|------|------|
| `lightrag/api/routers/document_routes.py` | 文档上传、删除、状态查询路由（~3000行） |
| `lightrag/api/routers/query_routes.py` | RAG 查询路由 |
| `lightrag/base.py` | `DocProcessingStatus`、`DocStatusStorage`、`QueryParam` 抽象定义 |
| `lightrag/lightrag.py` | `LightRAG` 核心类，`ainsert`、`aquery`、`adelete_by_doc_id` 等 |
| `lightrag/api/lightrag_server.py` | FastAPI App 工厂，路由注册 |
| `lightrag/kg/` | 各存储后端实现（JSON/Neo4j/PG/Mongo 等） |

---

## 3. 数据模型设计

### 3.1 Folder 数据结构

```python
@dataclass
class FolderInfo:
    id: str                          # 目录唯一 ID，格式: "folder-{uuid4}"
    name: str                        # 目录名称，同层级下唯一
    parent_id: str | None            # 父目录 ID；None 表示根目录
    workspace: str                   # 所属 workspace
    description: str                 # 目录描述（可选）
    created_at: str                  # ISO 8601 创建时间
    updated_at: str                  # ISO 8601 更新时间
    metadata: dict[str, Any]         # 扩展字段
```

#### 约束规则

- `name` 在同一 `parent_id` + `workspace` 范围内唯一
- 删除目录时，若目录下有文档或子目录，拒绝删除（默认），或支持 `force=true` 级联删除
- 目录层级深度不作显式限制，由调用方控制合理深度
- `workspace` 字段与 LightRAG 现有 workspace 隔离机制对齐

### 3.2 Document 与 Folder 的关联

在 `DocProcessingStatus.metadata` 中增加 `folder_id` 字段：

```python
# 现有 metadata 结构示例（新增 folder_id）
metadata = {
    "folder_id": "folder-550e8400-e29b-41d4-a716-446655440000",  # 新增
    # ... 其他已有字段 ...
}
```

**选择 metadata 而非新增顶层字段的原因：**
1. `DocProcessingStatus` 是序列化存储的数据类，修改签名需要同步更新所有存储实现
2. `metadata` 是专为扩展预留的 `dict`，各存储后端均已支持
3. 旧文档 `folder_id` 默认为 `None`（未分类），业务层统一处理

### 3.3 Folder 存储

#### 存储位置

新增存储命名空间 `doc_folders`，复用现有 `BaseKVStorage` 接口，键为 `folder_id`，值为 `FolderInfo` 的序列化字典。

#### 各存储后端存储位置

| 存储后端 | Folder 数据位置 |
|---------|----------------|
| JSON（默认） | `{working_dir}/{workspace}/kv_store_doc_folders.json` |
| PostgreSQL | `lightrag_doc_folders_{workspace}` 表 |
| MongoDB | `lightrag_doc_folders_{workspace}` collection |
| Redis | key prefix `lightrag:doc_folders:{workspace}:` |

---

## 4. API 接口设计

所有新增接口都挂载在 `/documents/folders` 路径下，tags 为 `["folders"]`，遵循现有认证机制（`combined_auth`）。

---

### 4.1 Folder CRUD API

#### 4.1.1 创建目录

```
POST /documents/folders
```

**请求体：**

```json
{
    "name": "技术文档",
    "parent_id": null,
    "description": "存放技术相关文档",
    "metadata": {}
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 目录名称，1-255字符，不允许包含 `/` `\` |
| `parent_id` | string \| null | ❌ | 父目录 ID；null 为根目录 |
| `description` | string | ❌ | 目录描述 |
| `metadata` | object | ❌ | 扩展信息 |

**响应体（201 Created）：**

```json
{
    "id": "folder-550e8400-e29b-41d4-a716-446655440000",
    "name": "技术文档",
    "parent_id": null,
    "description": "存放技术相关文档",
    "created_at": "2026-05-30T10:00:00+00:00",
    "updated_at": "2026-05-30T10:00:00+00:00",
    "metadata": {}
}
```

**错误响应：**

| HTTP 状态码 | 场景 |
|-------------|------|
| 400 | 名称包含非法字符 |
| 404 | `parent_id` 不存在 |
| 409 | 同层级同名目录已存在 |

---

#### 4.1.2 获取目录列表

```
GET /documents/folders
```

**Query 参数：**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `parent_id` | string \| null | （不传）= 查全部 | 按父级过滤；传 `root` 表示只查根目录 |
| `recursive` | bool | false | 是否递归返回所有子孙目录 |

**响应体（200 OK）：**

```json
{
    "folders": [
        {
            "id": "folder-550e8400-...",
            "name": "技术文档",
            "parent_id": null,
            "description": "...",
            "created_at": "...",
            "updated_at": "...",
            "child_count": 3,
            "doc_count": 12,
            "metadata": {}
        }
    ],
    "total": 1
}
```

---

#### 4.1.3 获取单个目录

```
GET /documents/folders/{folder_id}
```

**响应体（200 OK）：**

```json
{
    "id": "folder-550e8400-...",
    "name": "技术文档",
    "parent_id": null,
    "description": "...",
    "created_at": "...",
    "updated_at": "...",
    "child_count": 3,
    "doc_count": 12,
    "path": ["技术文档"],
    "ancestors": [],
    "metadata": {}
}
```

`path` 为从根到当前目录的名称列表；`ancestors` 为祖先目录 ID 列表（不含自身）。

---

#### 4.1.4 更新目录

```
PUT /documents/folders/{folder_id}
```

**请求体（仅传需要修改的字段）：**

```json
{
    "name": "技术文档（更新）",
    "description": "新的描述",
    "parent_id": "folder-another-id"
}
```

**说明：**
- 更新 `parent_id` 即移动目录（不允许将父目录设为自身或自身的子孙）
- `name` 更新需重新校验同层唯一性

**响应体（200 OK）：** 同创建接口响应结构

---

#### 4.1.5 删除目录

```
DELETE /documents/folders/{folder_id}?force=false
```

**Query 参数：**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `force` | bool | false | true = 级联删除所有子目录及文档（将触发文档删除流水线） |

**响应体（200 OK）：**

```json
{
    "status": "success",
    "message": "目录已删除",
    "deleted_folders": 1,
    "deleted_docs": 0
}
```

**错误响应：**

| HTTP 状态码 | 场景 |
|-------------|------|
| 404 | 目录不存在 |
| 409 | 目录下有内容且 `force=false` |

---

#### 4.1.6 获取目录树

```
GET /documents/folders/tree
```

返回当前 workspace 下完整的目录树结构（含文档数统计）。

**响应体（200 OK）：**

```json
{
    "tree": [
        {
            "id": "folder-root-1",
            "name": "项目文档",
            "parent_id": null,
            "doc_count": 5,
            "children": [
                {
                    "id": "folder-child-1",
                    "name": "需求文档",
                    "parent_id": "folder-root-1",
                    "doc_count": 3,
                    "children": []
                }
            ]
        }
    ]
}
```

---

### 4.2 文档上传接口变更

所有上传接口新增必填字段 `folder_id`（向后兼容方案见 §7）。

#### 4.2.1 上传文件

```
POST /documents/upload
```

**变更点（multipart form 新增字段）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `folder_id` | string | ✅（新增） | 目标目录 ID |

**示例（curl）：**
```bash
curl -X POST /documents/upload \
  -F "file=@document.pdf" \
  -F "folder_id=folder-550e8400-..."
```

---

#### 4.2.2 上传文本

```
POST /documents/text
```

**请求体变更（新增 `folder_id`）：**

```json
{
    "text": "This is a sample text...",
    "file_source": "manual_input",
    "folder_id": "folder-550e8400-..."
}
```

---

#### 4.2.3 批量上传文本

```
POST /documents/texts
```

**请求体变更（新增 `folder_id`）：**

```json
{
    "texts": ["text1", "text2"],
    "file_sources": ["source1", "source2"],
    "folder_id": "folder-550e8400-..."
}
```

> **注意：** 批量文本共享同一个 `folder_id`，不支持每条文本单独指定目录。

---

### 4.3 文档查询接口变更

#### 4.3.1 分页查询文档列表

```
POST /documents
```

**请求体新增字段：**

```json
{
    "status_filter": "PROCESSED",
    "page": 1,
    "page_size": 50,
    "folder_id": "folder-550e8400-...",
    "include_subfolders": true
}
```

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `folder_id` | string \| null | null | 按目录过滤；null 表示不过滤（查全部） |
| `include_subfolders` | bool | true | 是否包含子目录下的文档 |

**响应体变更（`DocStatusResponse` 增加 `folder_id` 字段）：**

```json
{
    "documents": [
        {
            "id": "doc_123456",
            "file_path": "research_paper.pdf",
            "folder_id": "folder-550e8400-...",
            "folder_path": "项目文档/技术文档",
            "status": "PROCESSED",
            ...
        }
    ],
    "pagination": {...},
    "status_counts": {...}
}
```

---

#### 4.3.2 查询进度（Track Status）

```
GET /documents/status/{track_id}
```

**Query 参数新增：**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `folder_id` | string | null | 按目录过滤返回结果（可选） |

---

#### 4.3.3 文档状态总览

```
GET /documents/status/counts
```

**Query 参数新增：**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `folder_id` | string | null | 按目录过滤统计（可选） |
| `include_subfolders` | bool | true | 是否包含子目录 |

---

### 4.4 文档删除接口变更

#### 4.4.1 按 doc_ids 删除

```
DELETE /documents
```

**请求体（现有结构，无变更）：** 仍通过 `doc_ids` 指定，不需要额外 `folder_id`（因为删除时已知具体 ID）。

---

#### 4.4.2 按目录批量删除（新增）

```
DELETE /documents/folders/{folder_id}/documents
```

**Query 参数：**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `include_subfolders` | bool | false | 是否同时删除子目录文档 |
| `delete_file` | bool | false | 是否删除物理文件 |
| `delete_llm_cache` | bool | false | 是否删除 LLM 缓存 |

**响应体（200 OK）：**

```json
{
    "status": "success",
    "message": "批量删除已启动，共 N 个文档",
    "doc_count": 42,
    "track_id": "delete_20260530_100000_abc123"
}
```

---

### 4.5 RAG 查询接口变更

```
POST /query
POST /query/stream
POST /query/data
```

**请求体新增字段（`QueryRequest`）：**

```json
{
    "query": "What is machine learning?",
    "mode": "mix",
    "folder_ids": ["folder-550e8400-...", "folder-another-..."],
    "include_subfolders": true
}
```

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `folder_ids` | list[string] \| null | null | 限制检索范围到指定目录的文档；null 或空列表 = 全量检索 |
| `include_subfolders` | bool | true | 是否包含子目录下文档（`folder_ids` 非空时生效） |

**说明：** 目录范围过滤作用于向量检索阶段（Chunk 过滤），知识图谱（实体/关系）的检索不受影响（因图谱是全局共享的）。

---

## 5. 核心实现方案

### 5.1 Folder 存储管理类

新建 `lightrag/kg/folder_storage.py`，实现 `FolderManager`：

```python
class FolderManager:
    """
    管理文档目录树，基于现有 BaseKVStorage 存储 FolderInfo。
    每个 workspace 对应一个独立的 FolderManager 实例。
    """
    
    def __init__(self, kv_storage: BaseKVStorage, workspace: str):
        self._storage = kv_storage
        self._workspace = workspace
    
    async def create_folder(
        self, name: str, parent_id: str | None = None,
        description: str = "", metadata: dict = None
    ) -> FolderInfo: ...
    
    async def get_folder(self, folder_id: str) -> FolderInfo | None: ...
    
    async def list_folders(
        self, parent_id: str | None = None, recursive: bool = False
    ) -> list[FolderInfo]: ...
    
    async def update_folder(
        self, folder_id: str, name: str | None = None,
        parent_id: str | None = None, description: str | None = None,
        metadata: dict | None = None
    ) -> FolderInfo: ...
    
    async def delete_folder(
        self, folder_id: str, force: bool = False
    ) -> dict[str, int]: ...
    
    async def get_folder_tree(self) -> list[dict]: ...
    
    async def get_ancestors(self, folder_id: str) -> list[FolderInfo]: ...
    
    async def get_descendant_ids(self, folder_id: str) -> list[str]:
        """递归获取所有子孙目录 ID（含自身）"""
        ...
    
    async def validate_no_circular_reference(
        self, folder_id: str, new_parent_id: str
    ) -> bool: ...
```

### 5.2 DocStatusStorage 新增方法

在 `lightrag/base.py` 的 `DocStatusStorage` 抽象类中新增：

```python
@abstractmethod
async def get_docs_by_folder_ids(
    self,
    folder_ids: list[str],
    status_filter: DocStatus | None = None,
    page: int = 1,
    page_size: int = 50,
    sort_field: str = "updated_at",
    sort_direction: str = "desc",
) -> tuple[list[tuple[str, DocProcessingStatus]], int]:
    """按目录 ID 列表分页查询文档（支持多目录）"""

@abstractmethod
async def get_doc_ids_by_folder_ids(
    self, folder_ids: list[str]
) -> list[str]:
    """获取指定目录列表下所有文档的 ID 列表（用于批量删除/向量过滤）"""

@abstractmethod
async def get_status_counts_by_folder_ids(
    self, folder_ids: list[str]
) -> dict[str, int]:
    """获取指定目录列表下的文档状态统计"""
```

### 5.3 向量检索的目录范围过滤

`BaseVectorStorage.query()` 现有签名：

```python
async def query(
    self, query: str, top_k: int, query_embedding: list[float] = None
) -> list[dict[str, Any]]:
```

**方案：两阶段过滤**

不修改向量存储接口，在 `operate.py` 中实现应用层过滤：

```python
async def _get_doc_ids_for_folder_filter(
    doc_status_storage: DocStatusStorage,
    folder_ids: list[str]
) -> set[str]:
    """查询目录范围内的文档 ID 集合"""
    ids = await doc_status_storage.get_doc_ids_by_folder_ids(folder_ids)
    return set(ids)

async def _filter_chunks_by_doc_ids(
    chunks: list[dict], allowed_doc_ids: set[str]
) -> list[dict]:
    """从检索到的 chunks 中过滤出属于指定文档的部分"""
    return [c for c in chunks if c.get("full_doc_id") in allowed_doc_ids]
```

在 `operate.py` 的 `_get_node_data`、`_get_edge_data`、`_get_chunks_data` 等函数中，  
当 `QueryParam.folder_ids` 非空时，对检索结果进行后置过滤。

> **注意：** 这种方案在目录文档数量极大时效率较低（需要检索更多 top_k 再过滤）。  
> 高性能方案是在向量存储层添加 metadata filter 支持，作为 Phase 2 优化。

### 5.4 QueryParam 扩展

在 `lightrag/base.py` 的 `QueryParam` 中新增：

```python
@dataclass
class QueryParam:
    # ... 现有字段 ...
    
    folder_ids: list[str] | None = None
    """限制检索范围到指定目录 ID 列表的文档。None 或空列表表示全量检索。"""
    
    include_subfolders: bool = True
    """当 folder_ids 非空时，是否自动包含子目录下的文档。"""
```

### 5.5 新增路由文件

新建 `lightrag/api/routers/folder_routes.py`：

```python
def create_folder_routes(rag: LightRAG, api_key: Optional[str] = None) -> APIRouter:
    router = APIRouter(prefix="/documents/folders", tags=["folders"])
    folder_manager = FolderManager(...)
    combined_auth = get_combined_auth_dependency(api_key)
    
    # CRUD endpoints...
    return router
```

在 `lightrag_server.py` 中注册：

```python
from lightrag.api.routers.folder_routes import create_folder_routes

app.include_router(create_folder_routes(rag, api_key))
```

---

## 6. 数据流设计

### 6.1 上传文件流程（含目录）

```
Client → POST /documents/upload (file + folder_id)
  │
  ├─ [1] 校验 folder_id 存在（FolderManager.get_folder）
  │
  ├─ [2] 保存文件到 input_dir
  │
  ├─ [3] 生成 track_id，调用 rag.ainsert()
  │
  └─ [4] 在 DocProcessingStatus.metadata 中写入 folder_id
         doc_status_storage.upsert({doc_id: {metadata: {folder_id: ...}}})
```

### 6.2 按目录 RAG 查询流程

```
Client → POST /query (query + folder_ids)
  │
  ├─ [1] folder_ids 非空 → 递归展开子目录（include_subfolders=true）
  │       得到 expanded_folder_ids
  │
  ├─ [2] doc_status_storage.get_doc_ids_by_folder_ids(expanded_folder_ids)
  │       得到 allowed_doc_ids（文档 ID 白名单）
  │
  ├─ [3] 传入 QueryParam(folder_ids=expanded_folder_ids, ...)
  │       进入 operate.py 检索流水线
  │
  ├─ [4] vector_storage.query(query, top_k * 3)  # 多取以备过滤
  │       → 过滤 chunks: keep where full_doc_id in allowed_doc_ids
  │
  └─ [5] 正常 LLM 生成，返回结果（references 中的 file_path 也只含该目录文档）
```

### 6.3 按目录删除文档流程

```
Client → DELETE /documents/folders/{folder_id}/documents
  │
  ├─ [1] FolderManager.get_descendant_ids(folder_id, include_self=true)
  │
  ├─ [2] doc_status_storage.get_doc_ids_by_folder_ids(folder_ids)
  │
  ├─ [3] 批量调用 rag.adelete_by_doc_id() 异步删除
  │
  └─ [4] 返回 track_id（可通过 /documents/pipeline/status 查询进度）
```

---

## 7. 向后兼容策略

| 场景 | 处理方式 |
|------|---------|
| 旧文档（无 `folder_id`）| `metadata.get("folder_id")` 返回 `None`，属于"未分类"文档 |
| 上传接口 `folder_id` 必填 | 提供迁移期过渡：初始阶段设为**可选**，自动归入默认根目录 `__default__`，文档注明计划将来设为必填 |
| 查询接口不传 `folder_ids` | 行为与现在完全一致，查全部文档 |
| RAG 查询不传 `folder_ids` | `QueryParam.folder_ids=None`，跳过过滤逻辑，行为不变 |

---

## 8. 分阶段实施计划

### Phase 1：目录 CRUD + 文档关联（核心功能）

**目标：** 目录管理可用，上传时可关联目录，文档列表支持目录过滤。

**工作项：**

1. `lightrag/base.py` — 新增 `FolderInfo` dataclass
2. `lightrag/base.py` — `DocStatusStorage` 新增 3 个抽象方法
3. `lightrag/kg/json_kv_impl.py`（及其他存储后端）— 实现新增方法
4. `lightrag/kg/folder_storage.py` — `FolderManager` 实现
5. `lightrag/api/routers/folder_routes.py` — 目录 CRUD 路由（6 个接口）
6. `lightrag/api/routers/document_routes.py` — 上传接口增加 `folder_id` 字段
7. `lightrag/api/routers/document_routes.py` — 文档列表查询增加目录过滤
8. `lightrag/api/lightrag_server.py` — 注册新路由
9. 单元测试 `tests/test_folder_management.py`

### Phase 2：删除和进度查询的目录过滤

**目标：** 支持按目录批量删除文档，进度查询支持目录过滤。

**工作项：**

1. `lightrag/api/routers/document_routes.py` — 新增按目录删除接口
2. `lightrag/api/routers/document_routes.py` — Track Status 增加目录过滤
3. `lightrag/api/routers/document_routes.py` — 状态统计增加目录过滤

### Phase 3：RAG 查询的目录范围过滤

**目标：** `QueryParam` 支持 `folder_ids`，向量检索阶段按文档范围过滤。

**工作项：**

1. `lightrag/base.py` — `QueryParam` 新增 `folder_ids`、`include_subfolders`
2. `lightrag/operate.py` — 检索阶段增加 doc_id 过滤逻辑
3. `lightrag/api/routers/query_routes.py` — `QueryRequest` 增加 `folder_ids`
4. 集成测试

### Phase 4（可选）：向量存储原生 metadata filter

**目标：** 替代应用层过滤，在向量存储层支持 `where doc_id IN (...)` 形式的过滤，提升大规模场景下的性能。

涉及各存储后端（Qdrant、PGVector、Milvus 等）的 `query()` 方法扩展。

---

## 9. 安全考虑

| 风险 | 缓解措施 |
|------|---------|
| `folder_id` 注入 | `folder_id` 格式校验：`^folder-[0-9a-f-]{36}$` |
| 目录名称 XSS/特殊字符 | `name` 字段过滤 `/`、`\`、控制字符 |
| 跨 workspace 访问 | `FolderManager` 查询始终附带 `workspace` 条件，禁止跨 workspace 访问 |
| 循环引用 | `update_folder` 移动目录时校验不形成环（向上遍历祖先链） |
| 级联删除 DoS | `force=true` 的级联删除需额外权限或二次确认（可选） |

---

## 10. Pydantic 模型变更汇总

### 新增模型

```python
# lightrag/api/routers/folder_routes.py

class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: Optional[str] = None
    description: str = ""
    metadata: dict = Field(default_factory=dict)

class FolderUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    parent_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None

class FolderResponse(BaseModel):
    id: str
    name: str
    parent_id: Optional[str]
    description: str
    created_at: str
    updated_at: str
    child_count: int = 0
    doc_count: int = 0
    path: Optional[list[str]] = None        # 从根到自身的名称列表
    ancestors: Optional[list[str]] = None   # 祖先 folder_id 列表
    metadata: dict

class FolderListResponse(BaseModel):
    folders: list[FolderResponse]
    total: int

class FolderTreeNode(BaseModel):
    id: str
    name: str
    parent_id: Optional[str]
    doc_count: int
    children: list["FolderTreeNode"]

class FolderTreeResponse(BaseModel):
    tree: list[FolderTreeNode]

class FolderDeleteResponse(BaseModel):
    status: Literal["success", "fail"]
    message: str
    deleted_folders: int
    deleted_docs: int
```

### 修改已有模型

```python
# document_routes.py

class InsertTextRequest(BaseModel):
    text: str
    file_source: Optional[str] = None
    folder_id: Optional[str] = None   # 新增（过渡期可选，Phase1后设为必填）

class InsertTextsRequest(BaseModel):
    texts: list[str]
    file_sources: Optional[list[str]] = None
    folder_id: Optional[str] = None   # 新增

class DocumentsRequest(BaseModel):
    # ... 现有字段 ...
    folder_id: Optional[str] = None            # 新增：按目录过滤
    include_subfolders: bool = True            # 新增

class DocStatusResponse(BaseModel):
    # ... 现有字段 ...
    folder_id: Optional[str] = None            # 新增
    folder_path: Optional[str] = None          # 新增（如 "项目文档/技术文档"）

# query_routes.py

class QueryRequest(BaseModel):
    # ... 现有字段 ...
    folder_ids: Optional[list[str]] = None     # 新增
    include_subfolders: bool = True            # 新增
```

---

## 11. 目录结构变更

```
lightrag/
├── base.py                         # 修改：FolderInfo, DocStatusStorage 新方法, QueryParam 新字段
├── kg/
│   ├── folder_storage.py           # 新增：FolderManager 实现
│   ├── json_kv_impl.py             # 修改：实现新增 DocStatusStorage 方法
│   ├── pg_impl.py                  # 修改：实现新增 DocStatusStorage 方法
│   └── ...                         # 其他存储后端同理
├── operate.py                      # 修改（Phase 3）：向量检索目录过滤
└── api/
    └── routers/
        ├── folder_routes.py        # 新增：目录 CRUD 路由
        ├── document_routes.py      # 修改：上传/查询/删除增加目录支持
        └── query_routes.py         # 修改（Phase 3）：QueryRequest 增加 folder_ids

requirements/
└── folder-management-design.md    # 本文档

tests/
└── test_folder_management.py       # 新增
```

---

## 12. 接口总览

| 方法 | 路径 | 说明 | 阶段 |
|------|------|------|------|
| `POST` | `/documents/folders` | 创建目录 | Phase 1 |
| `GET` | `/documents/folders` | 查询目录列表 | Phase 1 |
| `GET` | `/documents/folders/tree` | 获取完整目录树 | Phase 1 |
| `GET` | `/documents/folders/{folder_id}` | 获取单个目录详情 | Phase 1 |
| `PUT` | `/documents/folders/{folder_id}` | 更新目录 | Phase 1 |
| `DELETE` | `/documents/folders/{folder_id}` | 删除目录 | Phase 1 |
| `POST` | `/documents/upload` | 上传文件（新增 `folder_id`） | Phase 1 |
| `POST` | `/documents/text` | 上传文本（新增 `folder_id`） | Phase 1 |
| `POST` | `/documents/texts` | 批量上传文本（新增 `folder_id`） | Phase 1 |
| `POST` | `/documents` | 分页查询文档（新增 `folder_id` 过滤） | Phase 1 |
| `GET` | `/documents/status/counts` | 文档状态统计（新增 `folder_id` 过滤） | Phase 2 |
| `GET` | `/documents/status/{track_id}` | 查询处理进度（新增 `folder_id` 过滤） | Phase 2 |
| `DELETE` | `/documents/folders/{folder_id}/documents` | 按目录批量删除文档 | Phase 2 |
| `POST` | `/query` | RAG 查询（新增 `folder_ids` 过滤） | Phase 3 |
| `POST` | `/query/stream` | 流式 RAG 查询（新增 `folder_ids` 过滤） | Phase 3 |
| `POST` | `/query/data` | 结构化 RAG 查询（新增 `folder_ids` 过滤） | Phase 3 |
