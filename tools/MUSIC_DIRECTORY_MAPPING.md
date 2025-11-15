# 音乐目录英文名称映射

## 目录映射表

| 中文分类 | 英文目录名 | 说明 |
|---------|-----------|------|
| 商业 | `business` | Business |
| 科技 | `technology` | Technology |
| 财经 | `finance` | Finance |
| 新闻 | `news` | News |
| 影视 | `film` | Film |
| 音乐 | `music` | Music |
| 文化艺术 | `culture` | Culture |
| 历史 | `history` | History |
| 哲学思考 | `philosophy` | Philosophy |
| 自我成长 | `self_improvement` | Self Improvement |
| 职场 | `career` | Career |
| 学习 | `learning` | Learning |
| 教育育儿 | `education` | Education |
| 情感恋爱 | `relationship` | Relationship |
| 健康养生 | `health` | Health |
| 旅游 | `travel` | Travel |
| 美食 | `food` | Food |
| 生活方式 | `lifestyle` | Lifestyle |
| 娱乐 | `entertainment` | Entertainment |
| 游戏电竞 | `gaming` | Gaming |
| 体育 | `sports` | Sports |
| 时尚美妆 | `fashion` | Fashion |
| 汽车 | `automotive` | Automotive |
| 法律 | `law` | Law |
| 宠物 | `pets` | Pets |

## 使用说明

### 1. 本地目录重命名

如果您的本地 `music/` 目录使用的是中文名称，需要重命名为英文：

**Windows PowerShell 示例：**
```powershell
# 进入 music 目录
cd music

# 重命名目录（示例）
Rename-Item "商业（包含创业创新" "business"
Rename-Item "科技（包含科学科普）" "technology"
Rename-Item "财经" "finance"
# ... 其他目录类似
```

**Linux/Mac 示例：**
```bash
# 进入 music 目录
cd music

# 重命名目录（示例）
mv "商业（包含创业创新" "business"
mv "科技（包含科学科普）" "technology"
mv "财经" "finance"
# ... 其他目录类似
```

### 2. 上传到云存储

使用 `tools/upload_music_to_cloud.py` 脚本上传时，确保目录已经是英文名称：

```bash
python tools/upload_music_to_cloud.py
```

上传后，云存储中的目录结构应该是：
```
music/
  ├── business/
  ├── technology/
  ├── finance/
  ├── sports/
  └── ...
```

### 3. 代码中的映射

代码中的映射关系（`hunyuan_podcast/music_selector.py`）：

```python
CATEGORY_TO_MUSIC_DIR = {
    "商业": "business",
    "科技": "technology",
    "财经": "finance",
    # ... 其他映射
}
```

当用户选择播客分类为"商业"时，系统会自动匹配到 `music/business/` 目录。

## 注意事项

1. **目录名大小写**：目录名使用小写，匹配时不区分大小写
2. **下划线和连字符**：`self_improvement` 和 `self-improvement` 可以互换匹配
3. **URL编码**：上传和下载时会自动处理URL编码，无需手动处理
4. **兼容性**：如果云存储中仍有中文目录名，系统会尝试匹配，但建议统一使用英文目录名

## 批量重命名脚本（可选）

如果需要批量重命名，可以使用以下 Python 脚本：

```python
import os
from pathlib import Path

# 映射关系
MAPPING = {
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
    "宠物": "pets"
}

music_dir = Path("music")
for old_name, new_name in MAPPING.items():
    old_path = music_dir / old_name
    new_path = music_dir / new_name
    if old_path.exists() and not new_path.exists():
        old_path.rename(new_path)
        print(f"✓ 重命名: {old_name} -> {new_name}")
    elif old_path.exists():
        print(f"⚠️ 跳过: {new_name} 已存在")
    else:
        print(f"⚠️ 未找到: {old_name}")
```

