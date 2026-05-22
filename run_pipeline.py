import sys
from pathlib import Path
from src.pipeline import Pipeline, max_config

print("=" * 50)
print("开始运行 Pipeline")
print("=" * 50)

# 设置数据集根目录
root_path = Path("data/stock_data")
print(f'root_path: {root_path}')

# 初始化主流程，使用推荐的最佳配置
pipeline = Pipeline(root_path, run_config=max_config)

print("\n步骤1：将规整后报告分块，便于后续向量化")
print("-" * 50)
pipeline.chunk_reports() 

print("\n步骤2：从分块报告创建向量数据库")
print("-" * 50)
pipeline.create_vector_dbs()     

print("\n" + "=" * 50)
print("完成！")
print("=" * 50)
