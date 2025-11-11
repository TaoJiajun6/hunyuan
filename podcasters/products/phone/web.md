# 集成SDK

更新时间: 2025-08-13 10:08







## 集成AGC及云存储SDK

1. [获取Web应用配置信息](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-storage-obtain-files-0000001275499192#section1078116446224)。

2. 复制“SDK代码片段”中的应用配置信息到您应用初始化阶段的代码中，例如<body>标记的底部。

3. 检查应用配置信息的"service > cloudstorage"中是否已默认配置default_storage。

   ```cangjie
   "cloudstorage":{    "default_storage":"您准备默认使用的存储实例名称",    "storage_url":"https://agc-storage-drcn.platform.dbankcloud.cn"  }
   ```

   如果未配置default_storage，将会导致云存储SDK初始化失败。请您手动添加缺省的存储实例名称，default_storage的值为“云开发（Serverless）> 云存储”页面中的“存储实例”对应的名称。

4. 如果您还没有package.json文件，可在JavaScript项目的根目录中运行以下命令进行创建。

   ```csharp
   npm init
   ```

   请按实际情况填写项目的配置信息。

5. 执行以下命令，安装AGC JS SDK到您的项目中，并将依赖添加到您项目中的package.json文件中。

   ```css
   npm install --save @hw-agconnect/cloudstorage@1.5.1
   ```

6. 执行以下命令，在您的项目中导入agc组件。

   ```javascript
   import agconnect from "@hw-agconnect/api";import "@hw-agconnect/cloudstorage";import "@hw-agconnect/instance";
   ```

7. 在您的应用初始化阶段调用agc的初始化方法，应用配置信息请参考

   获取Web应用配置信息

   。

   ```csharp
   var agConnectConfig =  {    //应用配置信息};//初始化agcagconnect.instance().configInstance(agConnectConfig);
   ```

# 初始化存储实例

更新时间: 2024-08-21 16:57







本文导读

展开章节

## 前提条件

- 您已[开通云存储服务](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-enable-service-0000001275330014)。
- 您已[集成云存储SDK](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-sdk-web-0000001054927608)。

## 操作步骤

如果您使用一个默认存储实例，在使用云存储服务前，需调用[agconnect.cloudStorage](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/overview-0000001054856767)初始化一个默认存储实例的[StorageManagement](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagemanagement-0000001055096686)对象。

```cpp
const storageManagement = agconnect.cloudStorage();
```

如果您要指定访问更多数据处理位置的存储实例，需调用[agconnect.cloudStorage(instance: AGCInstance, bucket: string)](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/overview-0000001054856767)方法使用指定的AGCInstance实例来初始化目标数据处理位置的[StorageManagement](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagemanagement-0000001055096686)对象。如下所示，以指定中国区为例：

```cangjie
let agConnectConfig = {//应用配置信息
}
// CNlet tagCN = 'cn';let insCN = agconnect.instance(tagCN);// 初始化AGCInstanceinsCN.configInstance(agConnectConfig);insCN.setOption({routePolicy: 1})// 匿名登录agconnect.auth(tagCN).signInAnonymously()// 初始化云存储实例const storageManagement = agconnect.cloudStorage(insCN, 'bucketFor
```

# 创建引用

更新时间: 2024-08-21 16:57







本文导读

展开章节

文件存储在云端的存储实例中，存储方式与本地硬盘中的文件系统类似。您可以通过文件的引用进行上传文件、获取文件的下载地址、删除文件、更新文件元数据等操作，也可以通过创建目录的引用来获取该目录下的文件列表。

## 前提条件

- 您已[开通云存储服务](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-enable-service-0000001275330014)。
- 您已[初始化存储实例](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-storage-initialize-bucket-web-0000001333920769)。

## 操作步骤

初始化成功后，您可通过调用[StorageManagement.storageReference](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagemanagement-0000001055096686#section012312924313)创建[StorageReference](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagereference-0000001055216725)对象的引用。

```cpp
// storageManagement为已经初始化的cloudStorage实例const reference = storageManagement.storageReference();
```

您也可以通过调用[StorageManagement.storageReference](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagemanagement-0000001055096686#section012312924313)传入一个完整的云端文件的地址来创建一个[StorageReference](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagereference-0000001055216725)对象的引用。

## 更多信息

创建引用后，您可以使用[StorageReference](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagereference-0000001055216725)实例的相关方法对引用进行相关操作：

- 在当前文件层次结构中向上向下导航，例如调用[child](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagereference-0000001055216725#section012312924313)获取子目录引用，调用[parent](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagereference-0000001055216725#section763894642219)属性获取父目录引用，调用[root](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagereference-0000001055216725#section763894642219)属性获取根目录引用。
- 获取当前引用的相关信息，例如调用[bucket](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagereference-0000001055216725#section763894642219)获取文件所在存储实例名称，调用[name](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagereference-0000001055216725#section763894642219)获取当前引用的文件或目录名称，调用[path](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagereference-0000001055216725#section763894642219)获取文件在云端的存储路径。
- 对文件进行[上传](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-upload-web-0000001055406166)、[删除](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-delete-web-0000001054966221)、[下载地址的获取](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-download-web-0000001055326213)和[元数据管理](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-metadata-web-0000001054766195)等操作。

# 上传文件

更新时间: 2024-08-21 16:57







本文导读

展开章节

通过云存储SDK，您可以快速上传本地设备上的文件或字符串到云端，同时可以对上传任务进行管理，如取消上传任务、监听上传任务中产生的事件等。

## 前提条件

- 您已[开通云存储服务](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-enable-service-0000001275330014)。
- 您已[初始化存储实例](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-storage-initialize-bucket-web-0000001333920769)。

## 上传本地文件

您可以通过引用操作本地设备上的文件，将文件上传到云端的存储实例中。

1. 调用

   StorageManagement.storageReference

   方法创建待上传文件的引用，将本地文件传入到预先规划的云端地址中。

   ```csharp
   var storageReference = storage.storageReference();var reference = storageReference.child('images/demo.jpg');
   ```

   说明

   - 上传文件时，会对云端文件的名称和大小进行严格的检查，具体限制请参见[使用限制](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-restrictions-0000001093263535#section1759375325210)。
   - 待上传文件最大为50GB。若上传任务异常中断，云存储SDK会根据设置的最大重试次数进行重试上传。因JavaScript SDK主要集成在Web服务器上给浏览器使用，因浏览器本身原因，在加载大文件时，可能会因加载失败而导致上传失败，您可尝试重新上传。

2. 调用

   StorageReference.put

   将文件上传到存储实例中。

   说明

   上传文件前支持您设置文件的自定义属性，具体请参见[元数据管理](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-metadata-web-0000001054766195)。

   ```csharp
   var uploadTask = reference.put(file); // file通过File实例化出来的对象
   ```

   如果您需要在上传文件时为文件指定自定义属性，可以使用[put](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storagereference-0000001055216725#section9814182519119)(data: File | Uint8Array | ArrayBuffer, attribute ?: UploadMetadata)方法中的UploadMetadata属性。

3. 使用put方法上传文件后，会返回包含上传任务的[UploadTask](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/uploadtask-0000001054975317)实例，您可以通过监听UploadTask的状态了解上传任务的相关状态，具体请参见[处理上传任务的事件](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-upload-web-0000001055406166#section864919101209)。

## 上传字符串

您可以通过引用操作一串编码后的字符串，将该数据作为文件内容上传到AGC云端的存储实例中。

1. 调用

   StorageManagement.storageReference

   创建需上传文件的引用，传入文件在云端预先规划的文件地址。

   ```csharp
   var storageReference = storage.storageReference();var reference = storageReference.child('images/demo.jpg');
   ```

2. 调用

   StorageReference.putString

   将文件上传到存储实例中。

   ```csharp
   var message = '待上传至云端的文件内容';var uploadTask = reference.putString(message);
   ```

3. 使用putString方法上传字符串后，会返回包含上传任务的

   UploadTask

   实例，您可以通过监听UploadTask的状态了解上传任务的相关状态。

   说明

   文件上传过程中如需对任务进行操作，请参见[处理上传任务的事件](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-upload-web-0000001055406166#section864919101209)。

## 处理上传任务的事件

文件在正常上传过程中，可通过调用[UploadTask](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/uploadtask-0000001054975317)类的[cancel](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/uploadtask-0000001054975317#section142543812159)方法切换上传任务的状态或调用[catch](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/uploadtask-0000001054975317#section18762102326)、[on](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/uploadtask-0000001054975317#section14770136133418)方法监听上传任务中的事件。

- cancel：取消一个上传任务。
- catch：捕获上传任务中产生的异常。
- on：监听上传任务中产生的事件。

```javascript
uploadTask.on('state_changed', function (snapshot) {    var progress = (snapshot.bytesTransferred / snapshot.totalByteCount) * 100    switch (snapshot.state) {        case agc.storage.TaskState.PAUSED: // or 'paused'            break        case agc.storage.TaskState.RUNNING: // or 'running'            break        }     }, function (error) {     }, function () {});uploadTask.cancel();uploadTask.catch();
```

## 更多信息

- 如您在上传文件前未设置文件的自定义属性，可在文件成功上传后进行[设置](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-metadata-web-0000001054766195#section164351295193)。
- 文件成功上传到云端后，您可以通过云存储SDK[获取文件的下载地址](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-download-web-0000001055326213)。
- 您可以通过云存储SDK的API[列举云端某个目录下的所有文件或子目录](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-list-web-0000001055126209)。
- 当您不再需要云端的文件时，可以调用云存储SDK的API在应用客户端[删除文件](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-delete-web-0000001054966221)。
- 除了在应用客户端通过云存储SDK的API来上传文件，您还可以直接[在AGC控制台以可视化的方式来上传文件](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-storage-manage-file-0000001281134398#section6704135012516)。

# 获取文件的下载地址

更新时间: 2024-08-21 16:57







本文导读

展开章节

文件上传到云端后，您可以通过云存储SDK获取云端文件的下载地址。

## 前提条件

- 您已[开通云存储服务](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-enable-service-0000001275330014)。
- 您已[初始化存储实例](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-storage-initialize-bucket-web-0000001333920769)。
- 您已[上传文件](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-upload-web-0000001055406166)。

## 操作步骤

说明

在下载文件前，您可以先[获取文件的元数据](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-cloudstorage-metadata-web-0000001054766195#ZH-CN_TOPIC_0000001054766195__li779174573913)，查看后再决定是否要下载文件。

1. 调用

   StorageManagement.storageReference

   创建需要下载文件的引用。

   ```csharp
   var storageReference = storage.storageReference();var reference = storageReference.child('images/demo.jpg');
   ```

2. 调用

   StorageReference.getDownloadURL

   获取下载地址。

   ```javascript
   reference.getDownloadURL().then(function(downloadURL){}).catch((err) => {});
   ```

3. 您可以通过将上一步获取的下载地址拷贝到浏览器的导航窗口体验文件的下载。

## 更多信息

除了在应用客户端通过云存储SDK的API来获取文件的下载地址，您还可以直接[在AGC控制台以可视化的方式来下载文件](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-storage-manage-file-0000001281134398#section116002011710)。



