"""
批量重命名 music 目录下的中文目录名为英文

使用方法：
python tools/rename_music_directories.py

注意：此脚本会直接重命名目录，请确保已备份或确认无误后再运行
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 中文到英文的目录名映射
DIRECTORY_MAPPING = {
    "商业（包含创业创新": "business",
    "科技（包含科学科普）": "technology",
    "财经": "finance",
    "新闻": "news",
    "影视": "film",
    "音乐": "music",
    "文化艺术（包含读书阅读）": "culture",
    "历史": "history",
    "哲学思考": "philosophy",
    "自我成长（包含自我成长与自愈、心理学": "self_improvement",
    "职场（包含职场万象、职场人际关系、求职就业）": "career",
    "学习（包含学习类、考题）": "learning",
    "教育育儿": "education",
    "情感恋爱": "relationship",
    "健康养生（包含运动健身）": "health",
    "旅游": "travel",
    "美食": "food",
    "生活方式": "lifestyle",
    "娱乐（包含娱乐八卦、喜剧）": "entertainment",
    "游戏电竞": "gaming",
    "体育": "sports",
    "时尚美妆": "fashion",
    "汽车": "automotive",
    "法律": "law",
    "宠物": "pets",
    "其他": "other"  # 如果存在"其他"目录
}


def rename_directories(music_dir: str = "music", dry_run: bool = False):
    """
    批量重命名目录
    
    Args:
        music_dir: music 目录路径
        dry_run: 如果为 True，只显示将要执行的操作，不实际重命名
    """
    music_path = Path(music_dir)
    
    if not music_path.exists():
        print(f"错误：音乐目录不存在: {music_dir}")
        return
    
    print("=" * 60)
    print("批量重命名音乐目录")
    print("=" * 60)
    print(f"音乐目录: {music_path.absolute()}")
    print(f"模式: {'预览模式（不会实际重命名）' if dry_run else '执行模式（将实际重命名）'}")
    print("=" * 60)
    print()
    
    renamed_count = 0
    skipped_count = 0
    not_found_count = 0
    
    for old_name, new_name in DIRECTORY_MAPPING.items():
        old_path = music_path / old_name
        new_path = music_path / new_name
        
        if old_path.exists() and old_path.is_dir():
            if new_path.exists():
                print(f"⚠️  跳过: '{old_name}' -> '{new_name}' (目标目录已存在)")
                skipped_count += 1
            else:
                if dry_run:
                    print(f"  [预览] '{old_name}' -> '{new_name}'")
                else:
                    try:
                        old_path.rename(new_path)
                        print(f"✓ 重命名: '{old_name}' -> '{new_name}'")
                        renamed_count += 1
                    except Exception as e:
                        print(f"✗ 重命名失败: '{old_name}' -> '{new_name}': {e}")
                        skipped_count += 1
        else:
            # 检查是否已经是英文名
            if new_path.exists():
                print(f"ℹ️  已存在: '{new_name}' (可能已经重命名过)")
            else:
                print(f"⚠️  未找到: '{old_name}'")
                not_found_count += 1
    
    print()
    print("=" * 60)
    print("重命名完成")
    print("=" * 60)
    print(f"成功: {renamed_count} 个")
    print(f"跳过: {skipped_count} 个")
    print(f"未找到: {not_found_count} 个")
    print()
    
    if dry_run:
        print("提示：这是预览模式，没有实际重命名目录")
        print("      要执行重命名，请运行: python tools/rename_music_directories.py --execute")
    else:
        print("✓ 目录重命名完成！")
        print("  现在可以使用 tools/upload_music_to_cloud.py 上传到云存储")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='批量重命名 music 目录下的中文目录名为英文')
    parser.add_argument('--music-dir', type=str, default='music',
                        help='music 目录路径（默认: music）')
    parser.add_argument('--execute', action='store_true',
                        help='执行重命名（默认是预览模式）')
    
    args = parser.parse_args()
    
    # 确认
    if args.execute:
        print("警告：此操作将重命名目录，请确保已备份！")
        response = input("确认继续？(y/n): ")
        if response.lower() != 'y':
            print("已取消")
            sys.exit(0)
    
    rename_directories(music_dir=args.music_dir, dry_run=not args.execute)


if __name__ == '__main__':
    main()

