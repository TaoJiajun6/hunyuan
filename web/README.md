# 混元AI播客生成系统 - Web端

这是混元AI播客生成系统的Web端应用，仿照鸿蒙应用的功能和设计，提供完整的播客生成功能。

## 功能特性

- 🎙️ **多角色互动播客**: 将文本素材转化为多角色自然互动的播客音频
- 👥 **自定义角色播客**: 根据用户自定义的角色人设和音色生成契合风格的播客音频
- 🎯 **主题深度播客**: 基于指定主题生成有深度、引发思考的播客音频
- 📁 **文件上传**: 支持上传文本文件和音频文件到云存储
- 📊 **实时进度**: 显示播客生成的实时进度
- 🎵 **音频播放**: 内置音频播放器，支持播放生成的播客

## 技术栈

- **React 18** - UI框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **React Router** - 路由管理
- **Tailwind CSS** - 样式框架
- **Axios** - HTTP客户端
- **Lucide React** - 图标库

## 项目结构

```
web/
├── src/
│   ├── components/          # 公共组件
│   │   └── AudioPlayer.tsx  # 音频播放器
│   ├── pages/              # 页面组件
│   │   ├── IndexPage.tsx   # 主页面（包含底部导航）
│   │   ├── PodcastPage.tsx # 播客主页
│   │   └── podcast/        # 播客功能页面
│   │       ├── MultiRolePage.tsx    # 多角色互动播客
│   │       ├── CharacterPage.tsx     # 自定义角色播客
│   │       └── DeepPage.tsx          # 主题深度播客
│   ├── services/           # 服务层
│   │   └── PodcastService.ts # API服务
│   ├── App.tsx             # 应用入口
│   ├── main.tsx            # 入口文件
│   └── index.css           # 全局样式
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## 安装和运行

### 前置要求

- Node.js >= 16.0.0
- npm 或 yarn

### 安装依赖

```bash
cd web
npm install
```

### 配置环境变量

创建 `.env` 文件（可选，默认使用云服务器地址）：

```env
VITE_API_BASE_URL=http://123.207.14.127:8000
```

**注意**：默认已配置为云服务器地址 `http://123.207.14.127:8000`，如需使用本地服务器，请在 `.env` 文件中覆盖。

### 开发模式

```bash
npm run dev
```

应用将在 `http://localhost:3000` 启动。

### 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist` 目录。

### 预览生产版本

```bash
npm run preview
```

## 使用说明

### 1. 多角色互动播客

1. 选择输入类型（文字、文件、公众号、网页等）
2. 根据输入类型提供相应的内容：
   - **文字**: 直接输入文本内容
   - **文件**: 上传文本文件（.txt, .doc, .docx, .pdf）
   - **公众号/网页**: 输入URL
3. 如果选择带"指令"的类型，可以输入指令内容
4. 为每个角色选择音色文件（音频文件）
5. （可选）选择播客分类
6. 点击"生成播客"按钮

### 2. 自定义角色播客

1. 输入文本素材（必需）
2. 配置角色信息：
   - 角色名称
   - 身份（可选）
   - 性格特点（可选）
   - 说话风格（可选）
   - 音色文件（必需）
3. 可以添加最多4个角色，至少需要2个角色
4. （可选）选择播客分类
5. 点击"生成播客"按钮

### 3. 主题深度播客

1. 输入播客主题（必需）
2. 选择角色数量（1-3个）
3. 选择深度级别（深度、中等、浅层）
4. 为每个角色选择音色文件（必需）
5. （可选）选择播客分类
6. 点击"生成播客"按钮

## API接口

Web端通过 `PodcastService` 与后端API通信，主要接口包括：

- `healthCheck()` - 健康检查
- `generateMultiRolePodcast()` - 生成多角色播客
- `generateCharacterPodcast()` - 生成自定义角色播客
- `generateDeepPodcast()` - 生成主题深度播客
- `analyzeTextForPodcast()` - 分析文本素材
- `uploadFile()` - 上传文件到云存储
- `getProgress()` - 获取任务进度
- `startProgressPolling()` - 启动进度轮询

## 与鸿蒙应用的对应关系

| 鸿蒙应用 | Web端 |
|---------|-------|
| `IndexPage.ets` | `IndexPage.tsx` |
| `PodcastPage.ets` | `PodcastPage.tsx` |
| `PodcastMultiRolePage.ets` | `MultiRolePage.tsx` |
| `PodcastCharacterPage.ets` | `CharacterPage.tsx` |
| `PodcastDeepPage.ets` | `DeepPage.tsx` |
| `PodcastService.ets` | `PodcastService.ts` |
| `MusicPlayController` | `AudioPlayer.tsx` |

## 开发注意事项

1. **API地址配置**: 默认使用 `http://localhost:8000`，可通过环境变量 `VITE_API_BASE_URL` 修改
2. **文件上传**: 所有文件（文本和音频）都需要先上传到云存储，获取URL后再调用生成接口
3. **进度轮询**: 使用HTTP轮询方式获取任务进度，默认每5秒轮询一次
4. **响应式设计**: 使用Tailwind CSS实现响应式布局，支持移动端和桌面端

## 待实现功能

- [ ] 音频播放器完整集成
- [ ] 最近播客列表从API获取
- [ ] 从云存储导入音频功能
- [ ] 上传背景音乐功能
- [ ] 搜索功能
- [ ] 用户设置页面

## 许可证

与主项目保持一致。

