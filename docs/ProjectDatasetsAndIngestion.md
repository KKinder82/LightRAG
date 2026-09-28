# 项目数据集与文件入库

## 使用方式

- 页面顶部“项目数据集”可新建和切换项目。原有数据保留在“默认数据集”，不会自动迁移。
- 每个项目有独立的文档、输入目录、向量、知识图谱、缓存及文件夹。相同文件名可以出现在不同项目。项目沿用服务现有认证机制；项目分类不是用户权限管理。
- 同名文件再次上传时自动生成带随机版本标记的新文件名；原文件和原记录保留。即使内容相同，也会建立独立文档和分块，可分别删除。文件名中的解析器提示仍有效。
- 上传时可勾选“快速索引”，只建立文本向量、跳过实体关系抽取。此模式应使用 `naive` 检索；普通上传仍建立完整知识图谱。实际耗时取决于文件大小、解析引擎、模型和队列负载。
- 有解析任务时仍可提交删除，接口返回 `deletion_queued`。删除请求持久保存，在入库释放锁后自动执行；不会在图谱写入过程中强行清理数据。服务重启会恢复待执行请求。此功能不代表立即中断正在解析的文档。

## 图片和旧版 Office 文件

新增 `.doc`、`.ppt`、`.xls`，以及 `.png`、`.jpg`、`.jpeg`、`.bmp`、`.tif`、`.tiff`、`.webp`。

旧版 Office 使用 LibreOffice 转成现代格式后提取；每次转换使用独立临时用户目录。图片使用 Tesseract 提取可识别文字，不做图片场景理解。单次转换/OCR 最多执行 120 秒，异常会记录为可查询的失败文档。

Ubuntu/Debian 主机依赖：

```bash
sudo apt-get install libreoffice-writer libreoffice-impress libreoffice-calc \
  tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng fonts-noto-cjk
```

配置 `LIGHTRAG_OCR_LANG=chi_sim+eng`，也可指定已安装的其他语言包。Dockerfile 与 Dockerfile.lite 已加入依赖，但需要重新构建镜像才会生效。

## API

```text
POST /projects                 {"name": "项目A"}
GET  /projects
```

新建接口返回不可变项目 `id`。项目相关请求附加 `X-LightRAG-Project: <id>`，适用于 `/documents`、`/query`、`/graph`、`/graphs` 和 Ollama `/api` 路径（含其子路径）。不带此头使用默认数据集；未知 ID 返回 404，不会退回默认数据集。

```text
POST /documents/upload         multipart: file, folder_id（可选）, fast_index（可选，默认 false）
DELETE /documents/delete_document  {"doc_ids": ["doc-..."]}
GET /documents/deletion_jobs    查看 queued / completed / failed 和未删成功的文档 ID
```

项目目录和删除队列使用工作目录中的 JSON 控制数据；应与知识库数据一并备份。支持同一服务的共享存储/多 worker 机制，不提供跨主机控制数据同步。若后端配置强制把所有实例绑定到同一 workspace，项目初始化会拒绝该配置，避免混用检索数据。

## 验证范围

自动化用例使用真实本地文件存储和模拟模型，覆盖重复上传、并发同名上传、快速索引、删除排队恢复、删除版本独立性、项目文档/图谱/查询隔离。另使用本机 LibreOffice/Tesseract 实测旧版 Office 和五类图片格式。真实模型吞吐、远程服务器和新 Docker 镜像的运行效果需部署环境验收。

本次本地验收还启动了仅监听回环地址的测试 API，上传真实 `.doc/.ppt/.xls/.png/.jpg/.tiff/.bmp/.webp` 文件并查询各自 `track_status`，八类文件均到达 `processed`。此测试使用模拟 LLM/embedding，不代表真实模型服务的性能验收；测试服务已关闭。前端构建、单元测试和定向 ESLint 检查通过；浏览器连接不可用，未完成浏览器交互验收。
