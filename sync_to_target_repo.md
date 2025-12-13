# 将本地代码覆盖到目标仓库的 hunyuan 文件夹

根据图片，目标仓库是 `tencent-hunyuan-ai-podcast`，需要将本地内容覆盖到目标仓库的 `hunyuan` 文件夹。

## 方法一：使用临时目录（推荐，最安全）

### 步骤：

1. **克隆目标仓库到临时目录**
   ```bash
   cd ..
   git clone <目标仓库地址> temp-target-repo
   cd temp-target-repo
   ```

2. **切换到 master 分支**
   ```bash
   git checkout master
   ```

3. **删除目标仓库中的旧 hunyuan 文件夹**
   ```bash
   # Windows PowerShell
   Remove-Item -Recurse -Force hunyuan
   
   # 或 Git 删除
   git rm -r hunyuan
   ```

4. **复制本地 hunyuan 目录的所有内容到目标仓库**
   ```bash
   # 复制整个目录
   # Windows PowerShell
   Copy-Item -Recurse ..\hunyuan\hunyuan hunyuan
   
   # 或者使用 robocopy（更可靠）
   robocopy ..\hunyuan\hunyuan hunyuan /E /XD .git __pycache__ .cursor
   ```

5. **添加所有更改并提交**
   ```bash
   git add .
   git commit -m "更新：覆盖 hunyuan 文件夹内容"
   ```

6. **推送到目标仓库**
   ```bash
   git push origin master
   ```

## 方法二：直接添加远程并推送（更直接）

### 步骤：

1. **在本地 hunyuan 目录中，先提交所有更改**
   ```bash
   git add .
   git commit -m "更新：准备同步到目标仓库"
   ```

2. **添加目标仓库为新的远程（替换为目标仓库的实际地址）**
   ```bash
   # 假设目标仓库地址是类似这样的格式（需要替换为实际地址）
   git remote add target <目标仓库地址>
   
   # 例如：
   # git remote add target https://gitee.com/xxx/tencent-hunyuan-ai-podcast.git
   # 或
   # git remote add target git@gitee.com:xxx/tencent-hunyuan-ai-podcast.git
   ```

3. **获取目标仓库的内容**
   ```bash
   git fetch target
   ```

4. **检查目标仓库的 master 分支**
   ```bash
   git checkout -b temp-master target/master
   ```

5. **将当前分支的内容合并到目标仓库结构**
   ```bash
   # 这个方法比较复杂，推荐使用方法一
   ```

## 方法三：使用脚本自动化（最简单）

我为您创建一个 PowerShell 脚本：

