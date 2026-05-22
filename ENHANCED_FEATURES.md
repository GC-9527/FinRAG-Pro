# RAG-cy 增强功能集成总结

## 概述

已将初会RAG助手的查询改写和增强重排序功能成功集成到RAG-cy项目中，用于企业年报问答场景。

## 新增功能

### 1. 查询改写模块 (`src/query_rewriter.py`)

#### 主要类

- **IntentClassifier**: 意图分类器
  - 支持多种查询类型：definition、calculation、comparison、trend、reason、procedure、risk、financial、business、governance
  - 基于关键词匹配和权重计算置信度

- **QueryExpander**: 查询扩展器
  - 使用LLM生成查询变体
  - 支持相关查询生成

- **SmartQueryRewriter**: 智能查询改写器
  - 整合意图分类和LLM改写
  - `auto_rewrite()` 方法返回改写结果、类型和置信度

#### 使用示例

```python
from src.query_rewriter import SmartQueryRewriter, rewrite_query

# 方式1: 使用类实例
rewriter = SmartQueryRewriter()
result = rewriter.auto_rewrite("华为的营收多少")
print(result['rewritten_query'])  # 改写后的查询
print(result['query_type'])       # 查询类型
print(result['confidence'])        # 置信度

# 方式2: 使用便捷函数
result = rewrite_query("分析中兴的风险")
```

### 2. 增强重排序模块 (`src/enhanced_reranker.py`)

#### 主要类

- **TongyiReranker**: 通义千问rerank模型排序器
  - 使用通义千问qwen3-rerank模型
  - 适合通用场景

- **RuleBasedReranker**: 基于规则的重排序器
  - 语义相似度评分
  - 关键词匹配评分
  - 位置评分
  - 内容质量评分
  - 针对企业年报场景优化

- **HybridReranker**: 混合排序器
  - 优先使用通义rerank
  - 失败时fallback到规则排序

- **BusinessReportReranker**: 企业年报专用排序器
  - 集成HybridReranker
  - 应用查询类型特殊规则
  - 财务指标特殊处理

#### 使用示例

```python
from src.enhanced_reranker import BusinessReportReranker, rerank_documents

# 模拟检索结果
results = [
    {'text': '2024年营收为1000亿元', 'page': 5, 'distance': 0.3},
    {'text': '公司面临的风险包括...', 'page': 15, 'distance': 0.4},
]

# 方式1: 使用类实例
reranker = BusinessReportReranker()
reranked = reranker.rerank("营收情况", results, top_k=3)

# 方式2: 使用便捷函数
reranked = rerank_documents("营收分析", results, top_k=3)
```

### 3. Pipeline集成

#### 修改的文件

1. **`src/questions_processing.py`**
   - 添加 `use_query_rewrite` 和 `use_enhanced_reranker` 参数
   - 在 `get_answer_for_company` 方法中集成查询改写和增强重排序
   - 记录查询改写信息到答案中

2. **`src/pipeline.py`**
   - 在 `RunConfig` 中添加新配置参数
   - 更新 `process_questions` 和 `answer_single_question` 方法
   - 添加 `enhanced_config` 配置

#### 配置选项

```python
from src.pipeline import RunConfig, enhanced_config

# 方式1: 使用预定义配置
pipeline = Pipeline(root_path, run_config=enhanced_config)

# 方式2: 自定义配置
config = RunConfig(
    use_query_rewrite=True,
    use_enhanced_reranker=True,
    # ... 其他参数
)
```

## 功能特点

### 查询改写

1. **自动意图识别**: 识别查询是计算、比较、定义、趋势、风险等类型
2. **智能改写**: 使用LLM将查询改写为更适合检索的形式
3. **查询扩展**: 可选地生成查询变体，提高检索覆盖率
4. **置信度评分**: 返回改写的置信度，帮助评估改写质量

### 增强重排序

1. **多维度评分**: 结合语义、关键词、位置、内容质量等多个维度
2. **企业年报优化**: 针对年报场景的特殊处理
3. **财务指标识别**: 自动识别财务相关关键词并提高权重
4. **查询类型适配**: 根据查询类型应用不同的排序规则

## 使用流程

```
用户查询 → 查询改写 → 向量检索 → 增强重排序 → LLM生成答案
           ↓                          ↓
      意图识别                   相关性排序
      查询优化                   内容质量评估
```

## 性能优化

1. **计时统计**: 所有关键步骤都包含计时统计，便于性能分析
2. **异常处理**: 完善的异常处理机制，确保部分功能失败不影响整体流程
3. **可配置性**: 所有功能都可以通过参数控制是否启用

## 测试

运行测试脚本验证功能：

```bash
cd RAG-cy
python test_enhanced_rag.py
```

运行示例代码：

```bash
python example_usage.py
```

## 注意事项

1. **API依赖**: 查询改写功能需要调用LLM API，确保DASHSCOPE_API_KEY配置正确
2. **数据准备**: 完整Pipeline使用需要准备好向量数据库和文档目录
3. **性能考量**: 查询改写会增加一定的处理时间，可根据需求选择性启用

## 未来优化方向

1. 支持更多查询类型和行业场景
2. 优化查询改写提示词，提高改写质量
3. 集成更多重排序模型
4. 添加缓存机制，避免重复改写
5. 优化性能，减少延迟

## 参考资料

- 初会RAG助手: [初会RAG助手项目路径]
- RAG-cy原项目: [RAG-cy项目路径]
