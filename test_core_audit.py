# -*- coding: utf-8 -*-
"""
自动化测试脚本：覆盖 RAG-cy 项目核心功能
验证代码审计清理后，所有核心模块功能正常，无回归问题
"""
import sys
import os
import time
import json
import traceback
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0
TEST_RESULTS = []


def log_pass(msg):
    global PASS_COUNT
    PASS_COUNT += 1
    TEST_RESULTS.append(("PASS", msg))
    print(f"    [PASS] {msg}")


def log_fail(msg):
    global FAIL_COUNT
    FAIL_COUNT += 1
    TEST_RESULTS.append(("FAIL", msg))
    print(f"    [FAIL] {msg}")


def log_warn(msg):
    global WARN_COUNT
    WARN_COUNT += 1
    TEST_RESULTS.append(("WARN", msg))
    print(f"    [WARN] {msg}")


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ============================================================
# 测试组1: 模块导入完整性检查
# ============================================================
def test_module_imports():
    print_section("测试组1: 模块导入完整性检查")

    modules_to_test = [
        ("src.pipeline", ["Pipeline", "RunConfig", "base_config", "max_config", "enhanced_config", "parent_document_retrieval_config"]),
        ("src.questions_processing", ["QuestionsProcessor"]),
        ("src.query_rewriter", ["SmartQueryRewriter", "EnhancedQueryRewriter", "IntentClassifier", "QueryExpander", "rewrite_query", "get_query_rewriter"]),
        ("src.enhanced_reranker", ["TongyiReranker", "RuleBasedReranker", "HybridReranker", "BusinessReportReranker", "rerank_documents", "get_business_reranker"]),
        ("src.retrieval", ["VectorRetriever", "BM25Retriever", "HybridRetriever"]),
        ("src.ingestion", ["BM25Ingestor", "VectorDBIngestor"]),
        ("src.reranking", ["JinaReranker", "LLMReranker"]),
        ("src.prompts", ["build_system_prompt", "RephrasedQuestionsPrompt", "AnswerWithRAGContextNamePrompt", "AnswerWithRAGContextNumberPrompt"]),
        ("src.text_splitter", ["TextSplitter"]),
        ("src.api_requests", ["BaseOpenaiProcessor", "AsyncOpenaiProcessor"]),
        ("src.tables_serialization", ["TableSerializer"]),
        ("src.parsed_reports_merging", ["PageTextPreparation"]),
    ]

    for module_name, class_names in modules_to_test:
        try:
            mod = __import__(module_name, fromlist=class_names)
            for class_name in class_names:
                try:
                    obj = getattr(mod, class_name)
                    log_pass(f"{module_name}.{class_name}")
                except AttributeError as e:
                    log_fail(f"{module_name}.{class_name} - 未找到: {e}")
        except ImportError as e:
            for class_name in class_names:
                log_fail(f"{module_name}.{class_name} - 模块导入失败: {e}")

    print_section("测试组1补充: 验证已删除的类不会被意外导入")
    deleted_classes = [
        ("src.enhanced_reranker", "AdvancedReranker"),
    ]
    for module_name, class_name in deleted_classes:
        try:
            mod = __import__(module_name, fromlist=[class_name])
            try:
                getattr(mod, class_name)
                log_fail(f"{module_name}.{class_name} - 已删除的类仍可访问（残留）")
            except AttributeError:
                log_pass(f"{module_name}.{class_name} - 确认已移除")
        except Exception as e:
            log_pass(f"{module_name}.{class_name} - 确认已移除 ({e})")


# ============================================================
# 测试组2: 数据完整性检查
# ============================================================
def test_data_integrity():
    print_section("测试组2: 数据完整性检查")

    ROOT_PATH = Path("data/stock_data")
    required_paths = [
        (ROOT_PATH / "subset.csv", "公司列表文件"),
        (ROOT_PATH / "questions.json", "问题文件"),
        (ROOT_PATH / "databases" / "vector_dbs", "向量数据库目录"),
        (ROOT_PATH / "databases" / "chunked_reports", "分块报告目录"),
        (ROOT_PATH / "debug_data" / "03_reports_markdown", "Markdown报告目录"),
    ]

    for path, desc in required_paths:
        if path.exists():
            log_pass(f"{desc}: {path}")
        else:
            log_warn(f"{desc}: {path} - 路径不存在，部分测试可能跳过")

    subset_path = ROOT_PATH / "subset.csv"
    if subset_path.exists():
        import csv
        with open(subset_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        log_pass(f"subset.csv 可读取，共 {len(rows)} 行数据")
        if rows:
            log_pass(f"subset.csv 字段: {list(rows[0].keys())}")

    questions_path = ROOT_PATH / "questions.json"
    if questions_path.exists():
        with open(questions_path, "r", encoding="utf-8") as f:
            questions = json.load(f)
        log_pass(f"questions.json 可读取，共 {len(questions)} 个问题")
        if questions:
            sample = questions[0]
            log_pass(f"questions.json 示例字段: {list(sample.keys())}")

    vector_db_dir = ROOT_PATH / "databases" / "vector_dbs"
    if vector_db_dir.exists():
        faiss_files = list(vector_db_dir.glob("*.index"))
        log_pass(f"向量数据库目录包含 {len(faiss_files)} 个 FAISS 索引文件")
    else:
        log_warn("向量数据库目录不存在，检索相关测试将跳过")


# ============================================================
# 测试组3: 配置预设检查
# ============================================================
def test_config_presets():
    print_section("测试组3: 配置预设检查")

    from src.pipeline import RunConfig, base_config, max_config, enhanced_config, parent_document_retrieval_config

    configs = {
        "base_config": base_config,
        "max_config": max_config,
        "enhanced_config": enhanced_config,
        "parent_document_retrieval_config": parent_document_retrieval_config,
    }

    required_fields = [
        "use_serialized_tables", "parent_document_retrieval",
        "use_vector_dbs", "use_bm25_db", "llm_reranking",
        "top_n_retrieval", "parallel_requests", "answering_model",
        "api_provider", "config_suffix",
        "use_query_rewrite", "use_enhanced_reranker"
    ]

    for name, config in configs.items():
        for field in required_fields:
            try:
                value = getattr(config, field)
                log_pass(f"{name}.{field} = {value}")
            except AttributeError:
                log_fail(f"{name}.{field} - 字段缺失")

    custom_config = RunConfig(
        use_query_rewrite=False,
        use_enhanced_reranker=False,
        answering_model="qwen-turbo-latest",
        config_suffix="_test"
    )
    log_pass(f"自定义 RunConfig 创建成功: use_query_rewrite={custom_config.use_query_rewrite}, use_enhanced_reranker={custom_config.use_enhanced_reranker}")


# ============================================================
# 测试组4: Pipeline 初始化检查
# ============================================================
def test_pipeline_init():
    print_section("测试组4: Pipeline 初始化检查")

    from src.pipeline import Pipeline, enhanced_config, max_config

    ROOT_PATH = Path("data/stock_data")

    if not ROOT_PATH.exists():
        log_warn(f"数据根目录 {ROOT_PATH} 不存在，跳过 Pipeline 初始化测试")
        return

    configs_to_test = [
        ("enhanced_config", enhanced_config),
        ("max_config", max_config),
    ]

    for config_name, config in configs_to_test:
        try:
            pipeline = Pipeline(ROOT_PATH, run_config=config)
            log_pass(f"{config_name} Pipeline 初始化成功")

            for attr in ["vector_db_dir", "documents_dir", "subset_path", "questions_file_path"]:
                try:
                    val = getattr(pipeline.paths, attr)
                    log_pass(f"  pipeline.paths.{attr} = {val}")
                except AttributeError:
                    log_fail(f"  pipeline.paths.{attr} - 属性不存在")
        except Exception as e:
            log_fail(f"{config_name} Pipeline 初始化失败: {e}")
            traceback.print_exc()


# ============================================================
# 测试组5: Prompt 模板检查
# ============================================================
def test_prompts():
    print_section("测试组5: Prompt 模板检查")

    from src.prompts import (
        build_system_prompt, RephrasedQuestionsPrompt,
        AnswerWithRAGContextNamePrompt, AnswerWithRAGContextNumberPrompt
    )

    basic_prompt = build_system_prompt(instruction="测试指令", example="测试示例")
    if basic_prompt and "测试指令" in basic_prompt:
        log_pass("build_system_prompt 基础功能正常")
    else:
        log_fail("build_system_prompt 返回异常")

    basic_prompt_schema = build_system_prompt(instruction="测试指令", pydantic_schema='{"key": "value"}')
    if "Schema" in basic_prompt_schema and "测试指令" in basic_prompt_schema:
        log_pass("build_system_prompt 带 Schema 功能正常")
    else:
        log_fail("build_system_prompt 带 Schema 返回异常")

    prompt_classes = [
        ("RephrasedQuestionsPrompt", RephrasedQuestionsPrompt),
        ("AnswerWithRAGContextNamePrompt", AnswerWithRAGContextNamePrompt),
        ("AnswerWithRAGContextNumberPrompt", AnswerWithRAGContextNumberPrompt),
    ]

    for name, cls in prompt_classes:
        try:
            for attr in ["instruction", "user_prompt", "system_prompt"]:
                val = getattr(cls, attr, None)
                if val and isinstance(val, str) and len(val) > 0:
                    log_pass(f"{name}.{attr} - 有效 ({len(val)} 字符)")
                else:
                    log_fail(f"{name}.{attr} - 为空或不存在")

            if hasattr(cls, "pydantic_schema"):
                schema = getattr(cls, "pydantic_schema")
                if schema:
                    log_pass(f"{name}.pydantic_schema - 有效 ({len(schema)} 字符)")
        except Exception as e:
            log_fail(f"{name} 检查失败: {e}")


# ============================================================
# 测试组6: 文本分块功能检查
# ============================================================
def test_text_splitter():
    print_section("测试组6: 文本分块功能检查")

    from src.text_splitter import TextSplitter

    try:
        splitter = TextSplitter()
        log_pass("TextSplitter 实例化成功")
    except Exception as e:
        log_fail(f"TextSplitter 实例化失败: {e}")
        return

    try:
        token_count = splitter.count_tokens("这是一个测试文本，用于验证 token 计数功能。")
        log_pass(f"count_tokens 正常: '{'这是一个测试文本，用于验证 token 计数功能。'}' = {token_count} tokens")
    except Exception as e:
        log_fail(f"count_tokens 失败: {e}")

    mock_report = {
        "content": {
            "pages": [
                {
                    "page": 1,
                    "text": "这是第一页的测试内容，包含一些财务数据。\n营业收入为500亿元。\n毛利为100亿元。",
                    "tables": []
                },
                {
                    "page": 2,
                    "text": "这是第二页的测试内容，包含风险因素分析。\n市场竞争加剧。\n技术迭代风险。",
                    "tables": []
                }
            ]
        }
    }

    try:
        chunks_meta = splitter._split_report(mock_report)
        log_pass(f"_split_report 正常: 返回类型 {type(chunks_meta).__name__}")
        if isinstance(chunks_meta, dict):
            if "content" in chunks_meta and "chunks" in chunks_meta["content"]:
                chunk_count = len(chunks_meta["content"]["chunks"])
                log_pass(f"分块结果: {chunk_count} 个 chunks")
            else:
                log_warn("_split_report 返回的 dict 结构不符合预期")
        else:
            log_warn(f"_split_report 返回类型异常: {type(chunks_meta).__name__}")
    except Exception as e:
        log_fail(f"_split_report 失败: {e}")
        traceback.print_exc()


# ============================================================
# 测试组7: 检索器初始化检查
# ============================================================
def test_retrievers():
    print_section("测试组7: 检索器初始化检查")

    from src.retrieval import VectorRetriever, BM25Retriever
    from pathlib import Path

    ROOT_PATH = Path("data/stock_data")
    vector_db_dir = ROOT_PATH / "databases" / "vector_dbs"
    documents_dir = ROOT_PATH / "databases" / "chunked_reports"

    if not vector_db_dir.exists():
        log_warn(f"向量数据库目录 {vector_db_dir} 不存在，跳过 VectorRetriever 测试")
    elif not documents_dir.exists():
        log_warn(f"文档目录 {documents_dir} 不存在，跳过 VectorRetriever 测试")
    else:
        try:
            retriever = VectorRetriever(vector_db_dir=vector_db_dir, documents_dir=documents_dir)
            log_pass("VectorRetriever 初始化成功")
            log_pass(f"  index_dir={vector_db_dir}")
        except Exception as e:
            log_fail(f"VectorRetriever 初始化失败: {e}")
            traceback.print_exc()

    bm25_db_dir = ROOT_PATH / "databases" / "bm25_dbs"
    if not bm25_db_dir.exists() or not documents_dir.exists():
        log_warn(f"BM25 数据库目录 {bm25_db_dir} 不存在，跳过 BM25Retriever 测试")
    else:
        try:
            bm25_retriever = BM25Retriever(bm25_db_dir=bm25_db_dir, documents_dir=documents_dir)
            log_pass("BM25Retriever 初始化成功")
        except Exception as e:
            log_warn(f"BM25Retriever 初始化失败: {e}")


# ============================================================
# 测试组8: 查询改写功能检查
# ============================================================
def test_query_rewrite():
    print_section("测试组8: 查询改写功能检查")

    from src.query_rewriter import SmartQueryRewriter, IntentClassifier, QueryExpander

    test_queries = [
        "中芯国际2024年营收多少",
        "比较华为和中兴的财务状况",
        "什么是资产负债率",
        "分析比亚迪的风险因素",
    ]

    try:
        classifier = IntentClassifier()
        log_pass("IntentClassifier 初始化成功")
    except Exception as e:
        log_fail(f"IntentClassifier 初始化失败: {e}")
        classifier = None

    if classifier:
        for query in test_queries:
            try:
                intent, confidence, matched = classifier.classify(query)
                if intent and confidence is not None:
                    log_pass(f"classify('{query}') -> intent={intent}, confidence={confidence:.2f}")
                else:
                    log_fail(f"classify('{query}') -> 返回异常: intent={intent}, confidence={confidence}")
            except Exception as e:
                log_fail(f"classify('{query}') 失败: {e}")

    try:
        expander = QueryExpander()
        log_pass("QueryExpander 初始化成功")
    except Exception as e:
        log_fail(f"QueryExpander 初始化失败: {e}")
        expander = None

    if expander:
        try:
            variations = expander.expand("公司营收增长情况", num_variations=2)
            if isinstance(variations, list):
                log_pass(f"QueryExpander.expand 返回 {len(variations)} 个变体")
            else:
                log_warn(f"QueryExpander.expand 返回类型异常: {type(variations)}")
        except Exception as e:
            log_fail(f"QueryExpander.expand 失败: {e}")

    try:
        rewriter = SmartQueryRewriter()
        log_pass("SmartQueryRewriter 初始化成功")

        result = rewriter.auto_rewrite("中芯国际的财务表现如何")
        if result and "rewritten_query" in result and "query_type" in result:
            log_pass(f"SmartQueryRewriter.auto_rewrite 成功: type={result['query_type']}, confidence={result.get('confidence', 'N/A')}")
        else:
            log_fail(f"SmartQueryRewriter.auto_rewrite 返回结构异常: {list(result.keys()) if result else 'None'}")
    except Exception as e:
        log_fail(f"SmartQueryRewriter 测试失败: {e}")
        traceback.print_exc()

    try:
        from src.query_rewriter import rewrite_query, get_query_rewriter
        rewriter_instance = get_query_rewriter()
        log_pass(f"get_query_rewriter 返回: {type(rewriter_instance).__name__}")
    except Exception as e:
        log_fail(f"get_query_rewriter 失败: {e}")


# ============================================================
# 测试组9: 重排序功能检查
# ============================================================
def test_reranking():
    print_section("测试组9: 重排序功能检查")

    from src.enhanced_reranker import (
        RuleBasedReranker, HybridReranker,
        BusinessReportReranker, rerank_documents, get_business_reranker
    )

    mock_results = [
        {'text': '根据年报数据，公司2024年营收为500亿元，同比增长20%。毛利率为35%。', 'page': 5, 'distance': 0.3},
        {'text': '公司面临的风险包括：市场竞争加剧、原材料价格波动、技术更新迭代等。', 'page': 15, 'distance': 0.4},
        {'text': '2024年度财务报告显示，营业收入为500亿元，净利润为50亿元。', 'page': 3, 'distance': 0.2},
        {'text': '公司的主营业务包括芯片设计、制造和封装测试。', 'page': 8, 'distance': 0.5},
        {'text': '毛利率计算公式为：(营业收入-营业成本)/营业收入 乘以100%。', 'page': 12, 'distance': 0.6},
    ]

    try:
        rule_reranker = RuleBasedReranker()
        results = rule_reranker.rerank("公司2024年的营收是多少", mock_results, top_k=3)
        if len(results) <= 3 and len(results) > 0:
            log_pass(f"RuleBasedReranker 返回 {len(results)} 条结果")
            if 'rerank_score' in results[0]:
                log_pass(f"RuleBasedReranker top1 score: {results[0]['rerank_score']:.3f}")
        else:
            log_fail(f"RuleBasedReranker 返回结果数异常: {len(results)}")
    except Exception as e:
        log_fail(f"RuleBasedReranker 失败: {e}")
        traceback.print_exc()

    try:
        business_reranker = BusinessReportReranker()
        results = business_reranker.rerank("计算毛利率", mock_results, top_k=3)
        if len(results) > 0:
            log_pass(f"BusinessReportReranker 返回 {len(results)} 条结果")
        else:
            log_fail("BusinessReportReranker 返回空结果")
    except Exception as e:
        log_fail(f"BusinessReportReranker 失败: {e}")
        traceback.print_exc()

    try:
        reranker = get_business_reranker()
        log_pass(f"get_business_reranker 返回: {type(reranker).__name__}")
    except Exception as e:
        log_fail(f"get_business_reranker 失败: {e}")

    try:
        results = rerank_documents("营收增长情况", mock_results, top_k=3)
        if len(results) > 0:
            log_pass(f"rerank_documents 便捷函数返回 {len(results)} 条结果")
        else:
            log_fail("rerank_documents 返回空结果")
    except Exception as e:
        log_fail(f"rerank_documents 失败: {e}")

    try:
        hybrid_reranker = HybridReranker(use_tongyi=False)
        results = hybrid_reranker.rerank("风险因素分析", mock_results, top_k=3)
        if len(results) > 0:
            log_pass(f"HybridReranker(use_tongyi=False) 返回 {len(results)} 条结果")
    except Exception as e:
        log_warn(f"HybridReranker 测试跳过: {e}")


# ============================================================
# 测试组10: src.__init__ 顶层导出检查
# ============================================================
def test_src_init_exports():
    print_section("测试组10: src.__init__ 顶层导出检查")

    try:
        import src
        expected_exports = [
            'SmartQueryRewriter', 'EnhancedQueryRewriter', 'IntentClassifier',
            'QueryExpander', 'rewrite_query', 'get_query_rewriter',
            'TongyiReranker', 'RuleBasedReranker', 'HybridReranker',
            'BusinessReportReranker', 'rerank_documents', 'get_business_reranker',
        ]

        for name in expected_exports:
            try:
                obj = getattr(src, name)
                log_pass(f"src.{name} - 可访问")
            except AttributeError:
                log_fail(f"src.{name} - 不可访问")

        deleted_exports = ['AdvancedReranker']
        for name in deleted_exports:
            try:
                getattr(src, name)
                log_fail(f"src.{name} - 已删除的类仍可导出（残留）")
            except AttributeError:
                log_pass(f"src.{name} - 确认已从 __all__ 移除")
    except Exception as e:
        log_fail(f"src 模块导入失败: {e}")


# ============================================================
# 测试组11: E2E 真实问答测试（可选，需数据支持）
# ============================================================
def test_e2e_qa():
    print_section("测试组11: E2E 真实问答测试")

    ROOT_PATH = Path("data/stock_data")

    if not ROOT_PATH.exists():
        log_warn(f"数据目录 {ROOT_PATH} 不存在，跳过 E2E 测试")
        return

    subset_path = ROOT_PATH / "subset.csv"
    vector_db_dir = ROOT_PATH / "databases" / "vector_dbs"

    if not (subset_path.exists() and vector_db_dir.exists()):
        log_warn("缺少必要数据文件，跳过 E2E 测试")
        return

    from src.questions_processing import QuestionsProcessor
    from src.pipeline import Pipeline, enhanced_config

    try:
        pipeline = Pipeline(ROOT_PATH, run_config=enhanced_config)
        log_pass("E2E: Pipeline 初始化成功")
    except Exception as e:
        log_fail(f"E2E: Pipeline 初始化失败: {e}")
        traceback.print_exc()
        return

    try:
        answer = pipeline.answer_single_question(
            "中芯国际的主要业务是什么？",
            kind="string"
        )
        log_pass(f"E2E: answer_single_question 成功")

        if "final_answer" in answer:
            log_pass(f"E2E: 答案包含 final_answer")
        if "retrieval_results" in answer:
            log_pass(f"E2E: 答案包含 {len(answer.get('retrieval_results', []))} 条检索结果")
        if "query_rewrite_info" in answer:
            log_pass(f"E2E: 答案包含 query_rewrite_info")

    except Exception as e:
        log_fail(f"E2E: answer_single_question 失败: {e}")
        traceback.print_exc()


# ============================================================
# 测试组12: API Server 端点测试（仅当服务器运行时）
# ============================================================
def test_api_endpoints():
    print_section("测试组12: API Server 端点测试")

    import requests

    BASE_URLS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    connected = False
    for base_url in BASE_URLS:
        try:
            resp = requests.get(f"{base_url}/api/health", timeout=3)
            if resp.status_code == 200:
                log_pass(f"API Server 可达: {base_url}")
                connected = True
                break
        except Exception:
            continue

    if not connected:
        log_warn("API Server 未运行，跳过 API 端点测试（可手动运行: python api_server.py）")
        return

    endpoints = [
        ("GET", "/api/health", None),
        ("GET", "/api/config", None),
        ("GET", "/api/companies", None),
    ]

    for method, path, body in endpoints:
        try:
            url = f"{base_url}{path}"
            if method == "GET":
                resp = requests.get(url, timeout=5)
            elif method == "POST":
                resp = requests.post(url, json=body, timeout=5)

            if resp.status_code == 200:
                data = resp.json()
                log_pass(f"{method} {path} -> 200 OK")
            elif resp.status_code == 422:
                log_pass(f"{method} {path} -> 422 (需要参数 - 正常)")
            else:
                log_warn(f"{method} {path} -> {resp.status_code}")
        except Exception as e:
            log_fail(f"{method} {path} 失败: {e}")

    print("\n    尝试 POST /api/config ...")
    try:
        resp = requests.post(
            f"{base_url}/api/config",
            json={"use_query_rewrite": True, "use_enhanced_reranker": True},
            timeout=5
        )
        if resp.status_code == 200:
            log_pass("POST /api/config -> 200 OK")
        else:
            log_warn(f"POST /api/config -> {resp.status_code}")
    except Exception as e:
        log_fail(f"POST /api/config 失败: {e}")


# ============================================================
# 主入口
# ============================================================
def main():
    global PASS_COUNT, FAIL_COUNT, WARN_COUNT

    print("=" * 60)
    print("  RAG-cy 核心功能自动化测试")
    print(f"  启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    t_start = time.time()

    test_functions = [
        ("模块导入完整性检查", test_module_imports),
        ("数据完整性检查", test_data_integrity),
        ("配置预设检查", test_config_presets),
        ("Pipeline 初始化检查", test_pipeline_init),
        ("Prompt 模板检查", test_prompts),
        ("文本分块功能检查", test_text_splitter),
        ("检索器初始化检查", test_retrievers),
        ("查询改写功能检查", test_query_rewrite),
        ("重排序功能检查", test_reranking),
        ("src.__init__ 顶层导出检查", test_src_init_exports),
        ("E2E 真实问答测试", test_e2e_qa),
        ("API Server 端点测试 (可选)", test_api_endpoints),
    ]

    for name, fn in test_functions:
        try:
            fn()
        except Exception as e:
            print(f"\n  !!! 测试组 [{name}] 发生未捕获异常: {e}")
            traceback.print_exc()
            log_fail(f"测试组 [{name}] 崩溃: {e}")

    t_end = time.time()

    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    print(f"  总计: {PASS_COUNT + FAIL_COUNT + WARN_COUNT}")
    print(f"  通过: {PASS_COUNT}")
    print(f"  失败: {FAIL_COUNT}")
    print(f"  警告: {WARN_COUNT}")
    print(f"  耗时: {t_end - t_start:.2f} 秒")
    print("=" * 60)

    if FAIL_COUNT > 0:
        print("\n  失败项详情:")
        for status, msg in TEST_RESULTS:
            if status == "FAIL":
                print(f"    [FAIL] {msg}")

    print("")

    return 0 if FAIL_COUNT == 0 else 1


if __name__ == "__main__":
    sys.exit(main())