# AI播客鸿蒙APP使用说明

## 功能概述

本APP基于混元AI播客生成系统，提供了三个主要的播客生成功能：

1. **多角色互动播客**：将文本素材转化为多角色自然互动的播客音频
2. **自定义角色播客**：根据用户自定义的角色人设和音色生成契合风格的播客音频
3. **主题深度播客**：基于指定主题生成有深度、引发思考的播客音频

## 配置说明

### 方式一：使用Cloud Studio（推荐，支持GPU加速）

#### 1. 在Cloud Studio中部署API服务器

1. 登录腾讯云Cloud Studio，创建或打开工作空间
2. 上传项目代码到Cloud Studio
3. 安装依赖和模型文件（参考项目根目录的INSTALL.md）
4. 启动API服务器：

```bash
# 方式1: 直接运行（前台）
python run_api_server.py --host 0.0.0.0 --port 8000 --fp16 --cuda_kernel

# 方式2: 使用启动脚本（后台运行，推荐）
bash start_api_server_cloudstudio.sh
```

#### 2. 获取端口转发地址

Cloud Studio会自动显示端口转发地址，格式为：
```
https://${SPACE_KEY}--8000.${REGION}.cloudstudio.work/
```

**获取方式**：
1. 查看浏览器地址栏，找到类似：`https://hfrsgm.ap-guangzhou.cloudstudio.work/`
2. 提取两部分：
   - SPACE_KEY: `hfrsgm`（浏览器地址中的第一段）
   - REGION: `ap-guangzhou`（浏览器地址中的第二段）
3. 构建预览地址：`https://hfrsgm--8000.ap-guangzhou.cloudstudio.work/`

**示例**：
- 浏览器地址：`https://hfrsgm.ap-guangzhou.cloudstudio.work/`
- API地址：`https://hfrsgm--8000.ap-guangzhou.cloudstudio.work/`

#### 3. 配置APP使用Cloud Studio API

在 `podcasters/components/lib_api/src/main/ets/services/PodcastService.ets` 文件中，修改配置：

```typescript
export class PodcastConfig {
  // 使用Cloud Studio端口转发地址
  static readonly API_BASE_URL: string = 'https://hfrsgm--8000.ap-guangzhou.cloudstudio.work';
  static readonly API_TIMEOUT: number = 600000; // 10分钟超时（考虑大文件上传和生成时间）
  static readonly USE_CLOUD_FUNCTION: boolean = false; // 使用直接连接模式
}
```

**Cloud Studio的优势**：
- 支持GPU加速，生成速度快
- 提供HTTPS加密传输
- 公网访问，手机可直接调用
- 24/7运行，无需本地服务器
- 自动端口转发，配置简单

### 方式二：使用华为AGC云函数

#### 1. 部署云函数

1. 进入 `podcasters/cloud_function_package` 目录
2. 将 `podcast-cloud.js` 和 `package.json` 上传到华为AGC云函数
3. 安装依赖：在云函数控制台执行 `npm install`，或上传 `node_modules.zip` 并解压
4. 配置环境变量：
   - `BACKEND_API_URL`: 后端API服务器地址（例如：`https://hfrsgm--8000.ap-guangzhou.cloudstudio.work`）
5. 配置HTTP触发器，获取云函数URL

#### 2. 配置APP使用云函数

在 `podcasters/components/lib_api/src/main/ets/services/PodcastService.ets` 文件中，修改配置：

```typescript
export class PodcastConfig {
  // 使用云函数URL
  static readonly API_BASE_URL: string = 'https://your-cloud-function-url.com';
  static readonly API_TIMEOUT: number = 600000; // 10分钟超时
  static readonly USE_CLOUD_FUNCTION: boolean = true; // 启用云函数模式
}
```

**云函数的优势**：
- 统一管理API密钥和配置
- 更好的安全性和访问控制
- 客户端无需知道后端服务器地址
- 支持HTTPS加密传输

### 方式三：直接使用本地/远程API服务器

#### 1. 配置后端API地址

在 `podcasters/components/lib_api/src/main/ets/services/PodcastService.ets` 文件中，修改 `PodcastConfig.API_BASE_URL` 为您的后端服务器地址：

```typescript
export class PodcastConfig {
  // 将此处替换为您的实际服务器地址
  static readonly API_BASE_URL: string = 'http://10.10.210.52:8000';
  static readonly API_TIMEOUT: number = 600000; // 10分钟超时
  static readonly USE_CLOUD_FUNCTION: boolean = false; // 使用直接连接模式
}
```

**重要提示**：
- 如果使用本地服务器，请确保手机和电脑在同一局域网内
- 如果是真机调试，请使用电脑的局域网IP地址（不是localhost或127.0.0.1）
- 如果使用远程服务器，请确保服务器地址可以访问

#### 2. 启动后端API服务

在项目根目录下启动后端API服务：

```bash
# 启动API服务（CPU模式）
python run_api_server.py --host 0.0.0.0 --port 8000

# 启动API服务（GPU模式，如果有GPU）
python run_api_server.py --host 0.0.0.0 --port 8000 --fp16 --cuda_kernel
```

确保后端服务正常运行后，访问 http://localhost:8000/health 检查服务状态。

### 3. 配置网络权限

APP已经配置了必要的网络权限：
- `ohos.permission.INTERNET`：网络访问权限
- `ohos.permission.GET_NETWORK_INFO`：获取网络信息权限

## 使用流程

### 1. 多角色互动播客

1. 进入APP，点击"AI办公"标签
2. 点击"AI播客"卡片
3. 选择"多角色互动播客"
4. 输入播客文本（支持角色标记如`[角色A]你好 [角色B]你好啊`或普通文本）
5. 为每个角色选择音色文件（WAV格式推荐）
6. 点击"开始生成"按钮
7. 等待生成完成后，可以播放音频和查看脚本

### 2. 自定义角色播客

1. 进入"自定义角色播客"页面
2. 输入播客主题（可选）
3. 为每个角色配置：
   - 角色名称
   - 身份/职业（可选）
   - 核心性格（可选）
   - 选择音色文件
4. 点击"开始生成"按钮

### 3. 主题深度播客

1. 进入"主题深度播客"页面
2. 输入播客主题
3. 选择角色数量（2个或3个）
4. 选择深度级别（深度/中等/浅层）
5. 为每个角色选择音色文件
6. 点击"开始生成"按钮

## 音色文件要求

- **推荐格式**：WAV格式
- **文件大小**：最大10MB（APP会自动检查文件大小）
- **音频质量**：清晰、无噪音的音频文件效果更好
- **时长**：建议5-30秒的音频片段

**文件大小限制**：
- 客户端限制：10MB（APP会自动检查并提示）
- 服务器限制：50MB（超过限制会返回错误）
- Base64编码后文件会增大约33%，请注意实际传输大小

## 注意事项

1. **网络连接**：
   - 如果使用Cloud Studio，确保手机可以访问公网
   - 如果使用本地服务器，确保手机和服务器在同一网络
   - 如果使用远程服务器，确保服务器地址可以访问
2. **生成时间**：播客生成可能需要较长时间（通常1-5分钟），请耐心等待
3. **文件大小**：音色文件限制10MB，超过限制会提示错误
4. **文件选择**：目前使用DocumentViewPicker选择文件
5. **音频播放**：生成的音频使用HarmonyOS的AVPlayer播放，确保设备支持音频播放
6. **超时设置**：API超时时间设置为10分钟，如果生成时间较长可能需要等待

## 故障排查

### 1. 无法连接到服务器

- 检查服务器是否正常运行
- 检查API_BASE_URL配置是否正确
- 检查手机和服务器是否在同一网络
- 检查防火墙设置

### 2. 文件选择失败

- 确保已授予文件访问权限
- 尝试使用其他文件选择方式
- 检查文件格式是否支持

### 3. 音频播放失败

- 检查音频数据是否完整
- 检查设备是否支持音频播放
- 查看错误日志获取详细错误信息

## 开发说明

### 项目结构

```
podcasters/
├── components/
│   └── lib_api/
│       └── src/main/ets/services/
│           └── PodcastService.ets    # 播客API服务
├── products/phone/src/main/ets/
│   ├── pages/podcast/               # 播客相关页面
│   │   ├── PodcastPage.ets          # 播客主页
│   │   ├── PodcastMultiRolePage.ets # 多角色播客页面
│   │   ├── PodcastCharacterPage.ets # 自定义角色播客页面
│   │   ├── PodcastDeepPage.ets      # 主题深度播客页面
│   │   └── PodcastResultPage.ets    # 播客结果页面
│   ├── components/
│   │   └── AudioPlayer.ets          # 音频播放器组件
│   └── utils/
│       └── FileUtils.ets            # 文件工具类
```

### API接口说明

所有API接口定义在 `PodcastService.ets` 中：

- `healthCheck()`: 健康检查
- `generateMultiRolePodcast()`: 生成多角色播客
- `generateCharacterPodcast()`: 生成自定义角色播客
- `generateDeepPodcast()`: 生成主题深度播客

### 云函数部署说明

详细的云函数部署和使用说明，请参考 `podcasters/cloud_function_package/README.md` 文件。

云函数作为代理层，具有以下特点：
- 统一管理后端API服务器地址
- 提供HTTPS加密传输
- 支持CORS跨域请求
- 简化客户端配置

### 扩展开发

如需扩展功能，可以：

1. 添加新的播客生成类型
2. 优化音频播放器功能
3. 添加播客历史记录功能
4. 添加播客分享功能
5. 优化文件选择体验

## 许可证

本项目基于混元AI播客生成系统开发，请遵循相应的许可证要求。

