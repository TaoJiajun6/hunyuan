@echo off
REM 将技术报告.md转换为Word文档
REM 需要先安装pandoc: https://pandoc.org/installing.html

echo 正在将技术报告.md转换为Word文档...

REM 检查pandoc是否安装
where pandoc >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到pandoc，请先安装pandoc
    echo 下载地址: https://pandoc.org/installing.html
    pause
    exit /b 1
)

REM 使用pandoc转换
pandoc "技术报告.md" -o "基于混元大模型和SoulX-Podcast的AI播客生成系统技术报告.docx" --reference-doc=reference.docx 2>nul

if %errorlevel% equ 0 (
    echo 转换成功！输出文件: 基于混元大模型和SoulX-Podcast的AI播客生成系统技术报告.docx
) else (
    REM 如果没有reference.docx，使用默认格式
    pandoc "技术报告.md" -o "基于混元大模型和SoulX-Podcast的AI播客生成系统技术报告.docx"
    if %errorlevel% equ 0 (
        echo 转换成功！输出文件: 基于混元大模型和SoulX-Podcast的AI播客生成系统技术报告.docx
    ) else (
        echo 转换失败，请检查pandoc是否正确安装
    )
)

pause


