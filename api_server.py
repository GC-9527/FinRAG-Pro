# -*- coding: utf-8 -*-
"""
RAG-cy FastAPI 后端服务
提供 REST API 供前端调用
"""
import sys
import os
import json
import uuid
import time
import asyncio
import csv
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 将当前目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import Pipeline, enhanced_config, RunConfig
from src.questions_processing import QuestionsProcessor

# --- FastAPI 应用 ---
app = FastAPI(title="RAG-cy API", version="1.0.0")

# CORS 允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 全局状态 ---
ROOT_PATH = Path("data/stock_data")

# 默认使用 enhanced_config
_pipeline: Optional[Pipeline] = None
_current_config: Optional[RunConfig] = None

# 会话存储 (简易内存存储)
_sessions: dict = {}


def get_pipeline() -> Pipeline:
    global _pipeline, _current_config
    if _pipeline is None:
        _current_config = enhanced_config
        _pipeline = Pipeline(ROOT_PATH, run_config=_current_config)
    return _pipeline


def update_config(use_query_rewrite: bool, use_enhanced_reranker: bool):
    global _pipeline, _current_config
    _current_config = RunConfig(
        use_serialized_tables=False,
        parent_document_retrieval=True,
        llm_reranking=False,
        parallel_requests=1,
        submission_file=False,
        pipeline_details="API Enhanced RAG",
        answering_model="qwen-turbo-latest",
        config_suffix="_api",
        use_query_rewrite=use_query_rewrite,
        use_enhanced_reranker=use_enhanced_reranker,
    )
    _pipeline = Pipeline(ROOT_PATH, run_config=_current_config)


def get_pipeline_with_options(use_qr: bool, use_rr: bool) -> Pipeline:
    """获取指定配置的 Pipeline，不会影响全局状态"""
    config = RunConfig(
        use_serialized_tables=False,
        parent_document_retrieval=True,
        llm_reranking=False,
        parallel_requests=1,
        submission_file=False,
        pipeline_details="API On-Demand RAG",
        answering_model="qwen-turbo-latest",
        config_suffix="_api_ondemand",
        use_query_rewrite=use_qr,
        use_enhanced_reranker=use_rr,
    )
    return Pipeline(ROOT_PATH, run_config=config)


# --- 请求/响应模型 ---
class ChatResponse(BaseModel):
    session_id: str = Field(..., description="会话ID")
    question: str = Field(..., description="原始问题")
    final_answer: str = Field("", description="最终答案")
    step_by_step_analysis: str = Field("", description="分步分析")
    reasoning_summary: str = Field("", description="推理摘要")
    references: list = Field(default_factory=list, description="引用列表")
    search_results: list = Field(default_factory=list, description="检索结果")
    query_rewrite_info: Optional[dict] = Field(None, description="查询改写信息")
    search_time: float = Field(0, description="检索耗时(秒)")
    total_time: float = Field(0, description="总耗时(秒)")


class StreamChatRequest(BaseModel):
    question: str = Field(..., description="用户问题")
    session_id: Optional[str] = Field(None, description="会话ID，不传则新建")
    kind: str = Field("string", description="答案类型: string/number/boolean/names")
    use_query_rewrite: Optional[bool] = Field(None, description="是否启用查询改写，None=使用全局默认")
    use_enhanced_reranker: Optional[bool] = Field(None, description="是否启用增强重排序，None=使用全局默认")
    company_name: Optional[str] = Field(None, description="指定公司名称，绕过自动识别")


class ChatRequest(BaseModel):
    question: str = Field(..., description="用户问题")
    session_id: Optional[str] = Field(None, description="会话ID，不传则新建")
    kind: str = Field("string", description="答案类型: string/number/boolean/names")
    use_query_rewrite: Optional[bool] = Field(None, description="是否启用查询改写，None=使用全局默认")
    use_enhanced_reranker: Optional[bool] = Field(None, description="是否启用增强重排序，None=使用全局默认")
    company_name: Optional[str] = Field(None, description="指定公司名称，绕过自动识别")


class ConfigResponse(BaseModel):
    use_query_rewrite: bool
    use_enhanced_reranker: bool


class ConfigUpdateRequest(BaseModel):
    use_query_rewrite: bool = True
    use_enhanced_reranker: bool = True


# --- API 端点 ---
@app.get("/api/health")
def health_check():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/config")
def get_config():
    """获取当前配置"""
    global _current_config
    if _current_config is None:
        _current_config = enhanced_config
    return ConfigResponse(
        use_query_rewrite=_current_config.use_query_rewrite,
        use_enhanced_reranker=_current_config.use_enhanced_reranker,
    )


@app.post("/api/config")
def set_config(req: ConfigUpdateRequest):
    """更新配置"""
    update_config(req.use_query_rewrite, req.use_enhanced_reranker)
    return {
        "status": "ok",
        "use_query_rewrite": req.use_query_rewrite,
        "use_enhanced_reranker": req.use_enhanced_reranker,
    }


@app.get("/api/companies")
def list_companies():
    """获取可用公司列表（从 subset.csv 读取）"""
    subset_path = ROOT_PATH / "subset.csv"
    companies = []
    if subset_path.exists():
        with open(subset_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            seen = set()
            for row in reader:
                name = row.get("company_name", "").strip()
                if name and name not in seen:
                    seen.add(name)
                    companies.append({
                        "name": name,
                        "files": [],
                    })
            # 补充文件信息
            f.seek(0)
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("company_name", "").strip()
                file_name = row.get("file_name", "").strip()
                for c in companies:
                    if c["name"] == name and file_name:
                        c["files"].append(file_name)
    return {"companies": companies, "count": len(companies)}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    问答接口：接收问题，返回结构化答案
    支持动态覆盖 query_rewrite 和 enhanced_reranker 设置
    """
    try:
        t0 = time.time()

        # 确定实际使用的参数
        use_qr = req.use_query_rewrite
        use_rr = req.use_enhanced_reranker

        # 如果请求中没指定，使用全局配置
        if use_qr is None or use_rr is None:
            global _current_config
            cfg = _current_config or enhanced_config
            if use_qr is None:
                use_qr = cfg.use_query_rewrite
            if use_rr is None:
                use_rr = cfg.use_enhanced_reranker

        # 使用指定配置的 Pipeline
        pipeline = get_pipeline_with_options(use_qr, use_rr)

        # 生成或获取 session_id
        session_id = req.session_id or str(uuid.uuid4())

        answer_dict = pipeline.answer_single_question(req.question, kind=req.kind, company_name=req.company_name)
        total_time = time.time() - t0

        # 解析答案结构
        content = answer_dict.get("content", answer_dict)
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                content = {"final_answer": content}

        final_answer = content.get("final_answer", "")
        step_by_step = content.get("step_by_step_analysis", "")
        reasoning_summary = content.get("reasoning_summary", "")

        # 提取查询改写信息
        query_rewrite_info = answer_dict.get("query_rewrite_info", None)

        # --- 从 answer_dict 中提取实际检索到的文档作为引用和搜索结果 ---
        references = []
        search_results = []

        # 尝试从 answer_dict 获取实际检索结果
        retrieval_results = answer_dict.get("retrieval_results", [])
        if not retrieval_results:
            # 尝试从 content 获取
            retrieval_results = content.get("retrieval_results", [])

        if retrieval_results:
            for i, r in enumerate(retrieval_results[:5], 1):
                text = r.get("text", r.get("content", ""))
                page = r.get("page", 0)
                lines = r.get("lines", [])
                score = r.get("score", r.get("rerank_score", r.get("similarity", r.get("distance", 0))))
                similarity_pct = r.get("similarity_pct", "")
                
                # 处理score: 若是字符串则转换
                if isinstance(score, str):
                    try:
                        score = float(score.replace("%", "")) / 100.0
                    except Exception:
                        score = 0.0
                elif isinstance(score, (int, float)) and score > 1:
                    score = score / 100.0
                
                # 构建引用标签：优先用行号，其次用页码
                if lines and len(lines) >= 2:
                    ref_label = f"L.{lines[0]}-{lines[1]}"
                elif page and page > 0:
                    ref_label = f"P.{page}"
                else:
                    ref_label = f"结果 {i}"
                
                search_results.append({
                    "id": str(i),
                    "index": i,
                    "score": round(float(score), 4),
                    "relevance_score": round(float(score), 4),
                    "similarity_pct": similarity_pct or f"{score * 100:.1f}%",
                    "page": page,
                    "lines": lines,
                    "content": text[:300],
                    "text": text[:300],
                })

                references.append({
                    "page": page,
                    "lines": lines,
                    "title": f"检索结果 {i} ({ref_label})",
                    "score": round(float(score), 4),
                    "similarity_pct": similarity_pct or f"{score * 100:.1f}%",
                    "content": text[:200],
                    "text": text[:200],
                })

        # 如果没有 retrieval_results，用 api_requests 返回的 pages 作为引用
        if not references:
            relevant_pages = answer_dict.get("relevant_pages", content.get("relevant_pages", []))
            api_refs = answer_dict.get("references", [])
            for i, p in enumerate(relevant_pages[:5], 1):
                references.append({
                    "page": p if isinstance(p, (int, float)) else p.get("page", 0),
                    "title": f"相关页面 {i}",
                    "score": 0,
                    "content": "",
                })
            if not references and api_refs:
                references = api_refs

        # 保存会话
        _sessions[session_id] = {
            "question": req.question,
            "answer": final_answer,
            "timestamp": datetime.now().isoformat(),
        }

        return ChatResponse(
            session_id=session_id,
            question=req.question,
            final_answer=final_answer,
            step_by_step_analysis=step_by_step,
            reasoning_summary=reasoning_summary,
            references=references,
            search_results=search_results,
            query_rewrite_info=query_rewrite_info,
            search_time=0,
            total_time=round(total_time, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(req: StreamChatRequest):
    """
    流式问答接口：通过 SSE 逐事件发送答案内容，实现打字机效果
    事件类型：search_results, step_by_step, reasoning_summary, chunk, done, error
    """

    async def event_generator():
        try:
            # 1. 确定实际使用的参数
            use_qr = req.use_query_rewrite
            use_rr = req.use_enhanced_reranker

            # 如果请求中没指定，使用全局配置
            if use_qr is None or use_rr is None:
                global _current_config
                cfg = _current_config or enhanced_config
                if use_qr is None:
                    use_qr = cfg.use_query_rewrite
                if use_rr is None:
                    use_rr = cfg.use_enhanced_reranker

            # 使用指定配置的 Pipeline
            pipeline = get_pipeline_with_options(use_qr, use_rr)
            session_id = req.session_id or str(uuid.uuid4())
            
            t0 = time.time()
            answer_dict = pipeline.answer_single_question(req.question, kind=req.kind, company_name=req.company_name)
            total_time = time.time() - t0

            # 解析答案结构
            content = answer_dict.get("content", answer_dict)
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except Exception:
                    content = {"final_answer": content}

            final_answer = content.get("final_answer", "")
            step_by_step = content.get("step_by_step_analysis", "")
            reasoning_summary = content.get("reasoning_summary", "")
            query_rewrite_info = answer_dict.get("query_rewrite_info", None)

            # 2. 构建 search_results（与 /api/chat 完全一致的逻辑）
            search_results = []
            retrieval_results = answer_dict.get("retrieval_results", [])
            if not retrieval_results:
                retrieval_results = content.get("retrieval_results", [])

            if retrieval_results:
                for i, r in enumerate(retrieval_results[:5], 1):
                    text = r.get("text", r.get("content", ""))
                    page = r.get("page", 0)
                    lines = r.get("lines", [])
                    score = r.get("score", r.get("rerank_score", r.get("similarity", r.get("distance", 0))))
                    similarity_pct = r.get("similarity_pct", "")

                    # 处理score: 若是字符串则转换
                    if isinstance(score, str):
                        try:
                            score = float(score.replace("%", "")) / 100.0
                        except Exception:
                            score = 0.0
                    elif isinstance(score, (int, float)) and score > 1:
                        score = score / 100.0

                    search_results.append({
                        "id": str(i),
                        "index": i,
                        "score": round(float(score), 4),
                        "relevance_score": round(float(score), 4),
                        "similarity_pct": similarity_pct or f"{score * 100:.1f}%",
                        "page": page,
                        "lines": lines,
                        "content": text[:300],
                        "text": text[:300],
                    })

            # 3. 发送检索结果
            yield f"event: search_results\ndata: {json.dumps({'search_results': search_results}, ensure_ascii=False)}\n\n"

            # 4. 发送分步推理
            yield f"event: step_by_step\ndata: {json.dumps({'step_by_step_analysis': step_by_step}, ensure_ascii=False)}\n\n"

            # 5. 发送推理摘要
            yield f"event: reasoning_summary\ndata: {json.dumps({'reasoning_summary': reasoning_summary}, ensure_ascii=False)}\n\n"

            # 6. 流式发送 final_answer（模拟打字机效果，按字符分块发送）
            if final_answer:
                chunk_size = 3  # 每次发送3个字符
                for i in range(0, len(final_answer), chunk_size):
                    chunk = final_answer[i:i + chunk_size]
                    yield f"event: chunk\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.03)  # 30ms 延迟模拟打字机效果

            # 7. 发送完成事件（包含所有元数据）
            query_rewrite_info_data = None
            if query_rewrite_info:
                query_rewrite_info_data = query_rewrite_info

            done_data = {
                "session_id": session_id,
                "question": req.question,
                "final_answer": final_answer,
                "step_by_step_analysis": step_by_step,
                "reasoning_summary": reasoning_summary,
                "query_rewrite_info": query_rewrite_info_data,
                "search_results": search_results,
                "total_time": round(total_time, 2),
            }
            yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"

            # 8. 保存会话
            _sessions[session_id] = {
                "question": req.question,
                "answer": final_answer,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/conversations")
def list_conversations():
    """列出所有会话"""
    conversations = []
    for sid, data in _sessions.items():
        conversations.append({
            "id": sid,
            "title": data["question"][:30] + ("..." if len(data["question"]) > 30 else ""),
            "lastMessage": data["answer"][:40] + ("..." if len(data["answer"]) > 40 else ""),
            "timestamp": data["timestamp"][:16],
        })
    return conversations


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")