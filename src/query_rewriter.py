# -*- coding: utf-8 -*-
"""
增强版查询改写模块
集成意图分类、查询扩展和LLM改写功能
参考初会RAG助手的query_rewriter实现，针对企业年报问答场景优化
"""
import json
import os
import dashscope
from typing import List, Dict, Optional, Tuple
from http import HTTPStatus


# 从环境变量获取API密钥
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
dashscope.api_key = DASHSCOPE_API_KEY


class IntentClassifier:
    """增强的意图分类器 - 针对企业年报场景"""
    
    INTENT_PATTERNS = {
        'definition': {
            'keywords': ['是什么', '什么是', '定义', '概念', '含义', '包括', '包含'],
            'weight': 0.9
        },
        'calculation': {
            'keywords': ['计算', '怎么算', '如何算', '多少', '公式', '金额', '总额', '数值'],
            'weight': 0.85
        },
        'comparison': {
            'keywords': ['区别', '不同', '差异', '比较', '对比', '相比', '比较'],
            'weight': 0.8
        },
        'trend': {
            'keywords': ['变化', '增长', '下降', '趋势', '增加', '减少', '同比', '环比'],
            'weight': 0.85
        },
        'reason': {
            'keywords': ['为什么', '原因', '理由', '解释', '说明', '由于'],
            'weight': 0.75
        },
        'procedure': {
            'keywords': ['如何', '怎么做', '步骤', '流程', '方法', '处理'],
            'weight': 0.8
        },
        'risk': {
            'keywords': ['风险', '风险因素', '不确定性', '风险点', '风险管控'],
            'weight': 0.9
        },
        'financial': {
            'keywords': ['收入', '利润', '资产', '负债', '现金流', '财务', '营收', '毛利'],
            'weight': 0.85
        },
        'business': {
            'keywords': ['业务', '主营', '产品', '市场', '客户', '供应商', '经营'],
            'weight': 0.8
        },
        'governance': {
            'keywords': ['治理', '股权', '股东', '董事', '高管', '控制权'],
            'weight': 0.85
        }
    }
    
    @classmethod
    def classify(cls, query: str) -> Tuple[str, float, List[str]]:
        """
        分类查询类型
        
        Returns:
            (主类型, 置信度, 所有匹配的类型列表)
        """
        query_lower = query.lower()
        matched_types = []
        scores = {}
        
        for intent_type, config in cls.INTENT_PATTERNS.items():
            score = 0
            for keyword in config['keywords']:
                if keyword in query_lower:
                    score += config['weight']
                    matched_types.append(intent_type)
            
            if score > 0:
                scores[intent_type] = score
        
        if not scores:
            return 'general', 0.5, ['general']
        
        # 返回得分最高的类型
        main_type = max(scores, key=scores.get)
        max_score = scores[main_type]
        confidence = min(max_score / 1.0, 1.0)
        
        return main_type, confidence, matched_types


class QueryExpander:
    """查询扩展器 - 使用大模型生成相关查询"""
    
    def __init__(self, model: str = "qwen-turbo-latest"):
        self.model = model
    
    def expand(self, query: str, num_variations: int = 2) -> List[str]:
        """
        扩展查询，生成多个变体
        
        Args:
            query: 原始查询
            num_variations: 生成的变体数量
            
        Returns:
            查询变体列表
        """
        prompt = f"""
你是一个查询优化专家。请为以下企业年报查询生成{num_variations}个不同的变体，这些变体应该：
1. 使用不同的表达方式
2. 涵盖不同的角度或方面
3. 保持查询的原始意图

原始查询: {query}

请以JSON数组格式输出，例如：["变体1", "变体2", "变体3"]
"""
        
        try:
            response = self._call_llm(prompt)
            expansions = json.loads(response)
            if isinstance(expansions, list):
                return expansions[:num_variations]
        except Exception as e:
            print(f"查询扩展失败: {e}")
        
        return [query]
    
    def generate_related_queries(self, query: str) -> List[str]:
        """
        生成相关查询
        
        Args:
            query: 原始查询
            
        Returns:
            相关查询列表
        """
        prompt = f"""
基于以下企业年报查询，生成5个相关的子查询或补充查询：

原始查询: {query}

这些查询应该：
1. 涵盖查询的不同方面
2. 包括相关的概念和术语
3. 提出具体的子问题

请以JSON数组格式输出。
"""
        
        try:
            response = self._call_llm(prompt)
            queries = json.loads(response)
            if isinstance(queries, list):
                return queries[:5]
        except Exception as e:
            print(f"相关查询生成失败: {e}")
        
        return [query]
    
    def _call_llm(self, prompt: str) -> str:
        """调用大模型"""
        messages = [{"role": "user", "content": prompt}]
        response = dashscope.Generation.call(
            model=self.model,
            messages=messages,
            result_format='message',
            temperature=0.7,
        )
        
        if response.status_code == HTTPStatus.OK:
            return response.output.choices[0].message.content
        else:
            raise Exception(f"LLM调用失败: {response.message}")


class EnhancedQueryRewriter:
    """增强版查询改写器 - 针对企业年报问答场景"""
    
    def __init__(self, use_expansion: bool = True):
        """
        初始化增强版查询改写器
        
        Args:
            use_expansion: 是否使用查询扩展
        """
        self.classifier = IntentClassifier()
        self.expander = QueryExpander()
        self.use_expansion = use_expansion
    
    def rewrite(self, query: str, context: str = "") -> Dict:
        """
        改写查询
        
        Args:
            query: 原始查询
            context: 对话上下文
            
        Returns:
            包含改写结果和元数据的字典
        """
        # 1. 意图分类
        intent, confidence, matched_intents = self.classifier.classify(query)
        
        # 2. 使用大模型进行智能改写
        rewritten_query = self._llm_rewrite(query, intent, context)
        
        # 3. 生成查询变体（如果启用）
        variations = []
        if self.use_expansion:
            variations = self.expander.expand(query, num_variations=2)
        
        # 4. 准备结果
        result = {
            'original_query': query,
            'rewritten_query': rewritten_query,
            'intent': intent,
            'confidence': confidence,
            'matched_intents': matched_intents,
            'variations': variations
        }
        
        return result
    
    def _llm_rewrite(self, query: str, intent: str, context: str) -> str:
        """使用大模型改写查询"""
        
        intent_prompts = {
            'definition': "将查询改写成一个明确的定义性问题，例如：'请解释公司X的主营业务是什么'",
            'calculation': "将查询改写成一个具体的计算问题，例如：'X公司2024年的营业收入是多少，增长了多少'",
            'comparison': "将查询改写成一个清晰的对比性问题，例如：'请比较A公司和B公司在某方面的差异'",
            'trend': "将查询改写成一个趋势分析问题，例如：'分析X公司近几年的收入变化趋势'",
            'reason': "将查询改写成一个解释性问题，例如：'请解释X公司为什么出现这种情况'",
            'procedure': "将查询改写成一个步骤性问题，例如：'X公司的风险管理流程是'",
            'risk': "将查询改写成一个风险分析问题，例如：'分析X公司面临的主要风险因素'",
            'financial': "将查询改写成一个财务分析问题，例如：'X公司的财务状况如何'",
            'business': "将查询改写成一个业务分析问题，例如：'X公司的主要业务构成是什么'",
            'governance': "将查询改写成一个治理分析问题，例如：'X公司的治理结构如何'",
            'general': "将查询改写成一个清晰、直接的问题"
        }
        
        instruction = intent_prompts.get(intent, intent_prompts['general'])
        
        prompt = f"""
你是一个查询优化专家。请根据以下指令改写用户的查询。

### 改写要求 ###
{instruction}

### 原始查询 ###
{query}

### 对话上下文 ###
{context if context else "无"}

### 改写后的查询 ###
请只输出改写后的查询，不要其他内容。
"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = dashscope.Generation.call(
                model="qwen-turbo-latest",
                messages=messages,
                result_format='message',
                temperature=0,
            )
            
            if response.status_code == HTTPStatus.OK:
                rewritten = response.output.choices[0].message.content.strip()
                return rewritten if rewritten else query
        except Exception as e:
            print(f"LLM改写失败: {e}")
        
        return query
    
    def batch_rewrite(self, queries: List[str]) -> List[Dict]:
        """
        批量改写查询
        
        Args:
            queries: 查询列表
            
        Returns:
            改写结果列表
        """
        return [self.rewrite(q) for q in queries]


class SmartQueryRewriter(EnhancedQueryRewriter):
    """智能查询改写器 - EnhancedQueryRewriter的别名"""
    
    def auto_rewrite(self, query: str, use_expansion: bool = False) -> Dict:
        """
        自动查询改写
        
        Args:
            query: 原始查询
            use_expansion: 是否使用查询扩展
            
        Returns:
            包含改写结果的字典
        """
        result = self.rewrite(query, "")
        
        if use_expansion and result.get('variations'):
            return {
                'rewritten_query': result['rewritten_query'],
                'query_type': result['intent'],
                'confidence': result['confidence'],
                'variations': result['variations']
            }
        
        return {
            'rewritten_query': result['rewritten_query'],
            'query_type': result['intent'],
            'confidence': result['confidence']
        }


# 全局实例，供其他模块使用
_default_rewriter = None

def get_query_rewriter() -> SmartQueryRewriter:
    """获取全局查询改写器实例"""
    global _default_rewriter
    if _default_rewriter is None:
        _default_rewriter = SmartQueryRewriter()
    return _default_rewriter


def rewrite_query(query: str, use_expansion: bool = False) -> Dict:
    """
    便捷函数：改写单个查询
    
    Args:
        query: 原始查询
        use_expansion: 是否使用查询扩展
        
    Returns:
        改写结果字典
    """
    rewriter = get_query_rewriter()
    return rewriter.auto_rewrite(query, use_expansion=use_expansion)
