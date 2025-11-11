#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试输出路径配置"""
import os
import sys

# 添加项目路径
sys.path.insert(0, '.')

from hunyuan_podcast.config import OUTPUT_DIR
from hunyuan_podcast.utils import get_output_path

print("=" * 60)
print("输出路径配置测试")
print("=" * 60)
print(f"\n配置的输出目录: {OUTPUT_DIR}")
print(f"绝对路径: {os.path.abspath(OUTPUT_DIR)}")
print(f"目录存在: {os.path.exists(OUTPUT_DIR)}")

if os.path.exists(OUTPUT_DIR):
    files = os.listdir(OUTPUT_DIR)
    print(f"文件数量: {len(files)}")
    if files:
        print("文件列表:")
        for f in files[:10]:
            file_path = os.path.join(OUTPUT_DIR, f)
            size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            print(f"  - {f} ({size:.2f} MB)")
    else:
        print("目录为空")

# 测试生成路径
test_path = get_output_path("test.wav")
print(f"\n测试生成路径: {test_path}")
print(f"绝对路径: {os.path.abspath(test_path)}")
print("=" * 60)










