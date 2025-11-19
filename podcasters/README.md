# AI播客生成鸿蒙应用

基于混元大模型和SoulX-Podcast的AI播客生成HarmonyOS应用。

## 功能概述

本应用提供了三个主要的播客生成功能：

1. **多角色互动播客**：将文本素材转化为多角色自然互动的播客音频
2. **自定义角色播客**：根据用户自定义的角色人设和音色生成契合风格的播客音频
3. **主题深度播客**：基于指定主题生成有深度、引发思考的播客音频

## 约束与限制

### 环境

* DevEco Studio版本：DevEco Studio 5.0.5 Release及以上
* HarmonyOS SDK版本：HarmonyOS 5.0.5 Release SDK及以上
* 设备类型：华为手机（包括双折叠和阔折叠）、平板
* HarmonyOS版本：HarmonyOS 5.0.5(17)及以上

### 权限

* 网络权限：`ohos.permission.INTERNET`
* 麦克风权限：`ohos.permission.MICROPHONE`（可选，用于录制音色）
* 文件访问权限：用于选择音色文件

## 快速入门

### 配置工程

在运行此应用前，需要完成以下配置：

#### 1. 配置应用包名

1. 在[AppGallery Connect](https://developer.huawei.com/consumer/cn/doc/app/agc-help-create-atomic-service-0000002247795706)创建应用
2. 获取APP ID和包名
3. 将模板工程根目录下`AppScope/app.json5`文件中的`bundleName`替换为创建应用的包名

#### 2. 配置后端API地址

在`components/lib_api/src/main/ets/services/PodcastService.ets`中配置后端API地址：

```typescript
export class PodcastConfig {
  // Cloud Studio部署（推荐）
  static readonly API_BASE_URL: string = 'https://your-space-key--8000.your-region.cloudstudio.work';
  
  // 或本地/远程服务器
  // static readonly API_BASE_URL: string = 'http://your-api-server:8000';
  
  static readonly API_TIMEOUT: number = 600000; // 10分钟超时
  static readonly USE_CLOUD_FUNCTION: boolean = false; // 是否使用云函数
}
```

**推荐方式：使用Cloud Studio部署**

1. 在腾讯云Cloud Studio中部署后端API服务器（参考项目根目录的`部署说明.md`）
2. 获取端口转发地址（格式：`https://${SPACE_KEY}--8000.${REGION}.cloudstudio.work`）
3. 在APP中配置API地址

详细说明请参考：[PODCAST_README.md](PODCAST_README.md)

#### 3. 配置应用签名

对应用进行[手工签名](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-signing#section297715173233)。

### 运行调试工程

1. 用USB线连接调试手机和PC
2. 点击"Run"，运行模板工程

## 使用流程

### 多角色互动播客

1. 进入APP
2. 点击"AI播客"卡片
3. 选择"多角色互动播客"
4. 输入播客文本（支持角色标记如`[角色A]你好 [角色B]你好啊`或普通文本）
5. 为每个角色选择音色文件（WAV格式推荐）
6. 点击"开始生成"按钮
7. 等待生成完成后，可以播放音频和查看脚本

### 自定义角色播客

1. 进入"自定义角色播客"页面
2. 输入播客主题（可选）
3. 为每个角色配置：
   - 角色名称
   - 身份/职业（可选）
   - 核心性格（可选）
   - 说话风格（可选）
   - 选择音色文件
4. 点击"开始生成"按钮

### 主题深度播客

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

## 项目结构

```
podcasters/
├── components/                     # 组件库
│   ├── lib_api/                   # API服务组件
│   │   └── src/main/ets/services/
│   │       └── PodcastService.ets # 播客API服务
│   ├── lib_common/                # 通用组件
│   ├── lib_widget/                # UI组件库
│   └── ...
├── products/phone/src/main/       # 手机产品
│   └── ets/
│       ├── pages/
│       │   ├── podcast/           # 播客相关页面
│       │   │   ├── PodcastPage.ets          # 播客主页
│       │   │   ├── PodcastMultiRolePage.ets # 多角色播客页面
│       │   │   ├── PodcastCharacterPage.ets # 自定义角色播客页面
│       │   │   ├── PodcastDeepPage.ets      # 主题深度播客页面
│       │   │   └── PodcastResultPage.ets    # 播客结果页面
│       │   └── office/
│       │       └── OfficePage.ets # 办公主页（包含播客入口）
│       ├── components/
│       │   └── AudioPlayer.ets    # 音频播放器组件
│       └── utils/
│           └── FileUtils.ets      # 文件工具类
└── ...
```

## API接口说明

所有API接口定义在`components/lib_api/src/main/ets/services/PodcastService.ets`中：

- `healthCheck()`: 健康检查
- `generateMultiRolePodcast()`: 生成多角色播客
- `generateCharacterPodcast()`: 生成自定义角色播客
- `generateDeepPodcast()`: 生成主题深度播客

## 注意事项

1. **网络连接**：确保手机可以访问后端API服务器
2. **生成时间**：播客生成可能需要较长时间（通常1-5分钟），请耐心等待
3. **文件大小**：音色文件限制10MB，超过限制会提示错误
4. **超时设置**：API超时时间设置为10分钟，如果生成时间较长可能需要等待

## 相关文档

- [详细使用说明](PODCAST_README.md) - 完整的使用说明和配置指南
- [快速开始指南](QUICK_START.md) - 快速启动指南
- [实现总结](IMPLEMENTATION_SUMMARY.md) - 技术实现总结
- [项目根目录README](../README.md) - 项目总体说明
