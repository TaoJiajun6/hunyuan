# Cloud Studio部署指南

本文档详细说明如何在腾讯云Cloud Studio中部署混元AI播客生成API服务器，并通过鸿蒙应用调用。

## 目录

- [环境准备](#环境准备)
- [项目部署](#项目部署)
- [API服务器启动](#api服务器启动)
- [端口转发配置](#端口转发配置)
- [鸿蒙应用配置](#鸿蒙应用配置)
- [测试验证](#测试验证)
- [故障排查](#故障排查)
- [性能优化](#性能优化)

## 环境准备

### 1. Cloud Studio工作空间

1. 登录[腾讯云Cloud Studio](https://cloudstudio.net/)
2. 创建新的工作空间或打开现有工作空间
3. 选择GPU模板（如果可用）或标准模板

### 2. 系统要求

- Python 3.8+
- CUDA（如果使用GPU）
- 足够的内存和存储空间（建议至少8GB内存，20GB存储）

### 3. 检查GPU可用性

```bash
# 检查GPU是否可用
python -c "import torch; print(f'CUDA可用: {torch.cuda.is_available()}')"

# 查看GPU信息
nvidia-smi
```

## 项目部署

### 1. 上传项目代码

1. 使用Git克隆项目：
   ```bash
   git clone https://github.com/your-username/hunyuan.git
   cd hunyuan
   ```

2. 或者使用Cloud Studio的文件上传功能上传项目代码

### 2. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 如果使用uv环境
cd index-tts
uv pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 设置HuggingFace镜像（可选）
export HF_ENDPOINT="https://hf-mirror.com"

# 设置API密钥（从环境变量或配置文件读取）
export SILICONFLOW_API_KEY="your-api-key"
```

### 4. 下载模型文件

确保IndexTTS-2模型文件已下载并放置在正确的位置：
- 模型目录：`index-tts/models/`
- 配置文件：`index-tts/configs/`

## API服务器启动

### 方式一：使用启动脚本（推荐）

```bash
# 赋予执行权限
chmod +x start_api_server_cloudstudio.sh

# 启动服务器（后台运行）
bash start_api_server_cloudstudio.sh
```

启动脚本会自动：
- 检测GPU并配置GPU参数
- 设置环境变量
- 后台运行API服务器
- 生成日志文件

### 方式二：直接运行

```bash
# CPU模式
python run_api_server.py --host 0.0.0.0 --port 8000

# GPU模式（推荐）
python run_api_server.py --host 0.0.0.0 --port 8000 --fp16 --cuda_kernel
```

### 方式三：使用nohup后台运行

```bash
# 创建日志目录
mkdir -p logs

# 后台运行
nohup python run_api_server.py --host 0.0.0.0 --port 8000 --fp16 --cuda_kernel > logs/api_server.log 2>&1 &

# 查看日志
tail -f logs/api_server.log
```

### 启动参数说明

- `--host 0.0.0.0`: 监听所有网络接口
- `--port 8000`: API服务端口（Cloud Studio端口转发使用此端口）
- `--fp16`: 使用FP16精度（GPU加速，减少显存占用）
- `--cuda_kernel`: 使用CUDA内核加速（进一步提速）

## 端口转发配置

### 1. 获取端口转发地址

Cloud Studio会自动提供端口转发服务，地址格式为：
```
https://${SPACE_KEY}--${PORT}.${REGION}.cloudstudio.work/
```

### 2. 查找SPACE_KEY和REGION

**方法1：从浏览器地址栏获取**
- 查看浏览器地址栏，找到类似：`https://hfrsgm.ap-guangzhou.cloudstudio.work/`
- 提取SPACE_KEY：`hfrsgm`（第一段）
- 提取REGION：`ap-guangzhou`（第二段）

**方法2：从环境变量获取**
```bash
# 查看环境变量
echo $X_IDE_SPACE_KEY
echo $REGION

# 或者查看所有Cloud Studio相关环境变量
env | grep -i cloud
```

**方法3：从启动日志获取**
- 启动API服务器后，查看启动日志
- 日志中会自动显示端口转发地址

### 3. 构建API地址

根据获取的SPACE_KEY和REGION，构建API地址：
```
https://${SPACE_KEY}--8000.${REGION}.cloudstudio.work/
```

**示例**：
- SPACE_KEY: `hfrsgm`
- REGION: `ap-guangzhou`
- 端口: `8000`
- API地址: `https://hfrsgm--8000.ap-guangzhou.cloudstudio.work/`

### 4. 验证端口转发

在浏览器中访问：
- 健康检查: `https://hfrsgm--8000.ap-guangzhou.cloudstudio.work/health`
- API文档: `https://hfrsgm--8000.ap-guangzhou.cloudstudio.work/docs`

如果能够访问，说明端口转发配置成功。

## 鸿蒙应用配置

### 1. 修改API地址

打开文件：`podcasters/components/lib_api/src/main/ets/services/PodcastService.ets`

修改`PodcastConfig`类中的`API_BASE_URL`：

```typescript
export class PodcastConfig {
  // 使用Cloud Studio端口转发地址
  static readonly API_BASE_URL: string = 'https://hfrsgm--8000.ap-guangzhou.cloudstudio.work';
  static readonly API_TIMEOUT: number = 600000; // 10分钟超时
  static readonly USE_CLOUD_FUNCTION: boolean = false;
}
```

### 2. 配置说明

- **API_BASE_URL**: Cloud Studio端口转发地址（HTTPS）
- **API_TIMEOUT**: 请求超时时间（10分钟，考虑大文件上传和生成时间）
- **USE_CLOUD_FUNCTION**: 设置为`false`（直接连接模式）

### 3. 网络权限

确保APP已配置网络权限（通常在`module.json5`中）：
```json
{
  "requestPermissions": [
    {
      "name": "ohos.permission.INTERNET"
    },
    {
      "name": "ohos.permission.GET_NETWORK_INFO"
    }
  ]
}
```

## 测试验证

### 1. API服务器测试

#### 健康检查
```bash
curl https://hfrsgm--8000.ap-guangzhou.cloudstudio.work/health
```

预期响应：
```json
{
  "status": "healthy",
  "service": "混元AI播客生成API"
}
```

#### API文档
在浏览器中访问：
```
https://hfrsgm--8000.ap-guangzhou.cloudstudio.work/docs
```

### 2. 鸿蒙应用测试

1. **编译运行APP**
   - 打开DevEco Studio
   - 导入项目
   - 配置签名
   - 运行应用

2. **测试API连接**
   - 打开APP
   - 进入播客生成页面
   - 尝试生成播客
   - 查看是否能够正常连接和生成

3. **测试文件上传**
   - 选择音色文件（小于10MB）
   - 上传文件
   - 检查是否成功

### 3. 性能测试

- **生成速度**: 测试播客生成时间
- **文件上传**: 测试不同大小的文件上传
- **并发请求**: 测试多个请求的并发处理

## 故障排查

### 1. 无法访问API服务器

**问题**: 浏览器无法访问端口转发地址

**解决方案**:
- 检查API服务器是否正在运行
- 检查端口是否正确（应该是8000）
- 检查SPACE_KEY和REGION是否正确
- 检查Cloud Studio的端口转发服务是否正常

### 2. GPU不可用

**问题**: 日志显示GPU不可用

**解决方案**:
- 检查Cloud Studio是否提供GPU资源
- 检查CUDA是否正确安装
- 检查PyTorch是否支持CUDA
- 使用CPU模式运行（去掉`--fp16`和`--cuda_kernel`参数）

### 3. 文件上传失败

**问题**: 文件上传时出现错误

**解决方案**:
- 检查文件大小是否超过10MB（客户端限制）
- 检查文件大小是否超过50MB（服务器限制）
- 检查网络连接是否稳定
- 检查API服务器日志查看详细错误

### 4. 生成失败

**问题**: 播客生成失败

**解决方案**:
- 检查API密钥是否正确配置
- 检查模型文件是否完整
- 检查服务器日志查看详细错误
- 检查GPU内存是否足够

### 5. 超时错误

**问题**: 请求超时

**解决方案**:
- 增加超时时间（修改`API_TIMEOUT`）
- 检查网络连接是否稳定
- 检查服务器性能是否足够
- 优化生成参数

## 性能优化

### 1. GPU加速

- 使用`--fp16`参数启用FP16精度
- 使用`--cuda_kernel`参数启用CUDA内核加速
- 确保GPU内存足够（建议至少8GB）

### 2. 文件大小优化

- 客户端限制：10MB
- 服务器限制：50MB
- 建议使用压缩的音频格式（如MP3）

### 3. 超时设置

- 客户端超时：10分钟（600000毫秒）
- 服务器超时：根据实际情况调整
- 考虑网络延迟和生成时间

### 4. 并发处理

- 根据需要调整uvicorn的worker数量
- 使用负载均衡（如果有多个实例）
- 监控服务器资源使用情况

## 安全注意事项

### 1. API密钥保护

- 不要在代码中硬编码API密钥
- 使用环境变量或配置文件存储密钥
- 定期更换API密钥

### 2. 访问控制

- Cloud Studio端口转发是公开的
- 考虑添加身份验证（如API Key）
- 限制访问频率（Rate Limiting）

### 3. 数据安全

- 传输的数据使用HTTPS加密
- 临时文件及时清理
- 敏感信息不要记录在日志中

## 监控和维护

### 1. 日志管理

- 定期查看日志文件
- 设置日志轮转（Log Rotation）
- 监控错误日志

### 2. 性能监控

- 监控CPU和GPU使用率
- 监控内存使用情况
- 监控API响应时间

### 3. 备份和恢复

- 定期备份配置文件
- 备份模型文件（如果需要）
- 准备恢复方案

## 常见问题

### Q1: Cloud Studio是否免费？

A: Cloud Studio提供免费和付费版本，GPU资源可能需要付费。

### Q2: 端口转发是否稳定？

A: Cloud Studio的端口转发服务通常是稳定的，但可能会因为工作空间关闭而中断。

### Q3: 如何保持服务运行？

A: 使用后台运行方式（nohup或启动脚本），确保工作空间不关闭。

### Q4: 如何更新代码？

A: 使用Git拉取最新代码，或直接上传新文件，然后重启API服务器。

### Q5: 如何查看运行状态？

A: 查看日志文件，或访问健康检查端点。

## 参考资源

- [Cloud Studio文档](https://cloudstudio.net/docs)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [HarmonyOS开发文档](https://developer.harmonyos.com/)
- [项目README](./README.md)

## 支持

如有问题，请查看：
- 项目Issue: [GitHub Issues](https://github.com/your-username/hunyuan/issues)
- 项目文档: [README](./README.md)
- Cloud Studio支持: [Cloud Studio Support](https://cloudstudio.net/support)

---

最后更新: 2024-01-XX






















