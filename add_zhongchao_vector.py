
import os
import sys
import json
import shutil
import faiss
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion import VectorDBIngestor

CHUNK_FILE = PROJECT_ROOT / "data/stock_data/databases/chunked_reports/【财报】中超控股：最近一年的财务报告及其审计报告以及最近一期的财务报告.json"
OUTPUT_DIR = PROJECT_ROOT / "data/stock_data/databases/vector_dbs"

print("=" * 60)
print("开始向量化中超控股财报...")

# 加载已分块的数据
with open(CHUNK_FILE, "r", encoding="utf-8") as f:
    report_data = json.load(f)

sha1 = report_data["metainfo"]["sha1"]
company = report_data["metainfo"]["company_name"]
print(f"公司：{company}")
print(f"SHA1：{sha1}")

# 检查是否已经有现有索引
output_file = OUTPUT_DIR / f"{sha1}.faiss"
if output_file.exists():
    print(f"FAISS索引已存在，跳过")
    exit(0)

# 使用VectorDBIngestor
ingestor = VectorDBIngestor()

# 处理单个报告
index = ingestor._process_report(report_data)

# 确保输出目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# FAISS C++不支持中文路径，先写入当前目录，然后移动
temp_file = f"temp_{sha1}.faiss"
faiss.write_index(index, temp_file)
print(f"已写入临时FAISS索引: {temp_file}")

# 复制到目标目录
shutil.copy(temp_file, str(output_file))
print(f"已复制到: {output_file}")

# 删除临时文件
os.remove(temp_file)

# 验证
verify_index = faiss.read_index(str(output_file))
print(f"验证通过 - 维度: {verify_index.d}, 向量数: {verify_index.ntotal}")

print("\n✓ 向量化完成！")
print("=" * 60)
