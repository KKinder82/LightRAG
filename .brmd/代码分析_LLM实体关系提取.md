# LightRAG 代码分析报告：LLM 实体与关系提取流程

> 分析时间: 2026-07-23
> 项目根目录: /home/kk/github/LightRAG

## 一、整体架构概览

LightRAG 由多个 mixin 组合而成：

```text
LightRAG → _RoleLLMMixin → _StorageMigrationMixin → _PipelineMixin → object
```

核心模块及对应文件：

| 功能 | 文件 |
| --- | --- |
| 主类定义(lightrag.py) | `lightrag/lightrag.py` |
| LLM角色路由 | `lightrag/llm_roles.py` |
| 文档处理流水线 | `lightrag/pipeline.py` |
| 核心操作(实体提取/查询) | `lightrag/operate.py` |
| Prompt模板 | `lightrag/prompt.py` |
| LLM Provider绑定 | `lightrag/llm/` |
| 存储后端 | `lightrag/kg/` |
| 工具函数 | `lightrag/utils.py` |
| 底座抽象类 | `lightrag/base.py` |

---

## 二、LLM 角色注册表 (ROLES)

`lightrag/llm_roles.py` 定义了 4 个 LLM 角色：

| 角色名 | env 前缀 | 用途 | 默认值 |
|--------|----------|------|--------|
| `extract` | `EXTRACT_*` | 实体/关系提取 | 继承 base `llm_model_func` |
| `keyword` | `KEYWORD_*` | 关键词提取 | 继承 base |
| `query` | `QUERY_*` | 查询回答 | 继承 base |
| `vlm` | `VLM_*` | 视觉语言模型 | 继承 base |

每个角色可独立配置：`EXTRACT_LLM_BINDING` / `EXTRACT_LLM_MODEL` / `EXTRACT_MAX_ASYNC_LLM` / `EXTRACT_LLM_TIMEOUT`。

角色状态管理：

- `_role_llm_states`: `dict[str, _RoleLLMState]` — 存储每个角色的 raw_func、wrapped 函数、kwargs、metadata
- `role_llm_funcs` (property): 返回 `{角色名 → wrapped函数}` 的只读映射
- 每个角色函数的 wrapped 版本包含: 优先级队列 (`priority_limit_async_func_call`) + LLM timeout + model_kwargs

## 三、实体/关系提取核心流程

### 入口调用链

```text
用户插入文档(ainsert)
  → pipeline.py: apipeline_process_enqueue_documents()
    → 对每个文档:
      1. 解析文档 → chunks
      2. 保存 chunks → chunks_vdb + text_chunks (并发)
      3. _process_extract_entities(chunks)  ← 实体关系提取
      4. merge_nodes_and_edges()              ← 合并到存储
```

### `_process_extract_entities()` — lightrag.py:1749

```python
async def _process_extract_entities(self, chunk, pipeline_status, pipeline_status_lock):
    chunk_results = await extract_entities(
        chunk,
        global_config=self._build_global_config(),
        ...
    )
```

### `extract_entities()` — operate.py:3221

这是核心提取函数，流程如下：

#### 第一步：获取 LLM 函数和配置

```python
use_llm_func = global_config["role_llm_funcs"]["extract"]  # extract 角色的 LLM
```

#### 第二步：构建 Prompt（两种模式）

**文本模式** (默认):
- 实体: `entity<|#|>名称<|#|>类型<|#|>描述`
- 关系: `relation<|#|>源实体<|#|>目标实体<|#|>关键词<|#|>描述`
- 结束标记: `<|COMPLETE|>`

**JSON 模式** (`entity_extraction_use_json=True`):
- 输出 `{"entities": [...], "relationships": [...]}`
- 支持 LLM 的 JSON structured output

#### 第三步：首次 LLM 调用

```python
final_result, timestamp = await use_llm_func_with_cache(
    entity_extraction_user_prompt,
    use_llm_func,                     # 实际调 LLM
    system_prompt=...,
    llm_response_cache=...,           # 缓存检查
    cache_type="extract",
    response_format=({"type": "json_object"} if json模式 else None),
)
```

#### 第四步：Gleaning（二次提取）

当 `entity_extract_max_gleaning > 0` 时，用对话历史追加一次 LLM 调用：
- 补提取首次遗漏的实体/关系
- 对比描述长度，保留更优版本
- 如果 token 数超过 `MAX_EXTRACT_INPUT_TOKENS` 则跳过

#### 第五步：多模态实体注入

对于 `drawing`/`table`/`equation` 类型的 sidecar chunk，自动创建关联实体（不经过 LLM）。

---

## 四、LLM 调用链路

```text
use_llm_func_with_cache (utils.py:2509)
  ├─ 计算 cache key (prompt + system + history + response_format + llm_identity)
  ├─ handle_cache() → 检查 llm_response_cache (kv存储)
  │   ├─ 命中 → 直接返回缓存结果
  │   └─ 未命中 → 继续
  └─ use_llm_func() → role_llm_funcs["extract"]
      └─ priority_limit_async_func_call(max_async)
          └─ raw_func(hashing_kv, **model_kwargs)
              └─ 具体的 LLM Provider (openai/ollama/gemini/...)
```

并发控制：
- `llm_model_max_async` (默认 4) — 控制同时处理的 chunk 数
- `asyncio.Semaphore(chunk_max_async)` 控制并发

---

## 五、Prompt 模板一览

定义在 `lightrag/prompt.py`：

| Prompt Key | 用途 |
| --- | --- |
| `entity_extraction_system_prompt` | 系统角色定义+实体类型指南+few-shot示例 |
| `entity_extraction_user_prompt` | 待提取文本输入 |
| `entity_continue_extraction_user_prompt` | Gleaning 继续提取提示 |
| `entity_extraction_json_system_prompt` | JSON 模式的系统提示 |
| `entity_extraction_json_user_prompt` | JSON 模式的用户提示 |
| `entity_extraction_json_examples` | JSON 模式示例 |
| `default_entity_types_guidance` | 11 种默认实体类型 |

## 六、提取结果解析

### 文本模式 — `_process_extraction_result()` (operate.py:1186)

- 按 `\n` 分行 → 按 `{tuple_delimiter}` 分割字段
- 前缀 `entity` → 实体，`relation` → 关系
- 字段异常处理：长度不足、类型包含非法字符、描述为空等

### JSON 模式 — `_process_json_extraction_result()` (operate.py:622)

- json_repair 容错解析
- 字段校验：name/type/description 非空，keywords 逗号分隔

---

## 七、结果合并

`merge_nodes_and_edges()` (operate.py:1317)

将每个 chunk 提取的结果：

1. 合并到图存储 (`chunk_entity_relation_graph`)
1. 合并到图存储 (`chunk_entity_relation_graph`)
1. 写入实体向量数据库 (`entities_vdb`)
1. 写入关系向量数据库 (`relationships_vdb`)
1. 写入完全实体/关系 KV 存储 (`full_entities`, `full_relations`)
1. 为实体生成摘要 (`_entity_relation_summary`)
1. 记录实体与 chunk 的对应关系 (`entity_chunks`, `relation_chunks`)

---

## 八、关键词提取

查询阶段也涉及 LLM 调用 (`extract_keywords_only`, operate.py:4012)：

- 提取 `high_level_keywords` 和 `low_level_keywords`
- 同样支持缓存

---

## 九、当前项目状态

- 分支: `main`
- 最近新增: SKILL.md 代码分析 skill (workspace级)
- 模块已完全从单文件拆分为 mixin 结构
- 存储后端支持: JSON, NetworkX, Neo4j, PostgreSQL, MongoDB, Milvus, Qdrant, Faiss, etc.
- LLM Provider: OpenAI, Ollama, Azure, Gemini, Bedrock, Anthropic, Zhipu, LMDeploy, etc.
