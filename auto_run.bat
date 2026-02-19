@echo off
:: 1. Go to the correct project folder
cd /d "C:\Users\Admin\Desktop\joe\VIX dashboard"

:: 2. Force UTF-8 so emojis don't crash the script
set PYTHONIOENCODING=utf-8

:: 3. Run the script and capture ALL output to log
echo ========================================== >> fetch_log.txt
echo Run started at %date% %time% >> fetch_log.txt
python vix_data_fetcher.py >> fetch_log.txt 2>&1

:: 4. Log completion
echo Run finished at %date% %time% >> fetch_log.txt
echo ========================================== >> fetch_log.txt