#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查 IndexTTS-2 模型文件是否完整
"""
import os
import sys

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

checkpoints_dir = "index-tts/checkpoints"

# 必需文件列表
required_files = {
    "config.yaml": "配置文件",
    "bpe.model": "BPE 分词模型",
    "gpt.pth": "GPT 模型权重（约2-3GB）",
    "s2mel.pth": "S2Mel 模型权重（约1-2GB）",
    "wav2vec2bert_stats.pt": "Wav2Vec2BERT 统计文件"
}

# 可选文件
optional_files = {
    "pinyin.vocab": "拼音词汇表",
    "emo_matrix.pt": "情感矩阵",
    "spk_matrix.pt": "说话人矩阵"
}

print("=" * 60)
print("IndexTTS-2 模型文件检查")
print("=" * 60)
print(f"\n检查目录: {checkpoints_dir}\n")

if not os.path.exists(checkpoints_dir):
    print(f"❌ 目录不存在: {checkpoints_dir}")
    print("\n请先创建目录或下载模型文件")
    exit(1)

# 检查必需文件
print("必需文件检查：")
print("-" * 60)
missing_required = []
for file, desc in required_files.items():
    file_path = os.path.join(checkpoints_dir, file)
    if os.path.exists(file_path):
        size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        size_kb = os.path.getsize(file_path) / 1024  # KB
        
        # 特殊处理：某些文件可能很小但正常
        if file == "config.yaml":
            # config.yaml 通常是几KB到几十KB
            if size_kb < 1:  # 小于 1KB 才认为异常
                print(f"⚠️  {file:30s} - 存在但大小异常 ({size_kb:.2f} KB) - {desc}")
                missing_required.append(file)
            else:
                print(f"✅ {file:30s} - {size_kb:.2f} KB - {desc}")
        elif file == "wav2vec2bert_stats.pt":
            # wav2vec2bert_stats.pt 通常很小（几KB到几十KB）
            if size_kb < 0.1:  # 小于 0.1KB 才认为异常
                print(f"⚠️  {file:30s} - 存在但大小异常 ({size_kb:.2f} KB) - {desc}")
                missing_required.append(file)
            else:
                print(f"✅ {file:30s} - {size_kb:.2f} KB - {desc}")
        elif size < 0.1:  # 其他文件小于 100KB，可能是空文件或损坏
            print(f"⚠️  {file:30s} - 存在但大小异常 ({size:.2f} MB) - {desc}")
            missing_required.append(file)
        else:
            print(f"✅ {file:30s} - {size:.2f} MB - {desc}")
    else:
        print(f"❌ {file:30s} - 缺失 - {desc}")
        missing_required.append(file)

# 检查可选文件
print("\n可选文件检查：")
print("-" * 60)
for file, desc in optional_files.items():
    file_path = os.path.join(checkpoints_dir, file)
    if os.path.exists(file_path):
        size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        print(f"✅ {file:30s} - {size:.2f} MB - {desc}")
    else:
        print(f"⚪ {file:30s} - 未找到（可选） - {desc}")

# 总结
print("\n" + "=" * 60)
if missing_required:
    print(f"❌ 缺少 {len(missing_required)} 个必需文件:")
    for file in missing_required:
        print(f"   - {file}")
    print("\n💡 解决方案：")
    print("   1. 使用 HuggingFace CLI 下载：")
    print("      cd index-tts")
    print("      hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints")
    print("\n   2. 或使用 ModelScope 下载：")
    print("      cd index-tts")
    print("      modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints")
    print("\n   3. 如果下载中断，重新运行下载命令即可（支持断点续传）")
else:
    print("✅ 所有必需文件都已下载！")
    print("\n可以正常运行 IndexTTS-2 了")
print("=" * 60)

