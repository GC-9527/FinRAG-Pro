# -*- coding: utf-8 -*-
"""
端到端测试脚本：全面验证增强版RAG系统的各项功能
"""
import sys
import os
import time
import traceback

# 确保当前目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# 测试1: 模块导入检查
# ============================================================
def test_module_imports():
    print("=" * 60)
    print("测试1: 模块导入检查")
    print("=" * 60)
    
    modules_to_test = [
        ("src.query_rewriter", "SmartQueryRewriter"),
        ("src.query_rewriter", "EnhancedQueryRewriter"),
        ("src.query_rewriter", "IntentClassifier"),
        ("src.query_rewriter", "QueryExpander"),
        ("src.query_rewriter", "rewrite_query"),
        ("src.query_rewriter", "get_query_rewriter"),
        ("src.enhanced_reranker", "TongyiReranker"),
        ("src.enhanced_reranker", "RuleBasedReranker"),
        ("src.enhanced_reranker", "HybridReranker"),
        ("src.enhanced_reranker", "BusinessReportReranker"),
        ("src.enhanced_reranker", "rerank_documents"),
        ("src.enhanced_reranker", "get_business_reranker"),
        ("src.questions_processing", "QuestionsProcessor"),
        ("src.pipeline", "Pipeline"),
        ("src.pipeline", "RunConfig"),
        ("src.pipeline", "enhanced_config"),
        ("src.pipeline", "max_config"),
    ]
    
    all_pass = True
    for module_name, class_name in modules_to_test:
        try:
            mod = __import__(module_name, fromlist=[class_name])
            obj = getattr(mod, class_name)
            print(f"  [OK] {module_name}.{class_name}")
        except Exception as e:
            print(f"  [FAIL] {module_name}.{class_name}: {e}")
            all_pass = False
    
    return all_pass


# ============================================================
# 测试2: 查询改写功能（真实数据）
# ============================================================
def test_query_rewrite():
    print("\n" + "=" * 60)
    print("测试2: 查询改写功能")
    print("=" * 60)
    
    from src.query_rewriter import SmartQueryRewriter
    
    rewriter = SmartQueryRewriter()
    
    test_queries = [
        ("中芯国际在晶圆制造行业中的地位如何？其服务范围和全球布局是怎样的？", "综合查询"),
        ("中芯国际的营收和利润情况近期有何变化？影响因素是什么？", "趋势/财务"),
        ("美国对中国半导体产业的限制政策对中芯国际有何影响？", "风险/解释"),
        ("中芯国际的收入结构有何变化？尤其是在中国大陆和北美市场的表现如何？", "比较/业务"),
    ]
    
    all_pass = True
    for query, expected_type in test_queries:
        print(f"\n  原始: {query}")
        print(f"  期望类型: {expected_type}")
        try:
            t0 = time.time()
            result = rewriter.auto_rewrite(query)
            elapsed = time.time() - t0
            
            print(f"  改写后: {result['rewritten_query']}")
            print(f"  识别类型: {result['query_type']}")
            print(f"  置信度: {result['confidence']}")
            print(f"  耗时: {elapsed:.2f}秒")
            
            # 检查必需字段是否存在
            required_fields = ['rewritten_query', 'query_type', 'confidence']
            for field in required_fields:
                if field not in result:
                    print(f"  [FAIL] 缺少字段: {field}")
                    all_pass = False
            
            if result.get('rewritten_query') and result['rewritten_query'] != query:
                print(f"  [OK] 改写成功")
            else:
                print(f"  [WARN] 改写结果与原始查询相同")
                
        except Exception as e:
            print(f"  [FAIL] 改写出错: {e}")
            all_pass = False
    
    return all_pass


# ============================================================
# 测试3: 增强重排序功能（模拟数据）
# ============================================================
def test_enhanced_rerank():
    print("\n" + "=" * 60)
    print("测试3: 增强重排序功能")
    print("=" * 60)
    
    from src.enhanced_reranker import BusinessReportReranker, RuleBasedReranker, TongyiReranker
    
    # 模拟企业年报检索结果
    mock_results = [
        {'text': '报告期内，集团实现营业收入80.18亿美元，较2023年的63.22亿美元增长27.7%。毛利由2023年的13.28亿美元增至2024年的16.40亿美元，毛利率由21.0%升至20.5%。', 'page': 2, 'distance': 0.25},
        {'text': '中芯国际是世界领先的集成电路晶圆代工企业之一，也是中国大陆集成电路制造业的领导者。', 'page': 1, 'distance': 0.15},
        {'text': '公司面临的主要风险包括：地缘政治风险、行业周期波动、技术迭代风险、人才竞争风险。', 'page': 80, 'distance': 0.45},
        {'text': '中国大陆地区收入占比从2023年的53.5%上升至2024年的58.7%，北美地区收入占比从2023年的23.3%下降至2024年的19.8%。', 'page': 35, 'distance': 0.30},
        {'text': '研发投入持续增加，2024年研发支出达12.5亿美元，占营业收入的15.6%。', 'page': 42, 'distance': 0.35},
    ]
    
    all_pass = True
    
    # 测试规则排序器
    print("\n  --- 规则排序器测试 ---")
    rule_reranker = RuleBasedReranker()
    
    queries = [
        ("中芯国际的营收是多少", "计算"),
        ("什么是风险因素", "风险"),
        ("中国大陆和北美市场对比", "比较"),
    ]
    
    for query, qtype in queries:
        print(f"\n  查询: {query} (类型: {qtype})")
        try:
            results = rule_reranker.rerank(query, mock_results, top_k=3)
            for i, r in enumerate(results, 1):
                print(f"    {i}. 页{r['page']:3d} | 分数: {r['rerank_score']:.3f} | {r['text'][:50]}...")
        except Exception as e:
            print(f"    [FAIL] {e}")
            all_pass = False
    
    # 测试企业年报排序器
    print("\n  --- 企业年报排序器测试 ---")
    business_reranker = BusinessReportReranker()
    
    for query, qtype in queries:
        print(f"\n  查询: {query} (类型: {qtype})")
        try:
            results = business_reranker.rerank(query, mock_results, top_k=3)
            for i, r in enumerate(results, 1):
                print(f"    {i}. 页{r['page']:3d} | 分数: {r['rerank_score']:.3f} | {r['text'][:50]}...")
        except Exception as e:
            print(f"    [FAIL] {e}")
            all_pass = False
    
    # 测试便捷函数
    print("\n  --- 便捷函数测试 ---")
    try:
        from src.enhanced_reranker import rerank_documents
        results = rerank_documents("营收增长情况", mock_results, top_k=3)
        print(f"    返回结果数: {len(results)}")
        if len(results) > 0:
            print(f"    top1 页码: {results[0]['page']}")
            print(f"    [OK] 便捷函数可用")
        else:
            print(f"    [FAIL] 返回空结果")
            all_pass = False
    except Exception as e:
        print(f"    [FAIL] {e}")
        all_pass = False
    
    return all_pass


# ============================================================
# 测试4: Pipeline初始化检查
# ============================================================
def test_pipeline_init():
    print("\n" + "=" * 60)
    print("测试4: Pipeline初始化检查")
    print("=" * 60)
    
    from pathlib import Path
    from src.pipeline import Pipeline, RunConfig, enhanced_config, max_config
    
    root_path = Path("data/stock_data")
    
    all_pass = True
    
    # 检查数据目录
    required_paths = [
        root_path / "subset.csv",
        root_path / "questions.json",
        root_path / "databases" / "vector_dbs",
        root_path / "databases" / "chunked_reports",
    ]
    
    print("\n  --- 数据完整性检查 ---")
    for p in required_paths:
        exists = p.exists()
        status = "[OK]" if exists else "[FAIL]"
        print(f"    {status} {p}")
        if not exists:
            all_pass = False
    
    if not all_pass:
        return False
    
    # 测试增强配置初始化
    print("\n  --- 配置初始化 ---")
    try:
        pipeline = Pipeline(root_path, run_config=enhanced_config)
        print(f"    [OK] enhanced_config 初始化成功")
        print(f"        vector_db_dir: {pipeline.paths.vector_db_dir}")
        print(f"        documents_dir: {pipeline.paths.documents_dir}")
        print(f"        subset_path: {pipeline.paths.subset_path}")
        print(f"        use_query_rewrite: {pipeline.run_config.use_query_rewrite}")
        print(f"        use_enhanced_reranker: {pipeline.run_config.use_enhanced_reranker}")
    except Exception as e:
        print(f"    [FAIL] enhanced_config: {e}")
        all_pass = False
    
    # 测试max_config初始化
    try:
        pipeline2 = Pipeline(root_path, run_config=max_config)
        print(f"    [OK] max_config 初始化成功")
        print(f"        use_query_rewrite: {pipeline2.run_config.use_query_rewrite}")
        print(f"        use_enhanced_reranker: {pipeline2.run_config.use_enhanced_reranker}")
    except Exception as e:
        print(f"    [FAIL] max_config: {e}")
        all_pass = False
    
    return all_pass


# ============================================================
# 测试5: QuestionsProcessor集成测试
# ============================================================
def test_questions_processor():
    print("\n" + "=" * 60)
    print("测试5: QuestionsProcessor集成测试")
    print("=" * 60)
    
    from pathlib import Path
    from src.questions_processing import QuestionsProcessor
    
    root_path = Path("data/stock_data")
    vector_db_dir = root_path / "databases" / "vector_dbs"
    documents_dir = root_path / "databases" / "chunked_reports"
    subset_path = root_path / "subset.csv"
    questions_file = root_path / "questions.json"
    
    all_pass = True
    
    print("\n  --- QuestionsProcessor初始化 ---")
    try:
        processor = QuestionsProcessor(
            vector_db_dir=str(vector_db_dir),
            documents_dir=str(documents_dir),
            questions_file_path=str(questions_file),
            new_challenge_pipeline=True,
            subset_path=str(subset_path),
            parent_document_retrieval=False,
            llm_reranking=False,
            top_n_retrieval=5,
            parallel_requests=1,
            api_provider="dashscope",
            answering_model="qwen-turbo-latest",
            use_query_rewrite=True,
            use_enhanced_reranker=True
        )
        print(f"    [OK] QuestionsProcessor 初始化成功")
        print(f"        问题数: {len(processor.questions)}")
        print(f"        query_rewriter: {processor.query_rewriter is not None}")
        print(f"        enhanced_reranker: {processor.enhanced_reranker is not None}")
        print(f"        use_query_rewrite: {processor.use_query_rewrite}")
        print(f"        use_enhanced_reranker: {processor.use_enhanced_reranker}")
    except Exception as e:
        print(f"    [FAIL] 初始化失败: {e}")
        traceback.print_exc()
        return False
    
    # 测试单条问题处理
    print("\n  --- 单条问题处理测试 ---")
    test_question = processor.questions[0]["text"]
    test_kind = processor.questions[0]["kind"]
    print(f"    问题: {test_question}")
    print(f"    类型: {test_kind}")
    
    try:
        t0 = time.time()
        answer = processor.process_single_question(test_question, kind=test_kind)
        elapsed = time.time() - t0
        
        print(f"    耗时: {elapsed:.2f}秒")
        print(f"    答案键: {list(answer.keys())}")
        
        if "error" in answer:
            print(f"    [FAIL] 答案包含错误: {answer['error']}")
            all_pass = False
        elif answer.get("final_answer"):
            final = answer["final_answer"]
            print(f"    [OK] 成功生成答案")
            print(f"    最终答案: {str(final)[:200]}...")
            
            # 检查query_rewrite_info
            if answer.get("query_rewrite_info"):
                print(f"    查询改写信息: {answer['query_rewrite_info']}")
            
            # 检查references
            if answer.get("references"):
                print(f"    引用数: {len(answer['references'])}")
        else:
            print(f"    [WARN] 答案中无final_answer字段")
            
    except Exception as e:
        print(f"    [FAIL] 处理出错: {e}")
        traceback.print_exc()
        all_pass = False
    
    # 测试第二条问题（避免QPS限流，只测2条）
    if len(processor.questions) > 1:
        print("\n  --- 第二条问题处理测试 ---")
        test_question2 = processor.questions[1]["text"]
        test_kind2 = processor.questions[1]["kind"]
        print(f"    问题: {test_question2}")
        
        try:
            t0 = time.time()
            answer2 = processor.process_single_question(test_question2, kind=test_kind2)
            elapsed = time.time() - t0
            
            print(f"    耗时: {elapsed:.2f}秒")
            print(f"    答案键: {list(answer2.keys())}")
            
            if "error" in answer2:
                print(f"    [FAIL] 答案包含错误: {answer2['error']}")
                all_pass = False
            elif answer2.get("final_answer"):
                print(f"    [OK] 成功生成答案")
                print(f"    最终答案: {str(answer2['final_answer'])[:200]}...")
                
                # 检查query_rewrite_info
                if answer2.get("query_rewrite_info"):
                    print(f"    查询改写信息: {answer2['query_rewrite_info']}")
            else:
                print(f"    [WARN] 答案中无final_answer字段")
                
        except Exception as e:
            print(f"    [FAIL] 处理出错: {e}")
            traceback.print_exc()
            all_pass = False
    
    return all_pass


# ============================================================
# 测试6: Pipeline完整流程测试
# ============================================================
def test_full_pipeline():
    print("\n" + "=" * 60)
    print("测试6: Pipeline完整流程测试")
    print("=" * 60)
    
    from pathlib import Path
    from src.pipeline import Pipeline, enhanced_config
    
    root_path = Path("data/stock_data")
    
    if not (root_path / "subset.csv").exists():
        print("    [SKIP] 数据目录不存在")
        return True
    
    try:
        pipeline = Pipeline(root_path, run_config=enhanced_config)
        print(f"    [OK] Pipeline 初始化成功")
        
        # 测试单问
        print("\n  --- answer_single_question 测试 ---")
        question = "中芯国际在晶圆制造行业中的地位如何？"
        print(f"    问题: {question}")
        
        t0 = time.time()
        answer = pipeline.answer_single_question(question, kind="string")
        elapsed = time.time() - t0
        
        print(f"    总耗时: {elapsed:.2f}秒")
        
        # 检查返回结果
        if isinstance(answer, dict):
            if "error" in answer:
                print(f"    [FAIL] 答案包含错误: {answer['error']}")
                return False
            elif "final_answer" in answer:
                print(f"    [OK] Pipeline成功返回答案")
                print(f"    答案: {str(answer['final_answer'])[:200]}...")
                if "query_rewrite_info" in answer:
                    print(f"    查询改写: {answer['query_rewrite_info']}")
                return True
            else:
                print(f"    [WARN] 返回结果结构: {list(answer.keys())[:10]}")
                return True
        else:
            print(f"    [WARN] 返回类型: {type(answer)}")
            return True
            
    except Exception as e:
        print(f"    [FAIL] Pipeline测试出错: {e}")
        traceback.print_exc()
        return False


# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 70)
    print("   RAG-cy 增强版端到端测试")
    print("=" * 70)
    print(f"   时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    results = {}
    
    # 先运行不需要数据的测试
    results["模块导入"] = test_module_imports()
    results["查询改写"] = test_query_rewrite()
    results["增强重排序"] = test_enhanced_rerank()
    results["Pipeline初始化"] = test_pipeline_init()
    
    # 再运行需要数据的测试
    results["QuestionsProcessor"] = test_questions_processor()
    results["完整Pipeline"] = test_full_pipeline()
    
    # 输出总结
    print("\n" + "=" * 70)
    print("   测试结果总结")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
    
    print(f"\n  总计: {passed}/{total} 通过")
    
    if passed == total:
        print("  状态: 全部测试通过!")
        return 0
    else:
        print(f"  状态: {total - passed} 项测试失败")
        return 1


if __name__ == "__main__":
    exit(main())