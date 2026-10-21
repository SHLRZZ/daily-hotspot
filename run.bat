@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在采集今日网络热点，请稍候...
python run.py %*
if errorlevel 1 (
  echo.
  echo 运行失败：请确认已安装 Python 3.9+ 并加入 PATH
)
echo.
echo 报告已生成：%~dp0reports\latest.html
start "" "%~dp0reports\latest.html"
pause
