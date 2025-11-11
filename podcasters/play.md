# efaudio音乐播放器封装组件

eftool的音频相关封装包，封装了常用的播放、暂停、快进、设置url等功能，提供快捷操作方法。

音频音乐播放器

## 简介

ef_audio是`eftool`的音频相关组件包。

## ️包含组件

|     模块      |                  介绍                  |
| :-----------: | :------------------------------------: |
|  EfAVPlayer   |  提供eftool封装AVPlayer的常规使用功能  |
| EfAudioPlayer | 基于AVPlayer封装的极简的音乐播放器组件 |

## 使用EfAVPlayer

EfAVPlayer 针对 AVPlayer的不同状态封装了常见的 API。初始化、播放、暂停、停止、释放资源等。支持 url、fdSrc、dataSrc三种资源路径。

### 1.在项目中引入插件

```javascript
import { EfAVPlayer} from '@yunkss/ef_audio'
```

### 2.实例化

```vbnet
efAVPlay: EfAVPlayer = new EfAVPlayer()
```

### 3.初始化

需要注意，init是异步的，需要加上 await 使用。 如 await this.efAVPlay.init()

```kotlin
this.efAVPlay.init()
```

### 4.设置播放的url

```kotlin
this.efAVPlay.setUrl("https://env-00jxhf99mujs.normal.cloudstatic.cn/play/0.m4a")
```

#### 基本示例

```undefined
EfAVPlayerIndex
```

#### 播放器示例

实现了播放、暂停、音量大小调整、循环播放、列表播放、随机播放、单曲播放等功能

## 使用EfAudioPlayer

### 1. 功能介绍

1. 播放&暂停
2. 上一首&下一首
3. 单曲播放&列表播放&循环播放&随机播放
4. 音量大小调整
5. 播放进度调整

### 2.在项目中引入组件

```javascript
import { EfAudioPlayer} from '@yunkss/ef_audio'
```

### 3.使用组件

```jsx
import { promptAction } from '@kit.ArkUI'
import { EfAudioPlayer } from '../Index'
import { SongItemUrl } from '../src/main/ets/ui/Ef_audio_player/type'


interface SongItem {
 title: string
 url: SongItemUrl
}

@Component
export struct EfAudioPlayDemo {
 @State
 songList: SongItem[] = [
   {
     title: "直到世界的尽头",
     url: 'https://wsy997.obs.cn-east-3.myhuaweicloud.com/simple_audio%E7%B4%A0%E6%9D%90/0.m4a',
   },
   {
     title: '画',
     url: 'https://wsy997.obs.cn-east-3.myhuaweicloud.com/simple_audio%E7%B4%A0%E6%9D%90/1.mp3',
   },
   {
     title: 'Sweet Dreams',
     url: 'https://wsy997.obs.cn-east-3.myhuaweicloud.com/simple_audio%E7%B4%A0%E6%9D%90/2.mp3',
   },
   {
     title: '奢香夫人',
     url: 'https://wsy997.obs.cn-east-3.myhuaweicloud.com/simple_audio%E7%B4%A0%E6%9D%90/0.m4a',
   }
 ]
 @State
 songPlayIndex: number = 0
 @State
 volume: number = 1

 build() {
   Column() {
     EfAudioPlayer({
       songList: this.songList.map(v => v.url),
       songPlayIndex: this.songPlayIndex,
       onVolumnChange: (v) => {
         promptAction.showToast({ message: `音量改变` + v })
       },
       onTimeUpdate: (t => {
         // promptAction.showToast({ message: `${t}` })
       }),
       onPaused: () => {
         promptAction.showToast({ message: `暂停了` })
       },
       onPlay: () => {
         promptAction.showToast({ message: `播放了` })
       },
       onPlayModeIndex: (mode) => {
         promptAction.showToast({ message: `播放模式改变${mode}` })
       },
       onMuted: () => {
         promptAction.showToast({ message: `静音了` })
       },
       onError: (stateError) => {
         AlertDialog.show({ message: JSON.stringify(stateError, null, 2) })
       },
       onPlayIndexChange: (index) => {
         promptAction.showToast({ message: `歌曲序号${index}` })
       },
       onNext: (index) => {
         promptAction.showToast({ message: `下一首${index}` })
       },

       onPrevious: (index) => {
         promptAction.showToast({ message: `上一首${index}` })
       },
       onStateChange: (state) => {
         promptAction.showToast({ message: `播放状态${state}` })
       },
       onSeek: (time) => {
         promptAction.showToast({ message: `${time}` })
       }
     })

   }
   .width("100%")
   .height("100%")
   .justifyContent(FlexAlign.Center)
 }
}
```

### 4. Props

|   属性   |     类型      |                             说明                             |
| :------: | :-----------: | :----------------------------------------------------------: |
| songList | SongItemUrl[] |                       要播放的歌曲列表                       |
|  volume  |    number     |                    音量属性 0-1 包含小数                     |
| isMuted  |    boolean    |                           是否静音                           |
| efAVPlay |  EfAVPlayer   | [ef_auido 核心类](https://ohpm.openharmony.cn/#/cn/detail/@yunkss%2Fef_audio) |

### 5. event

|       事件        |     说明     |
| :---------------: | :----------: |
|      onNext       |    下一首    |
|    onPrevious     |    上一首    |
|      onMuted      |     静音     |
|      onError      |   错误监听   |
|   onTimeUpdate    |   实时播放   |
|  onVolumnChange   |   音量调整   |
| onPlayIndexChange |   歌曲切换   |
|      onSeek       |   播放进度   |
|     onPaused      |     暂停     |
|      onPlay       |     播放     |
|  onPlayModeIndex  | 播放模式改变 |
|   onStateChange   | 播放状态改变 |