# 企业级nl2sql问数智能体

#### 介绍
python语言开发的企业级nl2sql，docker部署
基于大模型的企业级 NL2SQL 智能问答系统，让业务人员用自然语言直接查询数据库，告别"找不到表、看不懂字段、不会写SQL"的痛点。

###技术栈

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + AsyncIO |
| Agent编排 | LangGraph / LangChain |
| 向量数据库 | Qdrant |
| 全文检索 | Elasticsearch |
| 关系型数据库 | MySQL |
| Embedding | bge-large-zh-v1.5 |
| LLM接入 | LiteLLM（兼容 OpenAI / 通义千问 / DeepSeek 等） |
| 前端 | React + SSE 流式 |
| 部署 | Docker + Docker Compose |

## 📁 项目结构
data-agent/
├── app/
│ ├── agent/ # Agent 编排（LangGraph 图定义 + 节点）
│ ├── clients/ # 各类客户端封装（embedding、ES、Qdrant、MySQL）
│ ├── repositories/ # 数据访问层
│ ├── services/ # 业务服务层
│ ├── scripts/ # 工具脚本（元数据构建等）
│ ├── conf/ # 配置管理
│ └── main.py # 入口
├── docker/ # Docker 部署配置
├── frontend/ # 前端（React）
├── conf/ # 运行配置文件
└── pyproject.toml # 依赖管理（uv）

#### 软件架构
用户提问
│
▼
┌─────────────────────────────────────────────────────┐
│ 关键词提取 (extract_keywords) │
└──────────────────────┬──────────────────────────────┘
│
┌────────────┼────────────┐
▼ ▼ ▼
字段向量召回 指标向量召回 枚举值召回
(Qdrant) (Qdrant) (Elasticsearch)
│ │ │
└────────────┼────────────┘
▼
┌──────────────────┐
│ 结果融合 (RRF) │
└────────┬─────────┘
▼
┌──────────────────┐
│ 表/指标过滤剪枝 │
└────────┬─────────┘
▼
┌──────────────────┐
│ SQL 生成 (LLM) │
└────────┬─────────┘
▼
┌──────────────────┐
│ SQL 语法校验 │─── 失败 ──┐
└────────┬─────────┘ │
│ 成功 ▼
▼ ┌──────────────┐
┌──────────────────┐ │ SQL 纠错 │
│ SQL 执行 & 返回 │◄───┘ │
└──────────────────┘
## ✨ 核心特性

- **多阶段推理架构**：基于 LangGraph 构建12节点有向图工作流，重写 → 召回 → 过滤 → 生成 → 校验 → 纠错，全链路可控
- **混合多路召回**：Qdrant 向量检索 + Elasticsearch 倒排索引 + RRF 融合，字段召回 Top-5 命中率达 92%
- **Schema 动态剪枝**：通过 CoT 思维链动态筛选相关表和字段，Prompt 压缩 70%，SQL 生成准确率提升至 85%
- **SQL 自纠错闭环**：自动语法校验 + 智能纠错，端到端 SQL 可执行率达 92%
- **流式响应**：SSE 流式输出，打字机效果，体验流畅


#### 安装教程


## 🚀 快速开始

### 1. 启动基础设施

```bash
cd docker
docker compose up -d
会启动：MySQL（业务库+元数据库）、Qdrant、Elasticsearch、Embedding 服务
2. 安装依赖
uv sync
3. 构建元数据知识库
uv run python -m app.scripts.build_meta_knowledge --conf conf/meta_config.yaml
4. 启动后端服务
uv run python -m app.main
服务启动后访问 http://localhost:8000/docs 查看 API 文档。
5. 启动前端
cd frontend
npm install
npm run dev
📊 效果展示
![界面效果](docs/images/demo1.png)

💡 设计亮点
1.三路并行召回 + RRF 融合：字段语义走向量、精确值走 ES、业务指标单独建库，三路结果用倒数排名融合，兼顾语义理解和精确匹配
2.Schema 动态剪枝：不是把所有表结构全塞给 LLM，而是先推理筛选，既省 Token 又减少干扰
3.多阶段而非端到端：每一步都有明确的输入输出和校验，出错可定位可修复，比一次性生成 SQL 靠谱得多
4.元数据三层架构：结构化（MySQL）+ 向量化（Qdrant）+ 全文（ES），各司其职



#### 特技

1.  使用 Readme\_XXX.md 来支持不同的语言，例如 Readme\_en.md, Readme\_zh.md
2.  Gitee 官方博客 [blog.gitee.com](https://blog.gitee.com)
3.  你可以 [https://gitee.com/explore](https://gitee.com/explore) 这个地址来了解 Gitee 上的优秀开源项目
4.  [GVP](https://gitee.com/gvp) 全称是 Gitee 最有价值开源项目，是综合评定出的优秀开源项目
5.  Gitee 官方提供的使用手册 [https://gitee.com/help](https://gitee.com/help)
6.  Gitee 封面人物是一档用来展示 Gitee 会员风采的栏目 [https://gitee.com/gitee-stars/](https://gitee.com/gitee-stars/)
