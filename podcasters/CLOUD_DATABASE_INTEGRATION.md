# 鸿蒙端侧云数据库集成文档

## 概述

本文档说明如何在鸿蒙端侧对接AGC云数据库和云存储，实现播客数据的查询和管理。

## 前提条件

1. 已在AGC控制台创建云数据库服务
2. 已在AGC控制台创建存储区（Zone）
3. 已在AGC控制台创建PodcastInfo对象类型
4. 已导出schema.json文件并放置在项目中

## 文件结构

### 新增文件

1. **schema.json** (`podcasters/AppScope/resources/rawfile/schema.json`)
   - 云数据库对象类型定义文件
   - 定义了PodcastInfo对象类型及其字段

2. **PodcastInfo.ets** (`podcasters/components/lib_api/src/main/ets/database/PodcastInfo.ets`)
   - 播客信息对象类型定义
   - 继承自`cloudDatabase.DatabaseObject`
   - 包含所有播客字段的定义和辅助方法

3. **CloudDatabaseService.ets** (`podcasters/components/lib_api/src/main/ets/services/CloudDatabaseService.ets`)
   - 云数据库访问服务类
   - 提供查询、保存、删除等操作

### 修改文件

1. **PodcastService.ets** (`podcasters/components/lib_api/src/main/ets/services/PodcastService.ets`)
   - 添加了从云数据库获取播客列表的方法
   - 添加了`PodcastListItem`接口定义

2. **EntryAbility.ets** (`podcasters/products/phone/src/main/ets/entryability/EntryAbility.ets`)
   - 在`onCreate`方法中初始化云数据库服务

3. **Index.ets** (`podcasters/components/lib_api/Index.ets`)
   - 导出云数据库相关的服务和类型

## 配置说明

### 1. 存储区名称配置

在`CloudDatabaseService.ets`中配置存储区名称：

```typescript
export class CloudDatabaseConfig {
  /**
   * 存储区名称
   * 需要在AGC控制台创建对应的存储区
   */
  static readonly ZONE_NAME: string = 'cloudDBZone'; // 根据实际情况修改
}
```

### 2. 网络权限

网络权限已在`module.json5`中配置：

```json5
"requestPermissions": [
  {
    "name": "ohos.permission.INTERNET"
  }
]
```

## 使用方法

### 1. 初始化云数据库服务

云数据库服务会在应用启动时自动初始化（在`EntryAbility.onCreate`中）。如果需要手动初始化：

```typescript
import { cloudDatabaseService } from 'lib_api';

// 初始化云数据库服务
cloudDatabaseService.initialize();
```

### 2. 查询播客列表

#### 从云数据库查询（推荐）

```typescript
import { podcastService } from 'lib_api';

// 查询所有播客
const podcasts = await podcastService.getPodcastListFromCloudDB();

// 查询指定数量的播客
const podcasts = await podcastService.getPodcastListFromCloudDB(20);

// 按分类查询
const podcasts = await podcastService.getPodcastListFromCloudDB(20, '科学与科技');
```

#### 从API服务器查询（备用方案）

```typescript
import { podcastService } from 'lib_api';

// 从云数据库获取播客列表（仅支持云数据库）
const podcasts = await podcastService.getPodcastList(20, '科学与科技');
```

#### 自动选择数据源（推荐）

```typescript
import { podcastService } from 'lib_api';

// 优先从云数据库获取，失败则从API获取
const podcasts = await podcastService.getPodcastList(20, '科学与科技', true);
```

### 3. 根据ID查询播客详情

```typescript
import { podcastService } from 'lib_api';

const podcast = await podcastService.getPodcastById('1765456637495_835634');
if (podcast) {
  console.log(`标题: ${podcast.title}`);
  console.log(`音频URL: ${podcast.audio_url}`);
  console.log(`角色: ${podcast.roles?.join(', ')}`);
}
```

### 4. 直接使用云数据库服务

如果需要更细粒度的控制，可以直接使用`CloudDatabaseService`：

```typescript
import { cloudDatabaseService } from 'lib_api';

// 查询所有播客
const result = await cloudDatabaseService.queryAllPodcasts(20);

// 根据标题查询（模糊匹配）
const result = await cloudDatabaseService.queryPodcastsByTitle('鸿蒙', 10);

// 根据分类查询
const result = await cloudDatabaseService.queryPodcastsByCategory('科学与科技', 10);

// 随机查询（用于推荐）
const result = await cloudDatabaseService.queryRandomPodcasts(10);

// 根据ID查询
const podcast = await cloudDatabaseService.queryPodcastById('1765456637495_835634');

// 保存播客
const podcast = new PodcastInfo();
podcast.id = '1765456637495_835634';
podcast.title = '鸿蒙应用开发与仓颉编程语言探索';
podcast.audio_url = 'https://...';
podcast.created_at = Date.now();
podcast.setRolesArray(['林深', '苏浅']);
await cloudDatabaseService.upsertPodcast(podcast);

// 删除播客
await cloudDatabaseService.deletePodcastById('1765456637495_835634');
```

## 数据结构

### PodcastListItem接口

```typescript
export interface PodcastListItem {
  id: string;                    // 播客ID（主键）
  title: string;                 // 播客标题
  audio_url?: string;            // 音频文件URL（云存储地址）
  local_file?: string;           // 本地文件名
  created_at: number;            // 创建时间戳（Unix时间戳）
  duration?: number;             // 播客时长（秒）
  category?: string;             // 播客分类
  status?: string;               // 播客状态（如：completed, processing等）
  script?: string;              // 播客脚本内容
  file_size_mb?: number;         // 文件大小（MB）
  topic?: string;               // 播客主题
  roles?: string[];             // 角色列表
  content?: string;              // 内容预览（script的前100字符）
}
```

### PodcastInfo对象类型

`PodcastInfo`继承自`cloudDatabase.DatabaseObject`，包含以下字段：

- `id: string` - 播客ID（主键）
- `title: string` - 播客标题
- `audio_url: string` - 音频文件URL
- `local_file: string` - 本地文件名
- `created_at: number` - 创建时间戳（Long类型）
- `duration: number` - 播客时长（Long类型）
- `category: string` - 播客分类
- `status: string` - 播客状态
- `script: string` - 播客脚本内容（Text类型）
- `file_size_mb: number` - 文件大小（Double类型）
- `topic: string` - 播客主题
- `roles: string` - 角色列表（JSON字符串格式）

### 辅助方法

`PodcastInfo`提供了以下辅助方法：

```typescript
// 将roles字符串解析为数组
getRolesArray(): string[]

// 将roles数组转换为JSON字符串
setRolesArray(roles: string[]): void

// 获取内容预览（script的前100个字符）
getContentPreview(): string
```

## 查询示例

### 简单查询

```typescript
// 查询所有播客
const result = await cloudDatabaseService.queryAllPodcasts();
```

### 条件查询

```typescript
// 按分类查询
const result = await cloudDatabaseService.queryPodcastsByCategory('科学与科技', 20);

// 按标题模糊查询
const result = await cloudDatabaseService.queryPodcastsByTitle('鸿蒙', 10);
```

### 复合查询

如果需要更复杂的查询条件，可以直接使用`DatabaseQuery`：

```typescript
import { cloudDatabase } from '@kit.CloudFoundationKit';
import { PodcastInfo } from 'lib_api';

const condition = new cloudDatabase.DatabaseQuery(PodcastInfo);
condition.equalTo('category', '科学与科技')
  .greaterThan('created_at', 1700000000)
  .orderByDesc('created_at')
  .limit(20);

const result = await cloudDatabaseService.queryAllPodcasts();
```

## 注意事项

1. **存储区数量限制**：云数据库最多创建4个存储区，超过4个会导致访问失败。

2. **数据同步**：云数据库查询是直接从云侧服务器查询数据，本地不会缓存数据。

3. **权限配置**：确保在AGC控制台正确配置了对象类型的权限（Read、Upsert、Delete）。

4. **字段类型匹配**：
   - String、Text对应`string`
   - Boolean对应`boolean`
   - Byte、ByteArray对应`Uint8Array`
   - Short、Integer、Long、Float、Double对应`number`
   - Date对应`Date`

5. **roles字段**：roles字段在数据库中存储为JSON字符串，使用`getRolesArray()`和`setRolesArray()`方法进行转换。

6. **错误处理**：所有数据库操作都应该进行错误处理，避免应用崩溃。

## 故障排查

### 1. 数据库初始化失败

- 检查网络连接
- 检查存储区名称是否正确
- 检查AGC控制台是否已创建存储区

### 2. 查询返回空列表

- 检查AGC控制台是否有数据
- 检查权限配置是否正确
- 检查对象类型名称是否匹配

### 3. 保存失败

- 检查必填字段是否都已设置
- 检查主键（id）是否已设置
- 检查权限配置是否包含Upsert权限

## 相关文档

- [鸿蒙端侧访问云数据库.md](../鸿蒙端侧访问云数据库.md)
- [AGC云数据库官方文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/cloudfoundation-database-initialize)

