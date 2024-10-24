# Stream Downloader

一個用於下載串流影片和字幕的Python工具。支持並行下載、自動提取源URL和字幕，並進行檔案管理。

## 功能特點

- 自動提取影片串流源URL
- 自動提取並下載字幕檔案
- 支持並行下載多個影片
- 自動建立輸出目錄結構
- 詳細的日誌記錄
- 檔案名稱自動清理和格式化
- 支援批量下載

## 系統要求

- Python 3.8 或更高版本
- FFmpeg（需要預先安裝）
- Windows/Mac/Linux 作業系統

## 安裝步驟

### 1. 安裝 Python

1. 訪問 [Python官網](https://www.python.org/downloads/) 下載並安裝 Python 3.8+
2. 安裝時請勾選「Add Python to PATH」選項
3. 開啟命令提示字元(cmd)，輸入以下命令確認安裝：
   ```bash
   python --version
   ```

### 2. 安裝 FFmpeg

#### Windows：
方法1 - 使用Chocolatey（推薦）：
1. 以系統管理員身份開啟 PowerShell
2. 執行以下命令：
   ```powershell
   choco install ffmpeg
   ```

方法2 - 手動安裝：
1. 訪問 [FFmpeg官網](https://ffmpeg.org/download.html)
2. 下載 Windows 版本
3. 解壓縮到指定目錄（如 `C:\ffmpeg`）
4. 將 bin 目錄（如 `C:\ffmpeg\bin`）添加到系統環境變數 PATH 中

#### Mac：
使用 Homebrew 安裝：
```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian)：
```bash
sudo apt update
sudo apt install ffmpeg
```

### 3. 安裝必要的 Python 套件

在命令提示字元中執行：
```bash
pip install requests beautifulsoup4
```

### 4. 驗證安裝

在命令提示字元中執行以下命令，確認所有組件都已正確安裝：
```bash
python --version
ffmpeg -version
pip list | findstr "requests beautifulsoup4"
```

## 使用方法

### 1. 準備下載任務檔案

創建一個 JSON 檔案（例如 `download_tasks.json`），格式如下：
```json
[
    {
        "url": "https://example.com/video-page",
        "title": "1-1導論|生成式AI為何重要"
    },
    {
        "url": "https://example.com/video-page2",
        "title": "1-2實作|基礎環境建置"
    }
]
```

### 2. 執行下載

基本使用：
```bash
python stream_downloader.py --json download_tasks.json
```

自定義並行數：
```bash
python stream_downloader.py --json download_tasks.json --workers 5
```

### 3. 輸出位置

- 影片檔案：`~/Desktop/Course/`
- 字幕檔案：`~/Desktop/st.vtt/`
- 日誌檔案：`~/Desktop/Course/logs/`

## 參數說明

- `--json`：指定下載任務JSON檔案的路徑（預設：download_tasks.json）
- `--workers`：指定最大並行下載數（預設：3）

## 檔案命名規則

- 影片檔案：使用原始標題，自動清理非法字符，副檔名為 `-acc.mp4`
- 字幕檔案：使用原始標題的前三個字符，副檔名為 `.vtt`

## 日誌記錄

程式會在 `~/Desktop/Course/logs/` 目錄下生成詳細的執行日誌，格式為：
```
download_YYYYMMDD_HHMMSS.log
```

## 常見問題排解

### 1. FFmpeg 未找到
錯誤訊息：`FFmpeg not found`
解決方案：
- 確認 FFmpeg 是否正確安裝
- 檢查系統環境變數 PATH 是否包含 FFmpeg

### 2. 下載失敗
可能原因：
- 網路連接問題
- URL 無效或已過期
- 檔案已存在
解決方案：
- 檢查網路連接
- 確認 URL 是否可訪問
- 檢查輸出目錄權限

### 3. 字符編碼錯誤
解決方案：
- 確保系統支援 UTF-8 編碼
- 檢查檔案名稱是否包含特殊字符

## 注意事項

1. 確保有足夠的硬碟空間
2. 建議使用穩定的網路連接
3. 不建議設置過高的並行數（建議 3-5 個）
4. 定期清理日誌檔案

## 授權說明

此工具僅供學習和個人使用，請遵守相關法律法規。

## 更新日誌

### v1.0.0
- 初始版本發布
- 支援影片和字幕下載
- 支援並行處理
- 自動建立目錄結構

PS 我可能不會再繼續更新了 因為我也想不到可以更新啥