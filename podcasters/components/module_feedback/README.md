# 意见反馈组件快速入门

## 目录

- [简介](#简介)
- [约束与限制](#约束与限制)
- [快速入门](#快速入门)
- [API参考](#API参考)
- [示例代码](#示例代码)

## 简介

本组件支持提交问题反馈、查看反馈记录。

| 意见反馈                                           | 反馈问题                                             | 反馈记录                                             |
|------------------------------------------------|--------------------------------------------------|--------------------------------------------------|
| <img src="./screenshots/menu.jpg" width="300"> | <img src="./screenshots/submit.jpg" width="300"> | <img src="./screenshots/record.jpg" width="300"> |

## 约束与限制

### 环境

- DevEco Studio版本：DevEco Studio 5.0.3 Release及以上
- HarmonyOS SDK版本：HarmonyOS 5.0.3 Release SDK及以上
- 设备类型：华为手机（包括双折叠和阔折叠）、平板
- 系统版本：HarmonyOS 5.0.1(13)及以上

## 快速入门

1. 安装组件。

   如果是在DevEco Studio使用插件集成组件，则无需安装组件，请忽略此步骤。

   如果是从生态市场下载组件，请参考以下步骤安装组件。

   a. 解压下载的组件包，将包中所有文件夹拷贝至您工程根目录的XXX目录下。

   b. 在项目根目录build-profile.json5添加module_feedback、module_imagepreview模块。

   ```
   // 项目根目录下build-profile.json5填写module_feedback、module_imagepreview路径。其中XXX为组件存放的目录名
   "modules": [
     {
       "name": "module_feedback",
       "srcPath": "./XXX/module_feedback"
     },
     {
       "name": "module_imagepreview",
       "srcPath": "./XXX/module_imagepreview"
     }
   ]
   ```

   c. 在项目根目录oh-package.json5添加依赖。
   ```
   // XXX为组件存放的目录名称
   "dependencies": {
     "module_feedback": "file:./XXX/module_feedback"
   }
   ```

2. 引入组件。

    ```
    import { RouterMap } from 'module_feedback';
    ```

## API参考

### 接口

由于本组件内流程闭环，以页面的方式注册并对外提供，不涉及API介绍。

### RouterMap枚举说明

**路由表枚举**

| 名称                        | 说明     |
|:--------------------------|:-------|
| FEEDBACK_PAGE             | 意见反馈页面 |
| FEEDBACK_RECORD_LIST_PAGE | 反馈记录页面 |
| FEEDBACK_SUBMIT_PAGE      | 反馈问题页面 |

## 示例代码

```ts
import { RouterMap, FeedbackModel } from 'module_feedback';

@Entry
@Preview
@ComponentV2
struct Sample1 {
  stack: NavPathStack = new NavPathStack()

  build() {
    Navigation(this.stack) {
      Column({ space: 10 }) {
        Text('意见反馈').fontSize(20).fontWeight(FontWeight.Bold)
        Button('跳转').width('100%').onClick(() => {
          this.stack.pushPath({
            name: RouterMap.FEEDBACK_PAGE,
            param: {
              windowTopPadding: 0,
              windowBottomPadding: 0,
              fontSizeRatio: 1,
            } as FeedbackModel,
          })
        })
      }
      .padding({
        left: 16,
        right: 16,
      })
    }
    .hideTitleBar(true)
    .mode(NavigationMode.Stack)
  }
}
```
