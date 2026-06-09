# 概念
## 基本概念：

### namespace : 存储命名空间，通常用于区分不同的存储区域或上下文。
  常用的命名空间示例包括：

### doc_status: 用于存储文档状态信息的命名空间。
    KV_STORE_FULL_DOCS = "full_docs"
    KV_STORE_TEXT_CHUNKS = "text_chunks"
    KV_STORE_LLM_RESPONSE_CACHE = "llm_response_cache"
    KV_STORE_FULL_ENTITIES = "full_entities"
    KV_STORE_FULL_RELATIONS = "full_relations"
    KV_STORE_ENTITY_CHUNKS = "entity_chunks"
    KV_STORE_RELATION_CHUNKS = "relation_chunks"

    VECTOR_STORE_ENTITIES = "entities"
    VECTOR_STORE_RELATIONSHIPS = "relationships"
    VECTOR_STORE_CHUNKS = "chunks"

    GRAPH_STORE_CHUNK_ENTITY_RELATION = "chunk_entity_relation"

    DOC_STATUS = "doc_status"

### workspace : 工作空间，表示一个特定的工作环境或项目范围。



## 全文对象 
file -> document(Text) -> chunk

### full_docs: 完整文档数据列表，每个元素包含文档的所有相关信息（如内容、元数据、处理选项等）。 (所以文档, 包括,有处理的,没有处理的. )
  - id -> 文档的唯一标识符。
  - 每一个文件一个文档对象，主要包含文档内容和相关信息。

### doc_status: 文档状态列表，每个元素包含文档的状态信息（如处理状态、错误信息等），但不包含文档内容。
  - id -> status_doc
  - 每一个文件一个状态对象. 

### pipeline_status: 管道状态，表示当前数据处理管道的状态信息。
   是一个字典，包含以下键值对：


## 处理重复文档的逻辑