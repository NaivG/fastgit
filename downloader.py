import os
import zipfile
from tqdm import tqdm
import requests
from loguru import logger

def download_file(url: str, file_path: str, chunk_size: int = 1024, MIN_FILE_SIZE: int = 100) -> bool:
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        if int(MIN_FILE_SIZE) > total_size:
            logger.debug(f"镜像源错误: 文件大小小于{MIN_FILE_SIZE}字节")
            return False
        logger.info(f"下载文件: {file_path} ({total_size/1024:.1f}KB)")

        with open(file_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc="下载文件") as pbar:
                for data in response.iter_content(chunk_size=int(chunk_size)):
                    f.write(data)
                    pbar.update(len(data))
        
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            try:
                zip_ref.testzip()  # 校验文件完整性
            except zipfile.BadZipFile:
                logger.error(f"下载失败: {file_path} 不是一个有效的zip文件")
                os.remove(file_path)
                return False
            
        return True
    except Exception as e:
        logger.error(f"下载失败: {str(e)}")
        return False