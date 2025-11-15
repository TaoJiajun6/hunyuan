# Git LFS 使用说明

## 概述

本项目使用 Git LFS（Large File Storage）来管理 `music/` 目录中的大音频文件。

## 配置说明

### 1. 已跟踪的文件类型

以下音频文件类型会自动使用 Git LFS 管理：
- `*.mp3`
- `*.wav`
- `*.m4a`
- `*.flac`
- `*.ogg`
- `*.aac`

所有位于 `music/` 目录及其子目录下的这些文件都会被 Git LFS 跟踪。

## 使用方法

### 首次设置（已完成）

```bash
# 1. 安装 Git LFS（如果未安装）
# Windows: 下载并安装 https://git-lfs.github.com/
# macOS: brew install git-lfs
# Linux: sudo apt-get install git-lfs

# 2. 初始化 Git LFS（已完成）
git lfs install

# 3. 跟踪文件类型（已完成，已配置在 .gitattributes 中）
# 文件已自动配置，无需手动执行
```

### 添加新文件

```bash
# 1. 将文件添加到 music 目录
# 例如：将 music.mp3 复制到 music/business/ 目录

# 2. 正常使用 git add（Git LFS 会自动处理）
git add music/business/music.mp3

# 3. 提交
git commit -m "添加背景音乐文件"

# 4. 推送到远程仓库
git push
```

### 克隆仓库（包含 LFS 文件）

```bash
# 方法1：克隆时自动下载 LFS 文件（推荐）
git lfs clone <repository-url>

# 方法2：先克隆，再拉取 LFS 文件
git clone <repository-url>
cd <repository-name>
git lfs pull
```

### 拉取更新（包含 LFS 文件）

```bash
# 拉取代码和 LFS 文件
git pull
git lfs pull
```

### 检查 LFS 文件状态

```bash
# 查看已跟踪的 LFS 文件
git lfs ls-files

# 查看 LFS 文件详细信息
git lfs ls-files --long

# 查看 LFS 文件大小
git lfs ls-files | ForEach-Object { git lfs pointer --file=$_ }
```

### 迁移现有文件到 LFS

如果 music 目录中已有文件但未使用 LFS：

```bash
# 1. 确保文件已添加到 Git
git add music/

# 2. 迁移到 LFS
git lfs migrate import --include="music/**/*.mp3,music/**/*.wav,music/**/*.m4a,music/**/*.flac,music/**/*.ogg,music/**/*.aac" --everything

# 3. 推送到远程
git push --force
```

## 注意事项

1. **文件大小限制**：
   - Git LFS 通常有存储配额限制（GitHub 免费账户：1GB 存储，1GB 带宽/月）
   - 如果文件过多，考虑使用云存储（如华为 AGC 云存储）

2. **性能**：
   - LFS 文件在 `git clone` 时不会自动下载，需要使用 `git lfs clone` 或 `git lfs pull`
   - 这样可以加快初始克隆速度

3. **`.gitattributes` 文件**：
   - 必须提交 `.gitattributes` 文件到仓库
   - 这样其他协作者克隆时也会自动使用 LFS

4. **忽略规则**：
   - 确保 `.gitignore` 不会忽略 `music/` 目录
   - 如果 music 目录在 `.gitignore` 中，需要移除或添加例外规则

## 故障排除

### 问题：LFS 文件显示为指针文件

```bash
# 解决方案：拉取 LFS 文件
git lfs pull
```

### 问题：推送时提示 LFS 配额不足

```bash
# 解决方案：
# 1. 检查 LFS 使用情况
git lfs ls-files | Measure-Object -Property Length -Sum

# 2. 考虑删除不需要的大文件
git lfs prune

# 3. 或使用云存储替代方案
```

### 问题：克隆后 music 目录为空

```bash
# 解决方案：拉取 LFS 文件
git lfs pull
```

## 相关命令速查

```bash
# 初始化 Git LFS
git lfs install

# 查看 LFS 文件
git lfs ls-files

# 拉取 LFS 文件
git lfs pull

# 克隆（包含 LFS）
git lfs clone <url>

# 迁移现有文件到 LFS
git lfs migrate import --include="pattern" --everything

# 清理本地 LFS 缓存
git lfs prune
```

