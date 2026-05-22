# -*- coding: utf-8 -*-
"""
测试脚本：验证查询改写和增强重排序功能
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.query_rewriter import SmartQueryRewriter, rewrite_query
from src.enhanced_reranker import (
    TongyiReranker, 
    RuleBasedReranker, 
    HybridReranker,
    BusinessReportReranker,
    rerank_documents
)


def test_query_rewriter():
    """测试查询改写功能"""
    print("=" * 60)
    print("测试查询改写功能")
    print("=" * 60)
    
    rewriter = SmartQueryRewriter()
    
    test_queries = [
        "中芯国际2024年营收多少",
        "比较华为和中兴的财务状况",
        "什么是资产负债率",
        "分析比亚迪的风险因素",
        "计算茅台的毛利率"
    ]
    
    for query in test_queries:
        print(f"\n原始查询: {query}")
        result = rewriter.auto_rewrite(query)
        print(f"改写后: {result['rewritten_query']}")
        print(f"查询类型: {result['query_type']}, 置信度: {result['confidence']}")
        if result.get('variations'):
            print(f"查询变体: {result['variations']}")


def test_enhanced_reranker():
    """测试增强重排序功能"""
    print("\n" + "=" * 60)
    print("测试增强重排序功能")
    print("=" * 60)
    
    # 模拟检索结果
    mock_results = [
        {
            'text': '根据年报数据，公司2024年营收为500亿元，同比增长20%。毛利率为35%。',
            'page': 5,
            'distance': 0.3
        },
        {
            'text': '公司面临的风险包括：市场竞争加剧、原材料价格波动、技术更新迭代等。',
            'page': 15,
            'distance': 0.4
        },
        {
            'text': '2024年度财务报告显示，营业收入为500亿元，净利润为50亿元。',
            'page': 3,
            'distance': 0.2
        },
        {
            'text': '公司的主营业务包括芯片设计、制造和封装测试。',
            'page': 8,
            'distance': 0.5
        },
        {
            'text': '毛利率计算公式为：(营业收入-营业成本)/营业收入×100%。',
            'page': 12,
            'distance': 0.6
        }
    ]
    
    test_queries = [
        "公司2024年的营收是多少",
        "计算毛利率",
        "分析风险因素"
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 40)
        
        # 测试规则排序器
        rule_reranker = RuleBasedReranker()
        rule_results = rule_reranker.rerank(query, mock_results, top_k=3)
        print(f"\n规则排序结果 (top 3):")
        for i, r in enumerate(rule_results, 1):
            print(f"  {i}. 分数: {r.get('rerank_score', 0):.3f}, 页码: {r['page']}, 相似度: {r.get('similarity', 'N/A')}")
        
        # 测试企业年报专用排序器
        business_reranker = BusinessReportReranker()
        business_results = business_reranker.rerank(query, mock_results, top_k=3)
        print(f"\n企业年报专用排序结果 (top 3):")
        for i, r in enumerate(business_results, 1):
            print(f"  {i}. 分数: {r.get('rerank_score', 0):.3f}, 页码: {r['page']}, 相似度: {r.get('similarity', 'N/A')}")


def test_query_rewrite_utility():
    """测试便捷函数"""
    print("\n" + "=" * 60)
    print("测试便捷函数")
    print("=" * 60)
    
    query = "中芯国际的财务表现如何"
    result = rewrite_query(query)
    print(f"\n原始查询: {query}")
    print(f"改写结果: {result}")


if __name__ == "__main__":
    try:
        # 测试查询改写
        test_query_rewriter()
        
        # 测试增强重排序
        test_enhanced_reranker()
        
        # 测试便捷函数
        test_query_rewrite_utility()
        
        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
