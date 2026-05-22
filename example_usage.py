# -*- coding: utf-8 -*-
"""
使用示例：展示如何在新RAG系统中使用查询改写和增强重排序
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from src.questions_processing import QuestionsProcessor
from src.pipeline import Pipeline, enhanced_config


def example_1_standalone_usage():
    """
    示例1: 独立使用查询改写功能
    """
    print("=" * 60)
    print("示例1: 独立使用查询改写功能")
    print("=" * 60)
    
    from src.query_rewriter import SmartQueryRewriter, rewrite_query
    
    # 方式1: 使用类实例
    rewriter = SmartQueryRewriter()
    query = "华为的营收多少"
    result = rewriter.auto_rewrite(query)
    print(f"原始查询: {query}")
    print(f"改写结果: {result}")
    
    # 方式2: 使用便捷函数
    print("\n使用便捷函数:")
    result = rewrite_query("分析中兴的风险")
    print(f"改写结果: {result}")


def example_2_standalone_reranker():
    """
    示例2: 独立使用增强重排序功能
    """
    print("\n" + "=" * 60)
    print("示例2: 独立使用增强重排序功能")
    print("=" * 60)
    
    from src.enhanced_reranker import (
        BusinessReportReranker,
        rerank_documents
    )
    
    # 模拟检索结果
    mock_results = [
        {
            'text': '2024年公司营收为1000亿元，同比增长30%。',
            'page': 5,
            'distance': 0.3
        },
        {
            'text': '公司面临的主要风险包括市场风险和经营风险。',
            'page': 15,
            'distance': 0.4
        },
        {
            'text': '毛利率为45%，表现良好。',
            'page': 10,
            'distance': 0.5
        }
    ]
    
    # 方式1: 使用类实例
    reranker = BusinessReportReranker()
    query = "公司的营收和利润情况"
    reranked = reranker.rerank(query, mock_results, top_k=3)
    print(f"查询: {query}")
    print(f"重排序结果:")
    for i, r in enumerate(reranked, 1):
        print(f"  {i}. 页码: {r['page']}, 分数: {r['rerank_score']:.3f}")
    
    # 方式2: 使用便捷函数
    print("\n使用便捷函数:")
    reranked = rerank_documents("风险分析", mock_results, top_k=3)
    print(f"重排序结果:")
    for i, r in enumerate(reranked, 1):
        print(f"  {i}. 页码: {r['page']}, 分数: {r['rerank_score']:.3f}")


def example_3_full_pipeline():
    """
    示例3: 使用完整Pipeline（需要配置数据路径）
    """
    print("\n" + "=" * 60)
    print("示例3: 使用完整Pipeline")
    print("=" * 60)
    
    # 设置数据路径
    root_path = Path("data/stock_data")
    
    # 使用增强配置
    pipeline = Pipeline(root_path, run_config=enhanced_config)
    
    # 单条问题测试
    question = "中芯国际2024年的营业收入是多少"
    print(f"问题: {question}")
    print("注意: 需要确保数据目录存在且包含相关年报数据")
    
    try:
        # 这需要实际的数据文件才能运行
        answer = pipeline.answer_single_question(question, kind="number")
        print(f"答案: {answer}")
    except Exception as e:
        print(f"无法运行完整Pipeline (需要数据文件): {e}")


def example_4_questions_processor():
    """
    示例4: 直接使用QuestionsProcessor（需要配置数据路径）
    """
    print("\n" + "=" * 60)
    print("示例4: 直接使用QuestionsProcessor")
    print("=" * 60)
    
    # 配置路径
    vector_db_dir = './vector_dbs'
    documents_dir = './documents'
    subset_path = './subset.csv'
    
    try:
        # 初始化处理器（启用查询改写和增强重排序）
        processor = QuestionsProcessor(
            vector_db_dir=vector_db_dir,
            documents_dir=documents_dir,
            subset_path=subset_path,
            new_challenge_pipeline=True,
            use_query_rewrite=True,
            use_enhanced_reranker=True
        )
        
        question = "中芯国际的财务表现如何"
        print(f"问题: {question}")
        print("注意: 需要确保数据库目录存在且包含相关数据")
        
        # 单条问题处理
        answer = processor.process_single_question(question, kind="string")
        print(f"答案: {answer}")
        
    except FileNotFoundError as e:
        print(f"数据文件不存在: {e}")
        print("请确保已创建向量数据库和文档目录")
    except Exception as e:
        print(f"处理失败: {e}")


if __name__ == "__main__":
    print("RAG-cy 增强功能使用示例")
    print("=" * 60)
    print()
    
    # 示例1和2不需要数据文件，可以直接运行
    example_1_standalone_usage()
    example_2_standalone_reranker()
    
    # 示例3和4需要数据文件
    print("\n" + "=" * 60)
    print("以下示例需要数据文件，请确保已准备好数据")
    print("=" * 60)
    
    # example_3_full_pipeline()
    # example_4_questions_processor()
    
    print("\n使用说明:")
    print("1. 查询改写功能会自动将用户查询优化为更适合检索的形式")
    print("2. 增强重排序会根据查询类型和内容相关性进行智能排序")
    print("3. 在Pipeline中使用时，这些功能会自动启用")
    print("4. 可以通过use_query_rewrite和use_enhanced_reranker参数控制是否启用")
