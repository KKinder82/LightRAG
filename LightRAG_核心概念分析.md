# LightRAG 项目核心概念详解

## 1. 知识图谱（Knowledge Graph）的核心功能

### 1.1 核心功能概览

LightRAG 的知识图谱系统包含三个主要存储层：

```python
# 四大存储类型（lightrag/base.py）
- KV_STORAGE: LLM 响应缓存、文本块、文档信息
- VECTOR_STORAGE: 实体/关系/文本块的向量嵌入
- GRAPH_STORAGE: 知识图谱的拓扑结构（节点和边）
- DOC_STATUS_STORAGE: 文档处理状态跟踪
```

### 1.2 实体处理（Entity Processing）

**实体数据结构**（lightrag/types.py）:
```python
class ExtractedEntity(BaseModel):
    entity_name: str              # 实体名称（标题大小写）
    entity_type: str              # 实体类型（如：PERSON, ORGANIZATION）
    entity_description: str       # 基于输入文本的综合描述

# 实体在图中的完整数据
node_data = {
    "entity_id": "entity_name",
    "entity_type": "PERSON",
    "description": "Comprehensive description",
    "source_id": "chunk1<|>chunk2<|>chunk3",      # 源块 ID 集合
    "file_path": "file1.pdf<|>file2.pdf",         # 文件路径集合
    "created_at": 1234567890,                     # 创建时间戳
    "truncate": "KEEP 10/50"                      # 截断信息
}
```

**实体提取流程**（lightrag/operate.py）:
```python
async def extract_entities(
    chunks: dict[str, TextChunkSchema],
    global_config: dict[str, str],
    # ... 其他参数
) -> list:
    # 1. 对每个文本块调用 LLM 进行实体提取
    # 2. 支持两种格式：
    #    - JSON 格式（entity_extraction_use_json=True）
    #    - 分隔符格式（默认）
    
    # 3. Gleaning 阶段：第二次 LLM 调用以获取遗漏的实体
    # 4. 多模态增强：为表格/图表/方程自动添加实体
    
    return chunk_results  # [(nodes_dict, edges_dict), ...]
```

### 1.3 关系处理（Relationship Processing）

**关系数据结构**:
```python
class ExtractedRelationship(BaseModel):
    source_entity: str                  # 源实体
    target_entity: str                  # 目标实体
    relationship_keywords: str          # 关系关键词（逗号分隔）
    relationship_description: str       # 关系描述

# 关系在图中的完整数据
edge_data = {
    "src_id": "Entity1",
    "tgt_id": "Entity2",
    "weight": 1.5,                           # 关系权重（值越大越重要）
    "description": "Entity1 manages Entity2",
    "keywords": "manage, control, lead",
    "source_id": "chunk1<|>chunk2",          # 源块集合
    "file_path": "file1.pdf<|>file2.pdf",
    "created_at": 1234567890,
    "truncate": "KEEP 5/20"
}
```

**关系合并逻辑**（lightrag/operate.py - `_merge_edges_then_upsert`）:
```python
# 关系合并的主要步骤：
# 1. 获取已存在的关系数据
# 2. 合并新的源 ID（chunk IDs）- 使用 merge_source_ids()
# 3. 应用源 ID 限制（max_source_ids_per_relation）
# 4. 合并描述文本 - 如果有多个，使用 LLM 总结
# 5. 合并关键词 - 去重并保留所有关键词
# 6. 计算权重 - 对所有权重求和
# 7. 限制文件路径数量 - 应用 max_file_paths 限制
# 8. 同时更新图存储和向量存储
```

---

## 2. 主要 API 和调用入口

### 2.1 核心入口类 - LightRAG（lightrag/lightrag.py）

```python
@final
@dataclass
class LightRAG(_RoleLLMMixin, _StorageMigrationMixin, _PipelineMixin):
    """主类通过 mixin 组织，实现关注点分离"""
    
    working_dir: str = "./rag_storage"
    workspace: str = "default"
    llm_model_func: Callable  # LLM 函数
    embedding_func: EmbeddingFunc  # 嵌入函数
    
    # 存储配置
    kv_storage: str = "JsonKVStorage"
    vector_storage: str = "NanoVectorDB"
    graph_storage: str = "NetworkXStorage"
    doc_status_storage: str = "JsonDocStatusStorage"
```

### 2.2 关键 API 方法

#### **文档插入（ainsert）**
```python
# 单个文档
await rag.ainsert("Your text here")

# 批量文档
await rag.ainsert(["Text 1", "Text 2", ...])

# 带自定义 ID 和文件路径
await rag.ainsert(
    ["Text 1", "Text 2"],
    ids=["doc-1", "doc-2"],
    file_paths=["doc1.pdf", "doc2.pdf"]
)

# 完整示例
import asyncio
from lightrag import LightRAG
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed

async def main():
    # ⚠️ 关键：必须初始化存储
    rag = LightRAG(
        working_dir="./rag_storage",
        llm_model_func=gpt_4o_mini_complete,
        embedding_func=openai_embed
    )
    await rag.initialize_storages()  # 必须！
    
    # 插入文档
    await rag.ainsert("AI 是改变世界的技术...")
    
    # 查询
    result = await rag.aquery("AI 的未来是什么？")
    print(result)
    
    # 清理
    await rag.finalize_storages()

asyncio.run(main())
```

#### **查询（aquery）**
```python
from lightrag import QueryParam

# 基础查询
result = await rag.aquery("Your question")

# 自定义参数查询
result = await rag.aquery(
    "Your question",
    param=QueryParam(
        mode="mix",                    # 查询模式
        top_k=60,                      # KG 实体/关系检索数量
        chunk_top_k=20,                # 文本块检索数量
        max_entity_tokens=6000,        # 实体最大令牌数
        max_relation_tokens=8000,      # 关系最大令牌数
        max_total_tokens=30000,        # 总令牌数
        enable_rerank=True,            # 启用重新排序
        user_prompt="请用简洁的语言回答",
        stream=False                   # 非流式返回
    )
)

print(result.content)      # LLM 生成的答案
print(result.raw_data)     # 完整的上下文数据
```

#### **实体操作**
```python
# 获取实体信息
entity_info = await rag.get_entity_info("Elon Musk")
print(entity_info["description"])
print(entity_info["entity_type"])

# 编辑实体
await rag.aedit_entity(
    "Elon Musk",
    updated_data={"description": "新的描述信息"},
    allow_rename=True
)

# 创建新关系
await rag.acreate_relation(
    source_entity="Elon Musk",
    target_entity="Tesla",
    relation_data={
        "description": "Elon Musk is CEO of Tesla",
        "keywords": "CEO, founder"
    }
)

# 编辑关系
await rag.aedit_relation(
    "Elon Musk",
    "Tesla",
    updated_data={"description": "新的关系描述"}
)
```

#### **知识图谱导出**
```python
# 获取知识图谱子图
kg = await rag.get_knowledge_graph(
    node_label="Elon Musk",
    max_depth=3,          # 关系深度
    max_nodes=100         # 最大节点数
)

# 导出为各种格式
await rag.aexport_data(
    output_path="kg_export.csv",
    file_format="csv"     # 支持: csv, json, md, xlsx
)
```

---

## 3. 关键代码文件和类的角色

### 3.1 文件层级关系

```
lightrag/
├── lightrag.py              ← 主类 LightRAG（150+ KB，所有 mixin 的聚合）
├── pipeline.py              ← _PipelineMixin：文档插入管道
├── operate.py               ← 核心查询和提取操作（2000+ 行）
├── base.py                  ← 抽象基类和数据结构
├── llm_roles.py             ← LLM 角色配置管理
├── storage_migrations.py    ← 数据迁移
├── addon_params.py          ← 可观察参数系统
└── kg/                      ← 存储实现
    ├── factory.py           ← 存储工厂
    ├── networkx_impl.py     ← 本地图存储
    ├── neo4j_impl.py        ← Neo4j 支持
    └── ...其他后端...
```

### 3.2 核心类的职责

#### **LightRAG 类（lightrag.py）- 业务协调者**

```python
class LightRAG(_RoleLLMMixin, _StorageMigrationMixin, _PipelineMixin):
    """
    通过 mixin 组织关注点：
    - _RoleLLMMixin: LLM 角色管理
    - _StorageMigrationMixin: 数据迁移
    - _PipelineMixin: 文档处理管道
    """
    
    # 核心属性
    chunk_entity_relation_graph: BaseGraphStorage  # 知识图谱
    entities_vdb: BaseVectorStorage                # 实体向量库
    relationships_vdb: BaseVectorStorage           # 关系向量库
    chunks_vdb: BaseVectorStorage                  # 文本块向量库
    text_chunks: BaseKVStorage                     # 文本块存储
    llm_response_cache: BaseKVStorage              # LLM 缓存
    
    # 核心方法
    async def ainsert(...)                  # 插入文档
    async def aquery(...)                   # 查询
    async def ainsert_custom_kg(...)        # 自定义插入知识图谱
    async def initialize_storages(...)      # 初始化存储（必须！）
    async def finalize_storages(...)        # 清理存储
```

#### **_PipelineMixin（pipeline.py）- 文档处理管道**

```python
class _PipelineMixin:
    """负责完整的文档摄取管道"""
    
    async def apipeline_enqueue_documents(...)     # 入队文档
    async def apipeline_process_enqueue_documents(...) # 处理入队文档
    async def apipeline_process_error_documents(...) # 处理错误文档
    
    # 多个解析器支持
    parse_native()     # 原生格式
    parse_mineru()     # MinERU 解析器
    parse_docling()    # Docling 解析器
```

#### **operate.py - 查询和提取的心脏**

```python
# 四大核心函数

1. extract_entities()           # 从文本块提取实体和关系
   - 调用 LLM 进行实体识别
   - 支持 JSON 和分隔符两种格式
   - 包含 Gleaning（再次提取）阶段

2. kg_query()                   # 知识图谱查询入口
   - 调用 _perform_kg_search() 进行搜索
   - 使用 _build_query_context() 构建上下文
   - 返回统一的 QueryResult 对象

3. naive_query()                # 简单向量搜索
   - 直接在向量库中搜索
   - 不使用知识图谱

4. rebuild_knowledge_from_chunks() # 从缓存重建知识图谱
   - 用于文档删除后的重建
   - 使用缓存的 LLM 提取结果
   - 支持并行处理
```

---

## 4. 不同查询模式的实现

### 4.1 查询模式概览

```python
# QueryParam 中的 mode 参数（lightrag/base.py）
mode: Literal["local", "global", "hybrid", "naive", "mix", "bypass"]
```

### 4.2 各模式详解

#### **1. Local 模式 - 局部上下文检索**

```python
# 实现位置：lightrag/operate.py - _perform_kg_search()

if query_param.mode == "local" and len(ll_keywords) > 0:
    local_entities, local_relations = await _get_node_data(
        ll_keywords,              # 低级关键词（具体概念）
        knowledge_graph_inst,
        entities_vdb,
        query_param,
        query_embedding=ll_embedding,
    )

# 核心逻辑：
# 1. 使用低级关键词（ll_keywords）查询实体向量库
# 2. 获取相关实体及其连接的关系
# 3. 从这些关系中找到相关的文本块
# 适用场景：需要具体事实的查询
```

**使用示例**：
```python
result = await rag.aquery(
    "Tesla 的 CEO 是谁？",
    param=QueryParam(mode="local", top_k=10)
)
# 流程：
# 1. 提取低级关键词：["Tesla", "CEO"]
# 2. 在实体库中搜索这些关键词
# 3. 找到 "Elon Musk" 和 "Tesla" 实体
# 4. 检索它们之间的关系
# 5. 收集相关文本块
```

#### **2. Global 模式 - 全局知识检索**

```python
# 实现位置：lightrag/operate.py - _perform_kg_search()

elif query_param.mode == "global" and len(hl_keywords) > 0:
    global_relations, global_entities = await _get_edge_data(
        hl_keywords,              # 高级关键词（抽象概念）
        knowledge_graph_inst,
        relationships_vdb,
        query_param,
        query_embedding=hl_embedding,
    )

# 核心逻辑：
# 1. 使用高级关键词（hl_keywords）查询关系向量库
# 2. 在社区或总结级别聚合信息
# 3. 获取这些关系连接的所有实体
# 适用场景：需要高层概述的查询
```

**使用示例**：
```python
result = await rag.aquery(
    "人工智能对社会的影响是什么？",
    param=QueryParam(mode="global", top_k=20)
)
# 流程：
# 1. 提取高级关键词：["AI", "society", "impact"]
# 2. 在关系库中搜索这些高级概念的关系
# 3. 聚合相关的所有实体和关系
# 4. 生成全局总结
```

#### **3. Hybrid 模式 - 混合检索**

```python
# 实现位置：lightrag/operate.py - _perform_kg_search()

else:  # hybrid or mix mode
    # 同时执行 local 和 global 搜索
    if len(ll_keywords) > 0:
        local_entities, local_relations = await _get_node_data(...)
    
    if len(hl_keywords) > 0:
        global_relations, global_entities = await _get_edge_data(...)
    
    # Round-robin 合并：交替添加 local 和 global 结果
    # 这样可以在一个查询中既有具体细节又有高层见解

# 核心逻辑：
# 1. 并行执行 local 和 global 搜索
# 2. 使用 Round-robin 策略合并结果
# 3. 既保留具体实体，又包含高层关系
# 适用场景：需要全面理解的复杂查询
```

**使用示例**：
```python
result = await rag.aquery(
    "Elon Musk 和他的公司对科技发展的贡献",
    param=QueryParam(mode="hybrid", top_k=30)
)
# 流程：
# 1. Local：找到 Elon Musk 的具体信息
# 2. Global：找到他与科技发展的高层关系
# 3. 合并：既有 CEO 的具体事实，又有产业影响的全景
```

#### **4. Naive 模式 - 简单向量搜索**

```python
# 实现位置：lightrag/operate.py - _get_vector_context()

async def _get_vector_context(
    query: str,
    chunks_vdb: BaseVectorStorage,
    query_param: QueryParam,
    query_embedding: list[float] = None,
) -> list[dict]:
    results = await chunks_vdb.query(
        query,
        top_k=query_param.chunk_top_k or query_param.top_k,
        query_embedding=query_embedding
    )
    # 返回原始向量搜索结果，不经过知识图谱

# 核心逻辑：
# 1. 跳过知识图谱
# 2. 直接在文本块向量库中做最近邻搜索
# 3. 最快但可能缺乏结构化推理
# 适用场景：快速查询或向量库已经很好的情况
```

**使用示例**：
```python
result = await rag.aquery(
    "什么是深度学习？",
    param=QueryParam(mode="naive", chunk_top_k=10)
)
# 流程：
# 直接在文本块向量库中搜索，返回最相似的 10 个块
```

#### **5. Mix 模式 - 综合检索（推荐）**

```python
# 实现位置：lightrag/operate.py - _perform_kg_search()

if query_param.mode == "mix" and chunks_vdb:
    # 同时使用：local + global + naive 向量搜索
    
    # 1. Local 搜索
    local_entities, local_relations = await _get_node_data(...)
    
    # 2. Global 搜索
    global_relations, global_entities = await _get_edge_data(...)
    
    # 3. Naive 向量搜索
    vector_chunks = await _get_vector_context(
        query, chunks_vdb, query_param, query_embedding
    )
    
    # 4. Round-robin 合并三种结果
    # 5. 如果启用 reranker，进行重新排序

# 核心逻辑：
# 1. 结合知识图谱的结构化推理
# 2. 结合向量搜索的语义匹配
# 3. 获得最完整的上下文
# 适用场景：大多数生产环境
```

**使用示例**：
```python
result = await rag.aquery(
    "Tesla 如何推动电动汽车革命？",
    param=QueryParam(
        mode="mix",
        top_k=60,
        chunk_top_k=20,
        enable_rerank=True,
        max_total_tokens=30000
    )
)
# 流程：
# 1. Local：获取 Tesla 和电动汽车的具体信息
# 2. Global：获取汽车行业革命的宏观视角
# 3. Vector：通过语义搜索找到相关文本块
# 4. Rerank：使用跨编码器对所有块重新排序
# 5. LLM：生成综合答案
```

### 4.3 查询流程对比

```
┌─────────────────────────────────────────────────────────────┐
│           Query Mode Comparison                            │
├──────────┬──────────────┬─────────────┬──────────────────────┤
│   Mode   │  Entity Src  │  Relation   │   Use Cases          │
│          │              │   Src       │                      │
├──────────┼──────────────┼─────────────┼──────────────────────┤
│ local    │ LL-keywords  │ Neighbor    │ Specific facts       │
│ global   │ HL keywords  │ HL-keywords │ High-level summary   │
│ hybrid   │ Both         │ Both        │ Comprehensive        │
│ naive    │ Vector only  │ None        │ Fast, semantic       │
│ mix      │ Both + Vec   │ Both + Vec  │ Best overall (rec.)  │
└──────────┴──────────────┴─────────────┴──────────────────────┘

Key Keywords:
- LL (Low-Level): 具体概念 (Tesla, CEO)
- HL (High-Level): 抽象概念 (innovation, impact)
```

---

## 5. 完整工作流示例

### 5.1 端到端示例

```python
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed

async def main():
    # 初始化 RAG 系统
    rag = LightRAG(
        working_dir="./rag_storage",
        workspace="my_project",
        llm_model_func=gpt_4o_mini_complete,
        embedding_func=openai_embed
    )
    await rag.initialize_storages()
    
    # 第 1 步：插入文档
    documents = [
        """
        Elon Musk 是 Tesla、SpaceX 和 Neuralink 的创始人。
        他致力于推动可持续能源和太空探索。
        Tesla 已成为全球最大的电动汽车制造商。
        """,
        """
        电动汽车革命改变了汽车工业。
        特斯拉的成功激励了其他传统汽车制造商进入电动汽车市场。
        可持续能源对应对气候变化至关重要。
        """
    ]
    
    print("插入文档...")
    await rag.ainsert(documents, file_paths=["doc1.txt", "doc2.txt"])
    
    # 第 2 步：执行不同类型的查询
    
    # 查询 1：Local 模式 - 具体事实
    print("\n=== Local 模式 ===")
    result = await rag.aquery(
        "Elon Musk 创办了哪些公司？",
        param=QueryParam(mode="local", top_k=10)
    )
    print(f"答案：{result.content}")
    print(f"实体：{result.raw_data['data'].get('entities', [])[:2]}")
    
    # 查询 2：Global 模式 - 高层概述
    print("\n=== Global 模式 ===")
    result = await rag.aquery(
        "电动汽车行业的未来趋势是什么？",
        param=QueryParam(mode="global", top_k=20)
    )
    print(f"答案：{result.content}")
    
    # 查询 3：Hybrid 模式 - 综合视角
    print("\n=== Hybrid 模式 ===")
    result = await rag.aquery(
        "Elon Musk 如何推动电动汽车革命？",
        param=QueryParam(mode="hybrid", top_k=30)
    )
    print(f"答案：{result.content}")
    
    # 查询 4：Mix 模式 - 最完整
    print("\n=== Mix 模式（推荐） ===")
    result = await rag.aquery(
        "可持续能源和 Tesla 的关系是什么？",
        param=QueryParam(
            mode="mix",
            top_k=60,
            chunk_top_k=20,
            enable_rerank=True,
            max_total_tokens=30000,
            user_prompt="请用三个段落详细解释",
            stream=False
        )
    )
    print(f"答案：{result.content}")
    print(f"原始数据：")
    print(f"  - 实体数量: {len(result.raw_data['data'].get('entities', []))}")
    print(f"  - 关系数量: {len(result.raw_data['data'].get('relationships', []))}")
    print(f"  - 文本块数量: {len(result.raw_data['data'].get('chunks', []))}")
    
    # 第 3 步：获取实体信息
    print("\n=== 实体信息 ===")
    entity_info = await rag.get_entity_info("Elon Musk")
    print(f"Elon Musk 的类型：{entity_info.get('graph_data', {}).get('entity_type')}")
    print(f"描述：{entity_info.get('graph_data', {}).get('description')}")
    
    # 第 4 步：导出知识图谱
    print("\n=== 导出知识图谱 ===")
    await rag.aexport_data(
        output_path="kg_export.csv",
        file_format="csv"
    )
    print("知识图谱已导出到 kg_export.csv")
    
    # 清理
    await rag.finalize_storages()

# 运行
asyncio.run(main())
```

### 5.2 内部流程图

```
用户查询
   ↓
["local", "global", "hybrid", "naive", "mix"]
   ↓
┌─────────────────────────────────────────┐
│  kg_query() 主函数 (operate.py)        │
└─────────────────────────────────────────┘
   ↓
get_keywords_from_query()
   ↓ 获取高级/低级关键词
   ↓
_perform_kg_search()
   ├→ _get_node_data()         [Local]
   ├→ _get_edge_data()         [Global]
   └→ _get_vector_context()    [Naive/Mix]
   ↓ 获取实体、关系、文本块
   ↓
_apply_token_truncation()
   ↓ 令牌预算控制
   ↓
_merge_all_chunks()
   ├→ _find_related_text_unit_from_entities()
   ├→ _find_related_text_unit_from_relations()
   └→ _get_vector_context()
   ↓ 去重合并
   ↓
_build_context_str()
   ├→ process_chunks_unified()    [可选重新排序]
   └→ convert_to_user_format()
   ↓ 生成 LLM 上下文
   ↓
调用 LLM 模型
   ↓ 生成最终答案
   ↓
返回 QueryResult
```

---

## 6. 存储后端配置

```python
# 支持的存储后端

KV_STORAGE:
  - JsonKVStorage        # JSON 文件（默认，本地）
  - PGKVStorage          # PostgreSQL
  - RedisKVStorage       # Redis
  - MongoDBKVStorage     # MongoDB

VECTOR_STORAGE:
  - NanoVectorDB         # 本地轻量（默认）
  - QdrantVectorStorage  # Qdrant
  - MilvusVectorStorage  # Milvus
  - FaissVectorStorage   # Faiss
  - OpenSearchVector     # OpenSearch

GRAPH_STORAGE:
  - NetworkXStorage      # 本地图（默认）
  - Neo4jStorage         # Neo4j
  - PostgreSQL           # 关系数据库
  - MemgraphStorage      # Memgraph
  - MongoDBGraphStorage  # MongoDB

# 配置示例
rag = LightRAG(
    kv_storage="PGKVStorage",
    vector_storage="MilvusVectorStorage",
    graph_storage="Neo4jStorage",
    kv_storage_cls_kwargs={
        "host": "localhost",
        "port": 5432,
        "dbname": "lightrag"
    },
    vector_db_storage_cls_kwargs={
        "host": "localhost",
        "port": 19530,
        "db_name": "lightrag"
    }
)
```

---

## 总结

| 概念 | 关键文件 | 主要函数 | 用途 |
|------|--------|--------|------|
| 实体提取 | operate.py | extract_entities() | 从文本提取结构化实体 |
| 关系提取 | operate.py | extract_entities() | 从文本提取实体间关系 |
| Local 查询 | operate.py | _get_node_data() | 具体事实检索 |
| Global 查询 | operate.py | _get_edge_data() | 高层知识检索 |
| 混合查询 | operate.py | kg_query() | 综合检索 |
| 文档管道 | pipeline.py | _PipelineMixin | 完整的文档处理 |
| 知识管理 | lightrag.py | LightRAG 类 | 统一的 API 界面 |
