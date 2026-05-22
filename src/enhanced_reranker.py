# -*- coding: utf-8 -*-
"""
增强版重排序模块
使用通义千问qwen3-rerank模型进行智能重排序
参考初会RAG助手的reranker实现，针对企业年报问答场景优化
"""
import os
import dashscope
from typing import List, Dict
from http import HTTPStatus


# 从环境变量获取API密钥
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
dashscope.api_key = DASHSCOPE_API_KEY


class TongyiReranker:
    """使用通义千问qwen3-rerank模型的排序器"""
    
    def __init__(self, model_name: str = "qwen3-rerank", top_n: int = 5):
        """
        初始化通义千问排序器
        
        Args:
            model_name: 模型名称，默认为 qwen3-rerank
            top_n: 返回的top n个结果
        """
        self.model_name = model_name
        self.top_n = top_n
    
    def rerank(self, query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        使用通义千问rerank模型对结果进行重排序
        
        Args:
            query: 用户查询
            results: 原始检索结果列表
            top_k: 返回前k个结果
            
        Returns:
            重排序后的结果
        """
        if not results:
            return []
        
        try:
            # 提取文档内容
            documents = []
            for result in results:
                # 支持不同的字段名
                content = result.get('text', result.get('content', ''))
                if content:
                    documents.append(content)
            
            if not documents:
                return results[:top_k]
            
            # 调用通义千问rerank API
            response = dashscope.TextReRank.call(
                model=self.model_name,
                query=query,
                documents=documents,
                top_n=min(top_k, len(documents)),
                return_documents=True,
                instruct="Given a business report query, retrieve relevant passages that answer the query."
            )
            
            if response.status_code != HTTPStatus.OK:
                print(f"通义Rerank API调用失败: {response.message}")
                # 如果API调用失败，使用原始结果
                return results[:top_k]
            
            # 解析响应
            reranked_results = []
            for item in response.output.results:
                idx = item.index
                score = item.relevance_score
                
                # 从原始结果中找到对应索引的文档
                if idx < len(results):
                    result = results[idx].copy()
                    result['rerank_score'] = score
                    result['similarity'] = f"{score * 100:.2f}%"
                    result['distance'] = 1 - score
                    reranked_results.append(result)
            
            return reranked_results
            
        except Exception as e:
            print(f"通义Rerank重排序失败: {str(e)}")
            # 出错时使用原始结果
            return results[:top_k]


class RuleBasedReranker:
    """基于规则的重排序器 - 针对企业年报场景"""
    
    def __init__(self, weights: Dict[str, float] = None):
        """
        初始化规则排序器
        
        Args:
            weights: 各策略的权重配置
        """
        self.weights = weights or {
            'semantic': 0.4,
            'keyword': 0.3,
            'position': 0.2,
            'quality': 0.1
        }
    
    def rerank(self, query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        基于规则对检索结果进行重排序
        
        Args:
            query: 用户查询
            results: 原始检索结果
            top_k: 返回前k个结果
            
        Returns:
            重排序后的结果
        """
        if not results:
            return []
        
        query_lower = query.lower()
        scored_results = []
        
        for result in results:
            scores = self._calculate_scores(query, query_lower, result)
            total_score = sum(
                scores[key] * self.weights[key] 
                for key in scores.keys()
            )
            
            result['rerank_score'] = total_score
            result['score_details'] = scores
            scored_results.append(result)
        
        scored_results.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        for result in scored_results[:top_k]:
            result['similarity'] = f"{result['rerank_score'] * 100:.2f}%"
            result['distance'] = 1 - result['rerank_score']
        
        return scored_results[:top_k]
    
    def _calculate_scores(self, query: str, query_lower: str, result: Dict) -> Dict[str, float]:
        """计算各项分数"""
        return {
            'semantic': self._calculate_semantic_score(result),
            'keyword': self._calculate_keyword_score(query_lower, result),
            'position': self._calculate_position_score(query_lower, result),
            'quality': self._calculate_quality_score(result)
        }
    
    def _calculate_semantic_score(self, result: Dict) -> float:
        """计算语义相似度分数"""
        # 优先使用rerank_score，其次使用distance
        rerank_score = result.get('rerank_score', 0)
        distance = result.get('distance', 0)
        
        # 如果有rerank_score，直接使用
        if rerank_score > 0:
            return rerank_score
        
        # 否则基于distance计算
        semantic_score = 1.0 - min(distance, 1.0)
        return semantic_score
    
    def _calculate_keyword_score(self, query_lower: str, result: Dict) -> float:
        """计算关键词匹配分数"""
        # 获取文本内容
        content = result.get('text', result.get('content', '')).lower()
        
        # 定义年报相关的关键词权重
        keywords_weights = {
            '收入': 1.5, '营收': 1.5, '利润': 1.5, '资产': 1.2, '负债': 1.2,
            '现金流': 1.3, '毛利率': 1.4, '净利率': 1.4, '同比': 1.3, '环比': 1.3,
            '主营业务': 1.2, '业务': 0.8, '产品': 0.8, '市场': 0.8,
            '风险': 1.2, '机遇': 1.2, '挑战': 1.2,
            '股东': 1.1, '股权': 1.1, '董事': 1.1, '治理': 1.0
        }
        
        score = 0.0
        matched_count = 0
        
        for keyword, weight in keywords_weights.items():
            if keyword in query_lower and keyword in content:
                score += weight
                matched_count += 1
            elif keyword in query_lower:
                score += 0.1  # 查询中有但文档中没有的关键词
        
        if matched_count == 0:
            return 0.5
        
        # 归一化分数
        return min(score / (len(keywords_weights) * 0.3), 1.0)
    
    def _calculate_position_score(self, query_lower: str, result: Dict) -> float:
        """计算位置相关分数"""
        content = result.get('text', result.get('content', '')).lower()
        
        # 检查查询关键词在内容中的位置
        first_pos = len(content)
        for keyword in query_lower.split():
            if len(keyword) > 2:  # 忽略短词
                pos = content.find(keyword)
                if pos != -1 and pos < first_pos:
                    first_pos = pos
        
        if first_pos == len(content):
            return 0.5
        
        # 越靠前分数越高
        position_ratio = first_pos / max(len(content), 1)
        position_score = 1.0 - position_ratio
        
        return position_score
    
    def _calculate_quality_score(self, result: Dict) -> float:
        """计算文档质量分数"""
        content = result.get('text', result.get('content', ''))
        metadata = result.get('metadata', {})
        
        quality_score = 0.0
        
        # 内容长度评分
        content_length = len(content)
        if 100 <= content_length <= 2000:
            quality_score += 0.4
        elif content_length > 0:
            quality_score += 0.2
        
        # 页面位置评分（年报中前面几页通常是重要摘要）
        page = result.get('page', 0)
        if page <= 5:
            quality_score += 0.2
        elif page <= 20:
            quality_score += 0.1
        
        # 元数据评分
        doc_type = metadata.get('type', '')
        if doc_type in ['executive_summary', '摘要', 'overview']:
            quality_score += 0.2
        elif doc_type in ['financial', '财务报表']:
            quality_score += 0.15
        
        # 完整性评分（检查是否包含完整句子）
        if content and (content.endswith('。') or content.endswith('.') or content.endswith('！') or content.endswith('？')):
            quality_score += 0.2
        
        return min(quality_score, 1.0)


class HybridReranker:
    """混合排序器 - 结合规则排序和通义Rerank"""
    
    def __init__(self, use_tongyi: bool = True):
        """
        初始化混合排序器
        
        Args:
            use_tongyi: 是否优先使用通义rerank
        """
        self.tongyi_reranker = TongyiReranker() if use_tongyi else None
        self.rule_reranker = RuleBasedReranker()
    
    def rerank(self, query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        混合重排序
        
        优先使用通义千问rerank，失败时使用规则排序
        """
        if not results:
            return []
        
        # 优先尝试使用通义rerank
        if self.tongyi_reranker:
            tongyi_results = self.tongyi_reranker.rerank(query, results, top_k)
            if tongyi_results:
                return tongyi_results
        
        # fallback到规则排序
        return self.rule_reranker.rerank(query, results, top_k)


class BusinessReportReranker:
    """针对企业年报的专业重排序器"""
    
    def __init__(self):
        self.hybrid_reranker = HybridReranker(use_tongyi=True)
        self.rule_reranker = RuleBasedReranker(weights={
            'semantic': 0.35,
            'keyword': 0.35,
            'position': 0.15,
            'quality': 0.15
        })
    
    def rerank(self, query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        企业年报专用重排序
        
        结合多种策略：
        1. 首先尝试通义千问rerank
        2. 应用查询类型特殊规则
        3. 基于规则进行二次排序
        """
        if not results:
            return []
        
        # 第一轮：使用混合排序器
        first_round_results = self.hybrid_reranker.rerank(query, results, top_k)
        
        # 第二轮：应用查询类型特殊规则
        final_results = self._apply_query_type_rules(query, first_round_results, top_k)
        
        return final_results
    
    def _classify_query(self, query: str) -> str:
        """分类查询类型"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['区别', '不同', '差异', '比较', '对比']):
            return 'comparison'
        if any(word in query_lower for word in ['多少', '数值', '金额', '计算', '公式']):
            return 'calculation'
        if any(word in query_lower for word in ['什么', '定义', '概念', '是']):
            return 'definition'
        if any(word in query_lower for word in ['变化', '趋势', '增长', '下降', '同比']):
            return 'trend'
        if any(word in query_lower for word in ['风险', '挑战', '不确定性']):
            return 'risk'
        
        return 'general'
    
    def _apply_query_type_rules(self, query: str, results: List[Dict], top_k: int) -> List[Dict]:
        """应用查询类型特殊规则"""
        query_type = self._classify_query(query)
        
        # 查询类型特定关键词
        type_keywords = {
            'comparison': ['差异', '区别', '比较', '对比', '不同'],
            'calculation': ['金额', '数值', '比例', '比率', '率', '计算'],
            'definition': ['定义', '概念', '包括', '包含', '含义'],
            'trend': ['增长', '下降', '变化', '趋势', '同比', '环比'],
            'risk': ['风险', '挑战', '威胁', '不确定性', '隐患']
        }
        
        # 为每条结果计算特殊分数
        for result in results:
            content = result.get('text', result.get('content', '')).lower()
            bonus = 0.0
            
            # 根据查询类型应用特殊规则
            if query_type in type_keywords:
                for keyword in type_keywords[query_type]:
                    if keyword in query.lower():
                        # 如果关键词在查询中，检查是否在结果中
                        if keyword in content:
                            bonus += 0.15
            
            # 财务指标特殊处理
            financial_keywords = ['毛利率', '净利率', '资产负债率', 'ROE', 'EPS', '营收']
            for kw in financial_keywords:
                if kw in query.lower() and kw in content:
                    bonus += 0.1
            
            # 应用特殊分数
            base_score = result.get('rerank_score', 0.5)
            result['rerank_score'] = base_score * 0.8 + bonus * 0.2
        
        # 重新排序
        results.sort(key=lambda x: x['rerank_score'], reverse=True)
        return results[:top_k]


# 全局实例
_default_reranker = None

def get_business_reranker() -> BusinessReportReranker:
    """获取全局企业年报重排序器实例"""
    global _default_reranker
    if _default_reranker is None:
        _default_reranker = BusinessReportReranker()
    return _default_reranker


def rerank_documents(query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
    """
    便捷函数：对文档进行重排序
    
    Args:
        query: 查询文本
        results: 原始检索结果
        top_k: 返回前k个结果
        
    Returns:
        重排序后的结果
    """
    reranker = get_business_reranker()
    return reranker.rerank(query, results, top_k)
