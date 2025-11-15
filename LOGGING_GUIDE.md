# 日志导出指南

## 功能说明

系统现在支持将日志同时输出到控制台和文件，方便查看和导出日志。

## 日志文件位置

日志文件默认保存在项目根目录下的 `logs` 文件夹中：

```
项目根目录/
  └── logs/
      ├── api_server.log          # API服务器日志
      ├── api_server.log.1        # 日志备份文件
      ├── upload_client.log       # 上传客户端日志
      └── upload_client.log.1     # 日志备份文件
```

## 日志配置

### 默认配置

- **日志级别**: INFO
- **单个文件最大大小**: 10MB
- **保留备份数量**: 5个
- **日志格式**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### 日志轮转

当日志文件达到最大大小（10MB）时，会自动创建新的日志文件：
- `podcast.log` - 当前日志文件
- `podcast.log.1` - 最新的备份
- `podcast.log.2` - 次新的备份
- ... 最多保留5个备份文件

## 查看日志

### 方法1：直接查看日志文件

```bash
# Windows PowerShell
Get-Content logs\api_server.log -Tail 50

# Linux/Mac
tail -f logs/api_server.log
```

### 方法2：使用文本编辑器

直接用文本编辑器（如记事本、VS Code等）打开日志文件查看。

### 方法3：搜索日志内容

```bash
# Windows PowerShell - 搜索错误日志
Select-String -Path logs\*.log -Pattern "ERROR"

# Linux/Mac
grep -r "ERROR" logs/
```

## 自定义日志配置

如果需要自定义日志配置，可以修改 `hunyuan_podcast/log_config.py` 中的 `setup_logging` 函数调用：

```python
from hunyuan_podcast.log_config import setup_logging

# 自定义配置
setup_logging(
    log_dir="custom_logs",      # 自定义日志目录
    log_file="my_app.log",       # 自定义日志文件名
    max_bytes=20 * 1024 * 1024, # 20MB
    backup_count=10,            # 保留10个备份
    level=logging.DEBUG          # DEBUG级别
)
```

## 日志文件说明

### api_server.log

包含API服务器的所有日志，包括：
- 请求和响应信息
- 播客生成过程
- 错误和警告信息
- 性能统计

### upload_client.log

包含上传客户端的日志，包括：
- 文件上传进度
- 上传成功/失败信息
- 网络错误和重试信息
- 上传速度统计

## 注意事项

1. **日志文件大小**: 默认单个文件最大10MB，超过后会自动轮转
2. **日志保留**: 默认保留5个备份文件，旧的日志文件会被自动删除
3. **日志目录**: 如果 `logs` 目录不存在，系统会自动创建
4. **编码**: 日志文件使用UTF-8编码，支持中文

## 导出日志

### 导出特定时间段的日志

```bash
# Windows PowerShell - 导出今天的日志
Get-Content logs\api_server.log | Where-Object { $_ -match "2025-11-15" } | Out-File today.log

# Linux/Mac
grep "2025-11-15" logs/api_server.log > today.log
```

### 导出错误日志

```bash
# Windows PowerShell
Select-String -Path logs\*.log -Pattern "ERROR" | Out-File errors.log

# Linux/Mac
grep "ERROR" logs/*.log > errors.log
```

## 清理日志

如果需要清理旧的日志文件：

```bash
# Windows PowerShell
Remove-Item logs\*.log.*

# Linux/Mac
rm logs/*.log.*
```

注意：删除备份文件不会影响当前的日志文件，系统会继续记录新的日志。

