#!/bin/bash
# 将技术报告.md转换为Word文档
# 需要先安装pandoc: https://pandoc.org/installing.html

echo "正在将技术报告.md转换为Word文档..."

# 检查pandoc是否安装
if ! command -v pandoc &> /dev/null; then
    echo "错误: 未找到pandoc，请先安装pandoc"
    echo "安装方法:"
    echo "  Ubuntu/Debian: sudo apt-get install pandoc"
    echo "  macOS: brew install pandoc"
    echo "  其他系统: https://pandoc.org/installing.html"
    exit 1
fi

# 使用pandoc转换
if [ -f "reference.docx" ]; then
    pandoc "技术报告.md" -o "基于混元大模型和SoulX-Podcast的AI播客生成系统技术报告.docx" --reference-doc=reference.docx
else
    pandoc "技术报告.md" -o "基于混元大模型和SoulX-Podcast的AI播客生成系统技术报告.docx"
fi

if [ $? -eq 0 ]; then
    echo "转换成功！输出文件: 基于混元大模型和SoulX-Podcast的AI播客生成系统技术报告.docx"
else
    echo "转换失败，请检查pandoc是否正确安装"
    exit 1
fi


