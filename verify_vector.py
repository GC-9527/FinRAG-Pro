
import json
import faiss
import numpy as np
import os

print('=== 验证中超控股向量化 ===')
print()

# 1. 检查chunk文件
chunk_file = 'data/stock_data/databases/chunked_reports/【财报】中超控股：最近一年的财务报告及其审计报告以及最近一期的财务报告.json'
with open(chunk_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

chunks = data['content']['chunks']
print(f'分块文件中的块数: {len(chunks)}')

# 统计非空文本块
text_chunks = []
for chunk in chunks:
    text = chunk['text'][:2048]  # 和ingestion.py一样，截断到2048字符
    if text.strip():
        text_chunks.append(text)

print(f'向量化时实际处理的非空块数: {len(text_chunks)}')
print()

# 2. 检查FAISS索引
faiss_path = 'data/stock_data/databases/vector_dbs/40ebc7089e.faiss'
if os.path.exists(faiss_path):
    index = faiss.read_index(faiss_path)
    print('=== FAISS索引信息 ===')
    print(f'向量维度: {index.d}')
    print(f'索引中向量数: {index.ntotal}')
    
    # 对比一下
    if index.ntotal == len(text_chunks):
        print('✅ 成功！所有块都已向量化')
    elif index.ntotal == 0:
        print('❌ 索引是空的！')
    elif index.ntotal < len(text_chunks):
        print(f'⚠️ 只向量化了 {index.ntotal}/{len(text_chunks)} 块')
    else:
        print(f'❌ 异常！索引中有 {index.ntotal} 个向量，但应该是 {len(text_chunks)}')

else:
    print(f'❌ FAISS索引文件不存在: {faiss_path}')
