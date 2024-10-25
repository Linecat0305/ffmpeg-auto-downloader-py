import os
import re
import sys
import subprocess
import argparse
from pathlib import Path
import logging
from typing import Optional
from dataclasses import dataclass

@dataclass
class Chapter:
    start: int
    end: int
    
    @classmethod
    def from_string(cls, chapter_str: str) -> 'Chapter':
        start, end = map(int, chapter_str.split('-'))
        return cls(start, end)
    
    def __eq__(self, other: 'Chapter') -> bool:
        return self.start == other.start and self.end == other.end

class VideoSubtitleMerger:
    def __init__(self, ffmpeg_path: str = 'ffmpeg', debug: bool = False):
        self.ffmpeg_path = ffmpeg_path
        
        log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _extract_chapter(self, filename: str) -> Optional[Chapter]:
        pattern = r'(\d+-\d+)'
        match = re.search(pattern, filename)
        if match:
            return Chapter.from_string(match.group(1))
        return None
    
    def _run_ffmpeg_command(self, cmd: list[str], description: str) -> bool:
        try:
            self.logger.debug(f"執行 FFmpeg 命令: {' '.join(cmd)}")
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                encoding='utf-8',
                errors='replace',
                check=False
            )

            if result.returncode != 0:
                self.logger.error(f"{description}失敗")
                self.logger.error(f"FFmpeg 錯誤輸出: {result.stderr}")
                return False
                
            self.logger.debug(f"{description}成功")
            return True
            
        except Exception as e:
            self.logger.error(f"{description}時發生錯誤: {str(e)}")
            return False
    
    def merge_with_chapter_matching(self,
                                  video_dir: str,
                                  subtitle_dir: str,
                                  output_dir: str,
                                  video_ext: str = '.mp4',
                                  subtitle_ext: str = '.vtt',
                                  subtitle_style: dict = None) -> None:
        os.makedirs(output_dir, exist_ok=True)
        
        default_style = {
            'FontSize': 24,
            'PrimaryColour': '&HFFFFFF&',
            'OutlineColour': '&H000000&',
            'Outline': 2,
            'FontName': 'Microsoft YaHei',
            'BackColour': '&H80000000&',
            'Bold': 1
        }
        
        if subtitle_style:
            default_style.update(subtitle_style)
        
        video_files = [f for f in os.listdir(video_dir) if f.endswith(video_ext)]
        subtitle_files = [f for f in os.listdir(subtitle_dir) if f.endswith(subtitle_ext)]
        
        total_files = len(video_files)
        processed_files = 0
        failed_files = 0
        
        self.logger.info(f"找到 {total_files} 個影片檔案")
        
        def sanitize_path(path):
            return os.path.normpath(path)
        
        for video_file in video_files:
            try:
                video_chapter = self._extract_chapter(video_file)
                if not video_chapter:
                    self.logger.warning(f"無法從 {video_file} 提取章節信息")
                    continue
                
                matching_subtitle = None
                for subtitle_file in subtitle_files:
                    subtitle_chapter = self._extract_chapter(subtitle_file)
                    if subtitle_chapter and subtitle_chapter == video_chapter:
                        matching_subtitle = subtitle_file
                        break
                
                if not matching_subtitle:
                    self.logger.warning(f"找不到匹配的字幕檔案: {video_file}")
                    continue
                
                video_path = sanitize_path(os.path.join(video_dir, video_file))
                subtitle_path = sanitize_path(os.path.join(subtitle_dir, matching_subtitle))
                
                if not os.path.exists(video_path):
                    self.logger.error(f"影片檔案不存在: {video_path}")
                    continue
                    
                if not os.path.exists(subtitle_path):
                    self.logger.error(f"字幕檔案不存在: {subtitle_path}")
                    continue
                
                output_path = sanitize_path(os.path.join(
                    output_dir,
                    f"{Path(video_file).stem}_hardsub{video_ext}"
                ))
                
                style_str = ','.join([
                    f"{k}={v}" for k, v in default_style.items()
                ])
                
                filter_complex = f"subtitles='{subtitle_path}':force_style='{style_str}'"
                
                if os.name == 'nt':
                    filter_complex = filter_complex.replace('\\', '\\\\')
                
                cmd = [
                    self.ffmpeg_path,
                    '-i', video_path,
                    '-vf', filter_complex,
                    '-c:a', 'copy',
                    '-max_muxing_queue_size', '1024',
                    '-y',
                    output_path
                ]
                
                if self._run_ffmpeg_command(cmd, f"處理檔案 {video_file}"):
                    processed_files += 1
                    self.logger.info(
                        f"成功處理 ({processed_files}/{total_files}): {video_file}"
                    )
                else:
                    failed_files += 1
                
            except Exception as e:
                failed_files += 1
                self.logger.error(f"處理 {video_file} 時發生錯誤: {str(e)}")
                self.logger.debug("錯誤詳情:", exc_info=True)
        
        self.logger.info("\n====== 處理完成 ======")
        self.logger.info(f"總檔案數: {total_files}")
        self.logger.info(f"成功處理: {processed_files}")
        self.logger.info(f"處理失敗: {failed_files}")

def main():
    parser = argparse.ArgumentParser(
        description='自動將字幕燒錄到影片中',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--video_dir',
        type=str,
        required=True,
        help='影片目錄路徑'
    )
    
    parser.add_argument(
        '--subtitle_dir',
        type=str,
        required=True,
        help='字幕目錄路徑'
    )
    
    parser.add_argument(
        '--output_dir',
        type=str,
        required=True,
        help='輸出目錄路徑'
    )
    
    parser.add_argument(
        '--video_ext',
        type=str,
        default='.mp4',
        help='影片副檔名'
    )
    
    parser.add_argument(
        '--subtitle_ext',
        type=str,
        default='.vtt',
        help='字幕副檔名'
    )
    
    parser.add_argument(
        '--ffmpeg_path',
        type=str,
        default='ffmpeg',
        help='FFmpeg執行檔路徑'
    )
    
    parser.add_argument(
        '--font_size',
        type=int,
        default=24,
        help='字幕大小'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='開啟除錯模式'
    )
    
    args = parser.parse_args()
    
    for dir_path in [args.video_dir, args.subtitle_dir]:
        if not os.path.exists(dir_path):
            print(f"錯誤: 目錄不存在: {dir_path}")
            return
    
    try:
        subprocess.run(
            [args.ffmpeg_path, '-version'],
            capture_output=True,
            check=True
        )
    except Exception as e:
        print(f"錯誤: FFmpeg 檢查失敗: {str(e)}")
        print("請確認 FFmpeg 已正確安裝且在系統路徑中")
        return
    
    subtitle_style = {
        'FontSize': args.font_size,
        'PrimaryColour': '&HFFFFFF&',
        'OutlineColour': '&H000000&',
        'Outline': 2,
        'FontName': 'Microsoft YaHei',
        'BackColour': '&H80000000&',
        'Bold': 1
    }
    
    merger = VideoSubtitleMerger(
        ffmpeg_path=args.ffmpeg_path,
        debug=args.debug
    )
    
    merger.merge_with_chapter_matching(
        video_dir=args.video_dir,
        subtitle_dir=args.subtitle_dir,
        output_dir=args.output_dir,
        video_ext=args.video_ext,
        subtitle_ext=args.subtitle_ext,
        subtitle_style=subtitle_style
    )

if __name__ == "__main__":
    main()