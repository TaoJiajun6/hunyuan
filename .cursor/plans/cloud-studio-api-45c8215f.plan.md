<!-- 45c8215f-155d-4a54-beee-1812e12bc3b8 0a6959ab-025d-41f0-9ee7-564561bfb0ee -->
# Cloud Studio API服务器部署和鸿蒙应用集成方案

## 项目目标

1. 在Cloud Studio中部署混元AI播客生成API服务器
2. 鸿蒙应用通过HTTPS端口转发直接调用Cloud Studio API
3. 优化文件上传流程，支持音频文件上传到Cloud Studio后端

## 当前架构分析

### 文件上传流程（已实现）

- 用户选择音频文件 → FileUtils.pickAudioFile()
- 读取为Uint8Array → fs.readSync()
- 转换为base64 → FileUtils.uint8ArrayToBase64()
- 通过JSON请求体发送 → role_voices字段
- API服务器解码 → decode_base64_audio()

### 需要解决的问题

1. Cloud Studio端口转发地址配置
2. HTTPS访问支持
3. 大文件上传优化（当前base64方式可用，但需添加大小限制）
4. 超时时间调整（大文件+生成时间）
5. 错误处理和用户反馈

## 实施步骤

### 阶段1: API服务器端配置

#### 1.1 修改API服务器启动脚本

文件: `run_api_server.py`

- 添加GPU自动检测和配置（--fp16 --cuda_kernel）
- 添加Cloud Studio环境检测
- 自动显示端口转发访问地址
- 显示GPU信息和配置建议

#### 1.2 优化API服务器配置

文件: `hunyuan_podcast/api_server.py`

- 验证CORS配置（已支持*）
- 添加请求大小限制配置
- 添加文件大小验证（限制50MB）
- 添加请求日志记录
- 优化错误处理

#### 1.3 创建Cloud Studio启动脚本

文件: `start_api_server_cloudstudio.sh` (新建)

- 配置环境变量
- 设置GPU使用
- 添加后台运行支持（nohup）
- 添加日志输出

### 阶段2: 鸿蒙前端配置更新

#### 2.1 更新API地址配置

文件: `podcasters/components/lib_api/src/main/ets/services/PodcastService.ets`

- 修改API_BASE_URL为Cloud Studio端口转发地址格式
- 支持HTTPS协议
- 添加配置说明（如何获取SPACE_KEY和REGION）
- 增加超时时间到600秒（10分钟）

#### 2.2 优化文件上传处理

文件: `podcasters/products/phone/src/main/ets/utils/FileUtils.ets`

- 添加文件大小检查（限制10MB）
- 添加文件大小提示
- 优化错误处理

#### 2.3 优化API调用

文件: `podcasters/components/lib_api/src/main/ets/services/PodcastService.ets`

- 增加超时时间
- 添加请求重试机制（可选）
- 优化错误处理和日志

### 阶段3: 文档更新

#### 3.1 更新现有文档

文件: `podcasters/PODCAST_README.md`, `podcasters/QUICK_START.md`

- 添加Cloud Studio部署说明
- 更新API地址配置步骤
- 添加端口转发地址构建说明

#### 3.2 创建部署文档

文件: `CLOUD_STUDIO_DEPLOYMENT.md` (新建)

- Cloud Studio环境准备
- API服务器部署步骤
- 端口转发配置
- 鸿蒙应用配置
- 故障排查指南

### 阶段4: 测试验证

#### 4.1 API服务器测试

- 测试启动和GPU使用
- 测试端口转发访问
- 测试文件上传（小、中、大文件）

#### 4.2 鸿蒙应用测试

- 测试HTTPS连接
- 测试文件上传
- 测试三种播客生成功能
- 测试错误处理

## 关键技术点

### 1. 端口转发地址格式

```
https://${SPACE_KEY}--8000.${REGION}.cloudstudio.work/
```

示例: `https://hfrsgm--8000.ap-guangzhou.cloudstudio.work/`

获取方式：

- 从浏览器地址栏: `https://hfrsgm.ap-guangzhou.cloudstudio.work/`
- 提取SPACE_KEY: `hfrsgm`
- 提取REGION: `ap-guangzhou`
- 端口: `8000`

### 2. 文件上传方式

当前使用base64编码方式：

- 优点: 实现简单，无需额外端点
- 缺点: 文件增大33%
- 优化: 添加文件大小限制（客户端10MB，服务器50MB）

### 3. HTTPS访问

- Cloud Studio端口转发提供HTTPS
- API服务器内部使用HTTP（0.0.0.0:8000）
- CORS已配置支持所有来源

### 4. GPU配置

- 自动检测GPU
- 使用FP16精度
- 使用CUDA内核加速

### 5. 会话保持

- 使用nohup后台运行
- 添加日志输出到文件

## 文件修改清单

### 需要修改的文件

1. `run_api_server.py` - Cloud Studio环境检测和GPU配置
2. `hunyuan_podcast/api_server.py` - 文件大小验证和日志
3. `podcasters/components/lib_api/src/main/ets/services/PodcastService.ets` - API地址和超时
4. `podcasters/products/phone/src/main/ets/utils/FileUtils.ets` - 文件大小检查
5. `podcasters/PODCAST_README.md` - 添加部署说明
6. `podcasters/QUICK_START.md` - 更新配置步骤

### 需要新建的文件

1. `start_api_server_cloudstudio.sh` - 启动脚本
2. `CLOUD_STUDIO_DEPLOYMENT.md` - 部署文档

## 配置说明

### API服务器配置

- 端口: 8000
- 主机: 0.0.0.0
- GPU: 自动检测（--fp16 --cuda_kernel）
- 文件大小限制: 50MB

### 鸿蒙前端配置

- API地址: `https://${SPACE_KEY}--8000.${REGION}.cloudstudio.work`
- 超时时间: 600秒（10分钟）
- 文件大小限制: 10MB

## 文件上传流程

1. 用户选择文件（FileUtils.pickAudioFile）
2. 检查文件大小（限制10MB）
3. 读取为Uint8Array
4. 转换为base64
5. 通过HTTPS发送到Cloud Studio API
6. 服务器验证并解码
7. 生成播客音频
8. 返回base64编码的音频

## 注意事项

1. 安全: Cloud Studio端口转发是公开的
2. 稳定性: 配置后台运行
3. 资源: 监控GPU和内存使用
4. 文件大小: 限制文件大小避免超时
5. 超时设置: 根据实际需求调整
6. 错误处理: 添加详细错误提示

## 验证步骤

1. Cloud Studio环境: 启动API服务器，获取端口转发地址
2. 鸿蒙应用配置: 更新API_BASE_URL，测试HTTPS连接
3. 文件上传测试: 测试不同大小的文件
4. 播客生成测试: 测试三种播客生成功能
5. 错误处理测试: 测试各种错误情况

### To-dos

- [ ] 修改run_api_server.py添加Cloud Studio环境检测和端口转发地址显示
- [ ] 创建start_api_server_cloudstudio.sh启动脚本，支持后台运行和GPU配置
- [ ] 更新PodcastService.ets，修改API_BASE_URL配置为Cloud Studio端口转发地址格式
- [ ] 更新PODCAST_README.md和QUICK_START.md，添加Cloud Studio部署说明
- [ ] 创建CLOUD_STUDIO_DEPLOYMENT.md详细部署文档
- [ ] 测试API服务器在Cloud Studio中的启动和访问
- [ ] 测试鸿蒙前端通过HTTPS访问Cloud Studio API服务器