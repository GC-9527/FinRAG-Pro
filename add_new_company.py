# -*- coding: utf-8 -*-
"""
新公司财报入库脚本：
1. 使用 MinerU API 解析 PDF URL -> 生成 markdown
2. 更新 subset.csv
3. 对 markdown 进行分块（chunk）
4. 创建/更新向量数据库（FAISS）
"""
import os
import sys
import csv
import hashlib
import shutil
from pathlib import Path

# 将项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import pdf_mineru
from src.text_splitter import TextSplitter
from src.ingestion import VectorDBIngestor


def add_new_company_to_kb(
    pdf_url: str,
    file_name: str,
    company_name: str,
    data_dir: str = "data/stock_data",
):
    """
    完整的入库流程：
    - pdf_url: PDF 文件的远程 URL
    - file_name: PDF 文件名（如 '【财报】中超控股：xxx.pdf'）
    - company_name: 公司名称（如 '中超控股'）
    - data_dir: 相对于项目根目录的数据目录
    """
    root = PROJECT_ROOT / data_dir
    pdf_reports_dir = root / "pdf_reports"
    reports_md_dir = root / "debug_data" / "03_reports_markdown"
    documents_dir = root / "databases" / "chunked_reports"
    vector_db_dir = root / "databases" / "vector_dbs"
    subset_csv_path = root / "subset.csv"

    # 确保目录存在
    pdf_reports_dir.mkdir(parents=True, exist_ok=True)
    reports_md_dir.mkdir(parents=True, exist_ok=True)
    documents_dir.mkdir(parents=True, exist_ok=True)
    vector_db_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"开始处理新公司: {company_name}")
    print(f"文件名: {file_name}")
    print(f"PDF URL: {pdf_url}")
    print("=" * 60)

    # =====================================================
    # 步骤1: 使用 MinerU API 解析 PDF -> markdown
    # =====================================================
    import time as _time

    print("\n[步骤1] 使用 MinerU Precision Extract API 解析 PDF...")
    task_id = pdf_mineru.get_task_id(file_name, pdf_url=pdf_url)
    print(f"获取到 task_id: {task_id}")

    # 带重试的轮询，防止网络闪断
    max_retries = 5
    for attempt in range(max_retries):
        try:
            pdf_mineru.get_result(task_id)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 10
                print(f"轮询时网络出错: {e}，{wait}秒后重试... (尝试 {attempt+2}/{max_retries})")
                _time.sleep(wait)
            else:
                raise

    # 解压后 markdown 文件位于当前目录 {task_id}/full.md
    extract_dir = Path(f"{task_id}")
    md_source = extract_dir / "full.md"
    if not md_source.exists():
        raise FileNotFoundError(f"MinerU 解析失败，未找到 markdown 文件: {md_source}")

    # 移动到 reports_markdown 目录
    base_name = os.path.splitext(file_name)[0]
    md_target = reports_md_dir / f"{base_name}.md"
    shutil.move(str(md_source), str(md_target))
    print(f"Markdown 已保存到: {md_target}")

    # 清理临时文件
    zip_file = Path(f"{task_id}.zip")
    if zip_file.exists():
        zip_file.unlink()
    if extract_dir.exists():
        shutil.rmtree(str(extract_dir), ignore_errors=True)
    print("临时文件已清理")

    # =====================================================
    # 步骤2: 更新 subset.csv
    # =====================================================
    print("\n[步骤2] 更新 subset.csv...")
    # 生成 sha1
    sha1 = hashlib.sha1(company_name.encode()).hexdigest()[:10]

    # 读取现有数据
    existing_rows = []
    if subset_csv_path.exists():
        with open(subset_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_rows.append(row)

    # 检查是否已存在
    already_exists = any(
        row.get("file_name", "").strip() == file_name for row in existing_rows
    )
    if not already_exists:
        existing_rows.append({
            "sha1": sha1,
            "file_name": file_name,
            "company_name": company_name,
        })
        with open(subset_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sha1", "file_name", "company_name"])
            writer.writeheader()
            writer.writerows(existing_rows)
        print(f"已添加 {company_name} 到 subset.csv (sha1={sha1})")
    else:
        print(f"{company_name} 已存在于 subset.csv，跳过")

    # =====================================================
    # 步骤3: 对 markdown 进行分块
    # =====================================================
    print("\n[步骤3] 对 markdown 进行分块...")
    text_splitter = TextSplitter()
    text_splitter.split_markdown_reports(
        all_md_dir=reports_md_dir,
        output_dir=documents_dir,
        chunk_size=30,
        chunk_overlap=5,
        subset_csv=subset_csv_path,
    )
    print(f"分块完成，输出目录: {documents_dir}")

    # =====================================================
    # 步骤4: 创建向量数据库
    # =====================================================
    print("\n[步骤4] 创建/更新向量数据库...")
    vdb_ingestor = VectorDBIngestor()
    vdb_ingestor.process_reports(
        all_reports_dir=documents_dir,
        output_dir=vector_db_dir,
    )
    print(f"向量数据库已更新，输出目录: {vector_db_dir}")

    # =====================================================
    # 完成
    # =====================================================
    print("\n" + "=" * 60)
    print(f"入库完成！公司 '{company_name}' 已成功加入知识库")
    print(f"- Markdown: {md_target}")
    print(f"- Chunk JSON: {documents_dir / (base_name + '.json')}")
    print(f"- FAISS Index: {vector_db_dir / (sha1 + '.faiss')}")
    print("=" * 60)


if __name__ == "__main__":
    PDF_URL = (
        "https://rag-1.oss-cn-shanghai.aliyuncs.com/"
        "%E8%B4%A2%E5%8A%A1%E6%8A%A5%E5%91%8A/"
        "%E4%B8%AD%E8%B6%85%E6%8E%A7%E8%82%A1%EF%BC%9A"
        "%E6%9C%80%E8%BF%91%E4%B8%80%E5%B9%B4%E7%9A%84%E8%B4%A2%E5%8A%A1%E6%8A%A5%E5%91%8A"
        "%E5%8F%8A%E5%85%B6%E5%AE%A1%E8%AE%A1%E6%8A%A5%E5%91%8A%E4%BB%A5%E5%8F%8A"
        "%E6%9C%80%E8%BF%91%E4%B8%80%E6%9C%9F%E7%9A%84%E8%B4%A2%E5%8A%A1%E6%8A%A5%E5%91%8A.pdf"
    )
    FILE_NAME = "【财报】中超控股：最近一年的财务报告及其审计报告以及最近一期的财务报告.pdf"
    COMPANY_NAME = "中超控股"

    add_new_company_to_kb(
        pdf_url=PDF_URL,
        file_name=FILE_NAME,
        company_name=COMPANY_NAME,
    )