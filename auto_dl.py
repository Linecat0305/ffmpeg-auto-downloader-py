import json
import subprocess
import os
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import re
import sys
import requests
from bs4 import BeautifulSoup
import json

class StreamDownloader:
    def __init__(self, json_path: str, max_workers: int = 3):
        """
        初始化下載器
        :param json_path: JSON檔案路徑
        :param max_workers: 最大並行下載數
        """
        self.json_path = json_path
        self.output_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'Course')
        self.subtitle_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'st.vtt')
        self.max_workers = max_workers
        self.setup_logging()
        
        for directory in [self.output_dir, self.subtitle_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"創建目錄: {directory}")

    def extract_urls(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        從網頁中提取source URL和caption URL
        :param url: 原始URL
        :return: (source URL, caption URL) 或 (None, None)
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            source_url = None
            caption_url = None
            
            for script in soup.find_all('script', type='application/json'):
                try:
                    data = json.loads(script.string)
                    
                    def find_source(obj):
                        if isinstance(obj, dict):
                            if 'source' in obj:
                                return obj['source']
                            for value in obj.values():
                                result = find_source(value)
                                if result:
                                    return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_source(item)
                                if result:
                                    return result
                        return None

                    def find_captions(obj):
                        if isinstance(obj, dict):
                            if 'captions' in obj and isinstance(obj['captions'], list):
                                captions = obj['captions']
                                if len(captions) >= 2 and 'src' in captions[0] and 'src' in captions[1]:
                                    if captions[0]['src'] == captions[1]['src']:
                                        return captions[0]['src']
                                    else:
                                        return captions[0]['src']
                                elif len(captions) >= 1 and 'src' in captions[0]:
                                    return captions[0]['src']
                            for value in obj.values():
                                result = find_captions(value)
                                if result:
                                    return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_captions(item)
                                if result:
                                    return result
                        return None
                    
                    source_url = source_url or find_source(data)
                    caption_url = caption_url or find_captions(data)
                    
                    if source_url and caption_url:
                        self.logger.info(f"找到source URL: {source_url}")
                        self.logger.info(f"找到caption URL: {caption_url}")
                        return source_url, caption_url
                        
                except json.JSONDecodeError:
                    continue
                
            return source_url, caption_url
            
        except requests.RequestException as e:
            self.logger.error(f"請求頁面時發生錯誤: {str(e)}")
            return None, None
        except Exception as e:
            self.logger.error(f"解析頁面時發生錯誤: {str(e)}")
            return None, None

    def download_caption(self, url: str, title: str) -> bool:
        """
        下載字幕檔案
        :param url: 字幕URL
        :param title: 標題
        :return: 是否成功
        """
        try:
            safe_title = self.sanitize_filename(title[:3])
            output_path = os.path.join(self.subtitle_dir, f"{safe_title}.vtt")
            
            if os.path.exists(output_path):
                self.logger.warning(f"字幕檔案已存在: {output_path}")
                return False
                
            response = requests.get(url)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
                
            self.logger.info(f"字幕下載完成: {safe_title}.vtt")
            return True
            
        except Exception as e:
            self.logger.error(f"下載字幕時發生錯誤: {str(e)}")
            return False

    def sanitize_filename(self, filename: str) -> str:
        """
        清理檔案名稱，移除或替換不合法的字符
        :param filename: 原始檔案名稱
        :return: 處理後的檔案名稱
        """
        filename = filename.replace('｜', '|')
        filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
        filename = filename.strip('. ')
        
        if not filename:
            filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        return filename

    def setup_logging(self):
        """設置日誌記錄"""
        log_dir = os.path.join(self.output_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, f'download_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_tasks(self) -> List[Dict]:
        """
        從JSON檔案載入下載任務
        :return: 任務列表
        """
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析錯誤: {e}")
            return []
        except FileNotFoundError:
            self.logger.error(f"找不到檔案: {self.json_path}")
            return []

    def run_ffmpeg_command(self, command: List[str], task_title: str) -> bool:
        """
        執行ffmpeg命令並處理輸出
        :param command: ffmpeg命令列表
        :param task_title: 任務標題
        :return: 是否成功
        """
        try:
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

            _, stderr_data = process.communicate()
            return_code = process.wait()

            if return_code == 0:
                self.logger.info(f"下載完成: {task_title}")
                return True
            else:
                try:
                    error_message = stderr_data.decode('utf-8', errors='replace')
                except:
                    error_message = str(stderr_data)
                
                self.logger.error(f"下載失敗: {task_title}")
                self.logger.error(f"錯誤訊息: {error_message}")
                return False

        except Exception as e:
            self.logger.error(f"執行ffmpeg時發生錯誤: {str(e)}")
            return False

    def download_stream(self, task: Dict) -> tuple:
        """
        下載單個串流和字幕
        :param task: 下載任務信息
        :return: (任務信息, 是否成功)
        """
        original_url = task['url']
        original_title = task['title']
        safe_title = self.sanitize_filename(original_title)
        
        source_url, caption_url = self.extract_urls(original_url)
        url = source_url or original_url
        
        if caption_url:
            self.download_caption(caption_url, original_title)
        
        output_path = os.path.join(self.output_dir, f"{safe_title}-acc.mp4")
        
        if original_title != safe_title:
            self.logger.info(f"檔案名稱已修正: {original_title} -> {safe_title}")
        
        if os.path.exists(output_path):
            self.logger.warning(f"檔案已存在: {output_path}")
            return task, False

        command = [
            'ffmpeg',
            '-i', url,
            '-c', 'copy',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-y',
            output_path
        ]

        success = self.run_ffmpeg_command(command, safe_title)
        return task, success

    def run(self):
        """執行所有下載任務（並行處理）"""
        tasks = self.load_tasks()
        if not tasks:
            self.logger.error("沒有找到任何下載任務")
            return

        total = len(tasks)
        success = 0
        
        self.logger.info(f"影片下載位置: {self.output_dir}")
        self.logger.info(f"字幕下載位置: {self.subtitle_dir}")
        self.logger.info(f"開始處理 {total} 個下載任務")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {executor.submit(self.download_stream, task): task for task in tasks}
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    _, is_success = future.result()
                    if is_success:
                        success += 1
                except Exception as e:
                    self.logger.error(f"任務執行失敗: {task['title']}, 錯誤: {str(e)}")

        self.logger.info(f"下載完成: 成功 {success}/{total}")

def main():
    parser = argparse.ArgumentParser(description='串流下載工具')
    parser.add_argument('--json', type=str, default='download_tasks.json',
                      help='JSON任務檔案路徑 (預設: download_tasks.json)')
    parser.add_argument('--workers', type=int, default=3,
                      help='最大並行下載數 (預設: 3)')
    
    args = parser.parse_args()
    
    downloader = StreamDownloader(
        json_path=args.json,
        max_workers=args.workers
    )
    downloader.run()

if __name__ == "__main__":
    main()