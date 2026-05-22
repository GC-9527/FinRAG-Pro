import sys
sys.path.insert(0, 'src')
from pipeline import Pipeline, max_config
from pathlib import Path

print("测试Pipeline初始化...")
try:
    root_path = Path('data/stock_data')
    pipeline = Pipeline(root_path, run_config=max_config)
    print("✅ Pipeline初始化成功")
    
    print("\n测试问题处理...")
    answer = pipeline.answer_single_question("中芯国际的主要业务是什么？", kind="string")
    print("✅ 单问回答成功")
    print("答案:", answer.get('final_answer', 'N/A'))
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()