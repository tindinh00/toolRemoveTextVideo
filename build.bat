@echo off
echo ============================================
echo   Build Auto Video Watermark Remover
echo ============================================
echo.

echo [1/3] Cai dat PyInstaller...
pip install pyinstaller
echo.

echo [2/3] Dang dong goi thanh file .exe...
pyinstaller --noconfirm --onedir --windowed ^
    --name "VideoWatermarkRemover" ^
    --add-data "auth.py;." ^
    --add-data "workspace_ui_flow.py;." ^
    --hidden-import "customtkinter" ^
    --hidden-import "playwright" ^
    --hidden-import "playwright.async_api" ^
    --hidden-import "playwright_stealth" ^
    --hidden-import "moviepy" ^
    --hidden-import "moviepy.editor" ^
    --collect-all "customtkinter" ^
    --collect-all "playwright" ^
    --collect-all "playwright_stealth" ^
    main.py

echo.
echo [3/3] Cai dat trinh duyet Playwright cho may nay...
playwright install chromium

echo.
echo ============================================
echo   HOAN TAT!
echo   File .exe nam tai: dist\VideoWatermarkRemover\VideoWatermarkRemover.exe
echo   Chi can chay file .exe do la xong!
echo ============================================
pause
