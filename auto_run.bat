@echo off
:: 1. Go to your specific folder
cd "C:\Users\Admin\Desktop\joe"

:: 2. Run the script
call python vix_data_fetcher.py

:: 3. Log the success (or failure) to a text file
echo Run attempt at %date% %time% >> fetch_log.txt