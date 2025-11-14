# 鸿蒙应用API适配说明

## 概述

本文档说明鸿蒙应用如何适配Cloud Studio API服务器，包括配置、使用和故障排查。

## 配置说明

### 1. API地址配置

在 `PodcastService.ets` 中配置API地址：

```typescript
export class PodcastConfig {
  // Cloud Studio端口转发地址
  static readonly API_BASE_URL: string = 'https://hfrsgm--8000.ap-guangzhou.cloudstudio.work';
  static readonly API_TIMEOUT: number = 600000; // 10分钟超时
  static readonly USE_CLOUD_FUNCTION: boolean = false;
}
```

### 2. 获取Cloud Studio地址

1. 查看浏览器地址栏：`https://hfrsgm.ap-guangzhou.cloudstudio.work/`
2. 提取SPACE_KEY（hfrsgm）和REGION（ap-guangzhou）
3. 构建API地址：`https://hfrsgm--8000.ap-guangzhou.cloudstudio.work`

## API适配特性

### 1. 自动URL规范化

- 自动移除末尾斜杠
- 统一URL格式处理
- 支持HTTPS和HTTP

### 2. 参数验证

所有API接口都包含完整的参数验证：

#### 多角色播客
- 文本内容不能为空
- 至少需要一个角色的音色文件
- 新增可选参数：
  - `podcast_name`: 播客名称
  - `topic`: 本期主题
  - `character_1_name`: 角色1名称
  - `character_1_personality`: 角色1性格特点
  - `character_1_speaking_style`: 角色1说话风格
  - `character_2_name`: 角色2名称
  - `character_2_personality`: 角色2性格特点
  - `character_2_speaking_style`: 角色2说话风格
  - `character_3_name`: 角色3名称
  - `character_3_personality`: 角色3性格特点
  - `character_3_speaking_style`: 角色3说话风格
  - `scene_types`: 互动场景类型列表（如：["接梗玩梗的轻松交流", "立场冲突的激烈辩论"]）

#### 自定义角色播客
- 至少需要2个角色，最多4个角色
- 角色名称和音色文件不能为空

#### 主题深度播客
- 主题不能为空
- 角色数量必须在1-3个之间
- 深度级别必须是：深度、中等或浅层
- 角色音色数量必须与角色数量一致

### 3. Base64数据处理

自动处理base64编码的音频数据：
- 自动移除数据URI前缀（如 `data:audio/wav;base64,xxx`）
- 只保留纯base64字符串
- 支持标准base64和数据URI两种格式

### 4. 统一错误处理

所有API调用都使用统一的错误处理机制：
- 网络错误处理
- HTTP状态码处理
- JSON解析错误处理
- 详细的错误日志记录

### 5. 日志记录

详细的日志记录包括：
- 请求URL
- 请求体大小
- 响应状态
- 错误信息

## 使用示例

### 1. 健康检查

```typescript
const podcastService = PodcastService.getInstance();
const isHealthy = await podcastService.healthCheck();
if (isHealthy) {
  console.log('API服务器连接正常');
} else {
  console.error('API服务器连接失败');
}
```

### 2. 生成多角色播客

```typescript
const request: MultiRoleRequest = {
  text: '播客文本内容',
  role_voices: {
    '角色A': 'base64编码的音频数据',
    '角色B': 'base64编码的音频数据'
  },
  silence_interval: 300,
  // 以下为可选参数
  podcast_name: '科技前沿',
  topic: 'AI技术的发展',
  character_1_name: '主持人',
  character_1_personality: '外向幽默、喜欢开玩笑',
  character_1_speaking_style: '语速较快，常用网络流行语',
  character_2_name: '专家',
  character_2_personality: '理性严谨、善于分析',
  character_2_speaking_style: '语速平稳，逻辑性强',
  scene_types: ['接梗玩梗的轻松交流', '立场冲突的激烈辩论']
};

const result = await podcastService.generateMultiRolePodcast(request);
if (result.success && result.data) {
  // 处理成功结果
  const audioBase64 = result.data.audio_base64;
  const script = result.data.script;
} else {
  // 处理错误
  console.error(result.error);
}
```

### 2.1 分析文本素材（新增）

```typescript
const request: AnalyzeTextRequest = {
  text: '要分析的文本素材'
};

const result = await podcastService.analyzeTextForPodcast(request);
if (result.success && result.data) {
  // 处理分析结果
  const podcastName = result.data.podcast_name;
  const topic = result.data.topic;
  const characters = result.data.characters;
  const sceneTypes = result.data.scene_types;
  
  // 可以使用分析结果填充多角色播客请求参数
  const multiRoleRequest: MultiRoleRequest = {
    text: '播客文本内容',
    role_voices: {
      '角色A': 'base64编码的音频数据',
      '角色B': 'base64编码的音频数据'
    },
    podcast_name: podcastName,
    topic: topic,
    character_1_name: characters[0]?.name,
    character_1_personality: characters[0]?.personality,
    character_1_speaking_style: characters[0]?.speaking_style,
    character_2_name: characters[1]?.name,
    character_2_personality: characters[1]?.personality,
    character_2_speaking_style: characters[1]?.speaking_style,
    scene_types: sceneTypes
  };
} else {
  // 处理错误
  console.error(result.error);
}
```

### 3. 生成自定义角色播客

```typescript
const request: CharacterRequest = {
  characters: [
    {
      name: '角色A',
      identity: 'AI研究员',
      personality: '严谨',
      voice: 'base64编码的音频数据'
    },
    {
      name: '角色B',
      identity: '科技记者',
      personality: '幽默',
      voice: 'base64编码的音频数据'
    }
  ],
  topic: '人工智能的未来',
  silence_interval: 300
};

const result = await podcastService.generateCharacterPodcast(request);
```

### 4. 生成主题深度播客

```typescript
const request: DeepPodcastRequest = {
  topic: '人工智能对社会的影响',
  role_voices: {
    '角色A': 'base64编码的音频数据',
    '角色B': 'base64编码的音频数据'
  },
  num_characters: 2,
  depth_level: '深度',
  silence_interval: 300
};

const result = await podcastService.generateDeepPodcast(request);
```

## 新增功能

### 文本自动分析

新增了文本分析功能，可以自动分析文本素材并推断出播客相关信息：

- **端点**: `/api/v1/podcast/analyze`
- **方法**: `analyzeTextForPodcast()`
- **功能**: 
  - 自动推断播客名称
  - 自动推断本期主题
  - 自动推断角色设定（2-4个角色）
  - 自动推断互动场景类型
- **使用场景**: 
  - 用户输入文本后，可以调用分析功能自动填充播客参数
  - 提升用户体验，减少手动输入

## API端点更新

### 多角色播客端点

- **端点**: `/api/v1/podcast/multi_role`
- **新增参数**: 
  - `podcast_name`: 播客名称（可选）
  - `topic`: 本期主题（可选）
  - `character_1_name`: 角色1名称（可选）
  - `character_1_personality`: 角色1性格特点（可选）
  - `character_1_speaking_style`: 角色1说话风格（可选）
  - `character_2_name`: 角色2名称（可选）
  - `character_2_personality`: 角色2性格特点（可选）
  - `character_2_speaking_style`: 角色2说话风格（可选）
  - `character_3_name`: 角色3名称（可选）
  - `character_3_personality`: 角色3性格特点（可选）
  - `character_3_speaking_style`: 角色3说话风格（可选）
  - `scene_types`: 互动场景类型列表（可选）

### 文本分析端点（新增）

- **端点**: `/api/v1/podcast/analyze`
- **方法**: POST
- **请求参数**:
  - `text`: 要分析的文本素材
- **返回结果**:
  - `podcast_name`: 播客名称
  - `topic`: 本期主题
  - `characters`: 角色设定列表
  - `scene_types`: 互动场景类型列表

## 文件大小限制

### 客户端限制
- 音色文件：最大10MB（在FileUtils.ets中检查）
- 超过限制会显示提示信息

### 服务器限制
- 音频文件：最大50MB
- 请求体：最大100MB
- 超过限制会返回HTTP 413错误

## 错误处理

### 常见错误类型

1. **网络错误**
   - 无法连接到服务器
   - 超时错误
   - 连接中断

2. **参数错误**
   - 参数验证失败
   - 缺少必需参数
   - 参数格式错误

3. **服务器错误**
   - HTTP 4xx错误（客户端错误）
   - HTTP 5xx错误（服务器错误）
   - 文件大小超过限制

4. **解析错误**
   - JSON解析失败
   - 响应格式错误

### 错误处理示例

```typescript
const result = await podcastService.generateMultiRolePodcast(request);
if (!result.success) {
  // 显示错误信息
  console.error('错误类型:', result.error);
  console.error('错误消息:', result.message);
  
  // 根据错误类型处理
  if (result.error?.includes('网络')) {
    // 处理网络错误
  } else if (result.error?.includes('参数')) {
    // 处理参数错误
  } else if (result.error?.includes('文件大小')) {
    // 处理文件大小错误
  }
}
```

## 性能优化

### 1. 超时设置
- 默认超时：10分钟（600000毫秒）
- 可以根据网络情况调整

### 2. 文件大小优化
- 使用压缩的音频格式（如MP3）
- 限制音色文件大小（建议5-10MB）
- 避免上传过大的文件

### 3. 并发处理
- 避免同时发送多个请求
- 使用队列管理请求
- 显示加载状态

## 故障排查

### 1. 无法连接到服务器

**问题**: 健康检查失败

**解决方案**:
- 检查API_BASE_URL配置是否正确
- 检查网络连接是否正常
- 检查Cloud Studio服务器是否运行
- 检查防火墙设置

### 2. 请求超时

**问题**: 请求超时错误

**解决方案**:
- 增加API_TIMEOUT时间
- 检查网络连接稳定性
- 检查服务器性能
- 优化文件大小

### 3. 文件上传失败

**问题**: 文件上传时出现错误

**解决方案**:
- 检查文件大小是否超过限制
- 检查文件格式是否支持
- 检查base64编码是否正确
- 查看服务器日志

### 4. 参数验证失败

**问题**: 参数验证错误

**解决方案**:
- 检查必需参数是否提供
- 检查参数格式是否正确
- 检查参数值是否有效
- 查看错误消息详情

### 5. 解析响应失败

**问题**: JSON解析错误

**解决方案**:
- 检查响应格式是否正确
- 检查响应内容是否完整
- 查看服务器日志
- 检查网络连接

## 测试建议

### 1. 单元测试
- 测试参数验证
- 测试错误处理
- 测试URL构建

### 2. 集成测试
- 测试API连接
- 测试数据上传
- 测试响应解析

### 3. 端到端测试
- 测试完整流程
- 测试错误场景
- 测试性能

## 更新日志

### v1.1.0 (2024-01-XX)
- 新增文本自动分析功能
- 多角色播客支持播客名称、主题、角色设定、场景类型等可选参数
- 新增 `/api/v1/podcast/analyze` 端点
- 改进提示词生成逻辑，支持完整的播客结构生成
- 支持音效标注和音频制作备注

### v1.0.0 (2024-01-XX)
- 初始版本
- 支持Cloud Studio API适配
- 添加参数验证
- 添加统一错误处理
- 添加详细日志记录

## 参考资源

- [Cloud Studio部署指南](../CLOUD_STUDIO_DEPLOYMENT.md)
- [API服务器文档](../hunyuan_podcast/api_server.py)
- [HarmonyOS网络开发文档](https://developer.harmonyos.com/)

## 支持

如有问题，请查看：
- 项目文档
- API服务器日志
- HarmonyOS开发文档

