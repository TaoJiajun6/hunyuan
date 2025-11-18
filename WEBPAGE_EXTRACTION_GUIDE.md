# 网页内容提取指南

## 概述

本系统支持两种方式提取网页内容：
1. **普通提取**：使用 `requests` 库直接提取静态HTML内容（快速，但无法处理JavaScript渲染的网页）
2. **无头浏览器提取**：使用 `Playwright` 无头浏览器提取需要JavaScript渲染的网页内容（较慢，但可以处理动态网页）

## 自动检测和回退

系统会自动检测需要JavaScript渲染的网站（如百度移动端、微博等），如果普通提取失败，会自动尝试使用无头浏览器提取。

## 安装 Playwright（可选）

如果要提取需要JavaScript渲染的网页（如百度移动端、微博等），需要安装 Playwright：

### Windows

```bash
pip install playwright
playwright install chromium
```

### Linux/Mac

```bash
pip install playwright
playwright install chromium
```

### 注意事项

- Playwright 需要下载浏览器驱动，首次安装可能需要几分钟
- 安装后，浏览器驱动会占用约 200-300MB 磁盘空间
- 如果不需要提取JavaScript渲染的网页，可以不安装 Playwright

## 支持的网站类型

### 可以直接提取（无需 Playwright）

- 普通静态网页
- 微信公众号文章
- 大多数新闻网站

### 需要 Playwright（自动检测并尝试）

- 百度移动端（`mbd.baidu.com`）
- 微博（`weibo.com`）
- Twitter（`twitter.com`）
- Facebook（`facebook.com`）
- Instagram（`instagram.com`）
- 其他需要JavaScript渲染的网站

## 使用方法

### 方法1：通过API自动提取

系统会自动检测网站类型，如果普通提取失败，会自动尝试使用无头浏览器：

```python
# 通过API调用，系统会自动处理
# 如果检测到需要JavaScript渲染的网站，会自动尝试使用无头浏览器
```

### 方法2：手动指定使用浏览器

如果需要强制使用无头浏览器，可以在代码中调用：

```python
from hunyuan_podcast.input_processor import InputProcessor

processor = InputProcessor()
# 强制使用无头浏览器
text = processor.extract_text_from_webpage(url, use_browser=True)
```

## 错误处理

### 如果 Playwright 未安装

如果系统检测到需要JavaScript渲染的网站，但 Playwright 未安装，会返回明确的错误提示：

```
需要安装playwright库才能提取需要JavaScript渲染的网页。安装方法: pip install playwright && playwright install chromium
```

### 如果提取失败

如果无头浏览器提取也失败，系统会提供以下建议：

1. **复制网页文本内容直接输入**：最简单可靠的方法
2. **使用"文字+指令"类型**：将文本内容粘贴到文本输入框
3. **安装playwright库后重试**：如果确定需要自动提取

## 性能说明

- **普通提取**：通常 1-3 秒
- **无头浏览器提取**：通常 5-15 秒（取决于网页加载速度）

## 最佳实践

1. **优先使用普通提取**：对于大多数网站，普通提取已经足够
2. **手动复制内容**：对于重要内容，建议手动复制文本内容，确保准确性
3. **安装 Playwright**：如果需要批量处理需要JavaScript渲染的网页，建议安装 Playwright

## 故障排除

### 问题1：Playwright 安装失败

**解决方案**：
- 确保网络连接正常（需要下载浏览器驱动）
- 尝试使用国内镜像：`pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple`
- 检查磁盘空间是否充足

### 问题2：无头浏览器提取超时

**解决方案**：
- 增加超时时间：`extract_text_from_webpage(url, timeout=60)`
- 检查网络连接
- 尝试手动复制内容

### 问题3：提取的内容不完整

**解决方案**：
- 检查网页是否需要登录
- 检查网页是否有反爬虫保护
- 尝试手动复制内容

## 技术细节

### 无头浏览器提取流程

1. 启动 Chromium 无头浏览器
2. 访问目标网页
3. 等待页面加载完成（等待网络空闲 + 额外2秒）
4. 尝试提取主要内容区域（main、article、content等）
5. 如果找不到，提取整个 body 内容
6. 关闭浏览器并返回文本

### 选择器优先级

系统会按以下顺序尝试提取内容：
1. `main` 标签
2. `article` 标签
3. 包含 "content" 的 class
4. 包含 "article" 的 class
5. 包含 "post" 的 class
6. 包含 "content" 的 id
7. 整个 `body` 标签

