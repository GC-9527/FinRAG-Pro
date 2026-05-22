import requests
import time
import zipfile
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("MINERU_API_KEY", "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI0ODgwMDQ4MCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3OTMyOTc3MiwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiZTlkZWY1ZTEtNzA4ZS00MzY3LTg4ZjktZGZmMjlhMjNlNDMyIiwiZW1haWwiOiIiLCJleHAiOjE3ODcxMDU3NzJ9.pwTffUq_ulDPGzbdezZGEEfk3iAevisT4i2FfWYd6mHxS03GoeGxVkLSCXT30K-NLv4f0pCVV9oMjDHNZTPHXA")

def get_task_id(file_name, pdf_url=None):
    """
    使用 Mineru Precision Extract API (v4) 获取任务ID
    :param file_name: PDF文件名（用于记录）
    :param pdf_url: PDF文件的远程URL，如果提供则使用该URL
    :return: task_id
    """
    url = 'https://mineru.net/api/v4/extract/task'
    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Bearer {api_key}"
    }
    
    if pdf_url:
        print(f"使用Precision Extract API解析URL: {pdf_url}")
        data = {
            'url': pdf_url,
            'is_ocr': True,
            'enable_formula': False,
            'model_version': 'vlm'
        }
    else:
        pdf_url = 'https://vl-image.oss-cn-shanghai.aliyuncs.com/pdf/' + file_name
        print(f"使用Precision Extract API解析URL: {pdf_url}")
        data = {
            'url': pdf_url,
            'is_ocr': True,
            'enable_formula': False,
            'model_version': 'vlm'
        }

    print(f"正在请求Mineru Precision Extract API解析...")
    res = requests.post(url, headers=headers, json=data)
    print(f"API响应状态: {res.status_code}")
    
    if res.status_code == 200:
        result = res.json()
        print(f"API响应: {result}")
        if result.get("code") == 0:
            return result["data"]['task_id']
        else:
            raise ValueError(f"API错误: {result.get('msg', '未知错误')}")
    else:
        raise ValueError(f"API请求失败: {res.status_code} - {res.text}")

def get_result(task_id):
    """
    查询任务结果（Precision Extract API v4）
    :param task_id: 任务ID
    """
    url = f'https://mineru.net/api/v4/extract/task/{task_id}'
    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Bearer {api_key}"
    }

    while True:
        res = requests.get(url, headers=headers)
        print(f"查询响应状态: {res.status_code}")
        
        if res.status_code != 200:
            print(f"查询失败: {res.status_code} - {res.text}")
            return
        
        try:
            result = res.json()
        except:
            print(f"响应不是JSON格式: {res.text}")
            return
            
        if result.get("code") != 0:
            print(f"查询错误: {result.get('msg', '未知错误')}")
            return
            
        data = result.get("data", {})
        print(f"任务状态数据: {data}")
        
        state = data.get('state')
        err_msg = data.get('err_msg', '')
        
        # 如果任务还在进行中，等待后重试
        if state in ['pending', 'running', 'converting']:
            progress = data.get('extract_progress', {})
            extracted = progress.get('extracted_pages', 0)
            total = progress.get('total_pages', 0)
            print(f"任务进行中 ({state}): {extracted}/{total} 页，等待5秒后重试...")
            time.sleep(5)
            continue
        
        # 如果有错误，输出错误信息
        if err_msg:
            print(f"任务出错: {err_msg}")
            return
        
        # 如果任务完成，下载文件
        if state == 'done':
            full_zip_url = data.get('full_zip_url')
            if full_zip_url:
                local_filename = f"{task_id}.zip"
                print(f"开始下载: {full_zip_url}")
                r = requests.get(full_zip_url, stream=True)
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"下载完成，已保存到: {local_filename}")
                # 下载完成后自动解压
                unzip_file(local_filename)
            else:
                print("未找到 full_zip_url，无法下载。")
            return
        
        # 其他未知状态
        print(f"未知状态: {state}")
        return

def unzip_file(zip_path, extract_dir=None):
    """
    解压指定的zip文件到目标文件夹。
    :param zip_path: zip文件路径
    :param extract_dir: 解压目标文件夹，默认为zip同名目录
    """
    if extract_dir is None:
        extract_dir = zip_path.rstrip('.zip')
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"已解压到: {extract_dir}")

if __name__ == "__main__":
    file_name = '【财报】中芯国际：中芯国际2024年年度报告_part3.pdf'
    pdf_url = 'https://rag-1.oss-cn-shanghai.aliyuncs.com/%E3%80%90%E8%B4%A2%E6%8A%A5%E3%80%91%E4%B8%AD%E8%8A%AF%E5%9B%BD%E9%99%85%EF%BC%9A%E4%B8%AD%E8%8A%AF%E5%9B%BD%E9%99%852024%E5%B9%B4%E5%B9%B4%E5%BA%A6%E6%8A%A5%E5%91%8A_part3.pdf'
    
    print(f"开始处理: {file_name}")
    print(f"使用URL: {pdf_url}")
    print("使用Mineru Precision Extract API (v4)")
    
    task_id = get_task_id(file_name, pdf_url)
    print(f"获取到task_id: {task_id}")
    
    get_result(task_id)