
import json
import os

# 读取分块文件
chunk_file = 'data/stock_data/databases/chunked_reports/【财报】中超控股：最近一年的财务报告及其审计报告以及最近一期的财务报告.json'
with open(chunk_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

chunks = data['content']['chunks']
total_chars = 0
non_empty_chunks = 0
chunk_info = []

for i, chunk in enumerate(chunks):
    text = chunk['text']
    text_len = len(text)
    if text.strip():
        non_empty_chunks += 1
        total_chars += text_len
    chunk_info.append((i+1, text_len, chunk['lines']))

print('=== 中超控股分块统计 ===')
print(f'总分块数: {len(chunks)}')
print(f'非空分块数: {non_empty_chunks}')
print(f'总字符数: {total_chars:,}')
print()
print('前20块详情:')
for info in chunk_info[:20]:
    print(f'块{info[0]}: {info[1]:,}字符, 行{info[2]}')
print('...')
print()
print('最后10块详情:')
for info in chunk_info[-10:]:
    print(f'块{info[0]}: {info[1]:,}字符, 行{info[2]}')

# 检查原Markdown
md_file = 'data/stock_data/debug_data/03_reports_markdown/【财报】中超控股：最近一年的财务报告及其审计报告以及最近一期的财务报告.md'
if os.path.exists(md_file):
    print()
    print('=== 原始Markdown统计 ===')
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    print(f'原始Markdown字符数: {len(md_content):,}')
    print(f'总行数: {len(md_content.splitlines()):,}')
