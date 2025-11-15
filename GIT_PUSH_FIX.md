# Git 推送被拒绝问题解决方案

## 问题描述

```
! [rejected]        computer -> computer (non-fast-forward)
error: failed to push some refs
```

这表示本地分支和远程分支已分叉，需要先同步。

## 解决方案

### 方案1：使用 Rebase（推荐，保持历史线性）

```powershell
# 1. 拉取远程更改并变基
git pull --rebase origin computer

# 2. 如果有冲突，解决冲突后：
git add .
git rebase --continue

# 3. 如果 rebase 过程中想放弃：
git rebase --abort

# 4. 推送
git push origin computer
```

**优点**：保持提交历史线性，没有合并提交  
**缺点**：如果有冲突需要逐个解决

### 方案2：使用 Merge（简单，但会有合并提交）

```powershell
# 1. 拉取远程更改并合并
git pull origin computer

# 2. 如果有冲突，解决冲突后：
git add .
git commit -m "合并远程更改"

# 3. 推送
git push origin computer
```

**优点**：简单，保留所有历史  
**缺点**：会创建合并提交

### 方案3：强制推送（危险，谨慎使用）

**⚠️ 警告**：这会覆盖远程分支，可能丢失其他人的提交！

```powershell
# 更安全的强制推送（推荐）
git push --force-with-lease origin computer

# 或者完全强制推送（不推荐）
git push --force origin computer
```

**使用场景**：
- 确定远程的更改不重要
- 使用了 `git lfs migrate` 重写了历史
- 确定没有其他人在使用这个分支

## 当前情况分析

根据 `git status` 输出：
- 本地有 64 个不同的提交
- 远程有 62 个不同的提交
- 分支已分叉

**建议**：
1. 如果本地提交重要（如"添加背景音乐文件"），使用 **方案1（rebase）**
2. 如果想保留所有历史，使用 **方案2（merge）**
3. 如果确定远程更改不重要，使用 **方案3（force-with-lease）**

## 操作步骤（推荐：Rebase）

```powershell
# 步骤1：拉取并变基
git pull --rebase origin computer

# 步骤2：如果有冲突，查看冲突文件
git status

# 步骤3：解决冲突后继续
git add .
git rebase --continue

# 步骤4：重复步骤2-3直到所有冲突解决

# 步骤5：推送
git push origin computer
```

## 如果使用 Git LFS 迁移

如果使用了 `git lfs migrate`，历史已被重写，必须强制推送：

```powershell
# 安全强制推送
git push --force-with-lease origin computer
```

## 处理"refusing to merge unrelated histories"错误

如果遇到以下错误：
```
fatal: refusing to merge unrelated histories
```

这表示两个分支没有共同的历史记录。解决方案：

### 方案1：允许合并不相关历史（推荐）

```powershell
# 从 main 分支拉取并允许不相关历史
git pull origin main --allow-unrelated-histories

# 如果有冲突，解决冲突后：
git add .
git commit -m "合并 main 分支的更改"

# 然后推送
git push origin computer
```

### 方案2：只合并特定分支

如果只想同步 computer 分支：

```powershell
# 从 computer 分支拉取（不是 main）
git pull origin computer --allow-unrelated-histories

# 或者使用 rebase
git pull --rebase origin computer --allow-unrelated-histories
```

### 方案3：创建合并提交

```powershell
# 合并 main 分支到当前分支
git merge origin/main --allow-unrelated-histories

# 解决冲突后提交
git add .
git commit -m "合并 main 分支"

# 推送
git push origin computer
```

## 预防措施

1. **推送前先拉取**：
   ```powershell
   git pull --rebase origin computer
   git push origin computer
   ```

2. **定期同步**：
   ```powershell
   git fetch origin
   git status  # 检查是否有新的远程提交
   ```

3. **使用分支保护**：
   - 在 GitHub/GitLab 设置分支保护规则
   - 防止意外强制推送

4. **避免跨分支拉取**：
   - 如果当前在 `computer` 分支，应该拉取 `origin/computer`，而不是 `origin/main`
   - 如果需要合并 main 分支，使用 `git merge origin/main`

