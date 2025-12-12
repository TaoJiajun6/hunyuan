# 混元生图（极速版）

最近更新时间：2025-09-12 01:07:46





*我的收藏*

## 本页目录：

- [1. 接口描述](https://cloud.tencent.com/document/product/1668/120721?from=console_document_search#1.-.E6.8E.A5.E5.8F.A3.E6.8F.8F.E8.BF.B0)

- [2. 输入参数](https://cloud.tencent.com/document/product/1668/120721?from=console_document_search#2.-.E8.BE.93.E5.85.A5.E5.8F.82.E6.95.B0)

- [3. 输出参数](https://cloud.tencent.com/document/product/1668/120721?from=console_document_search#3.-.E8.BE.93.E5.87.BA.E5.8F.82.E6.95.B0)

- 4. 示例

  - [示例1 调用示例](https://cloud.tencent.com/document/product/1668/120721?from=console_document_search#.E7.A4.BA.E4.BE.8B1-.E8.B0.83.E7.94.A8.E7.A4.BA.E4.BE.8B)

- 5. 开发者资源

  - [腾讯云 API 平台](https://cloud.tencent.com/document/product/1668/120721?from=console_document_search#.E8.85.BE.E8.AE.AF.E4.BA.91-API-.E5.B9.B3.E5.8F.B0)
  - [API Inspector](https://cloud.tencent.com/document/product/1668/120721?from=console_document_search#API-Inspector)
  - [SDK](https://cloud.tencent.com/document/product/1668/120721?from=console_document_search#SDK)
  - [命令行工具](https://cloud.tencent.com/document/product/1668/120721?from=console_document_search#.E5.91.BD.E4.BB.A4.E8.A1.8C.E5.B7.A5.E5.85.B7)

- [6. 错误码](https://cloud.tencent.com/document/product/1668/120721?from=console_document_search#6.-.E9.94.99.E8.AF.AF.E7.A0.81)

## 1. 接口描述

接口请求域名： aiart.tencentcloudapi.com 。

混元文生图接口，基于混元大模型，根据输入的文本描述智能生成图片
默认提供1个并发，代表最多能同时处理1个已提交的任务，上一个任务处理完毕后，才能开始处理下一个任务。

推荐使用 API Explorer

[点击调试](https://console.cloud.tencent.com/api/explorer?Product=aiart&Version=2022-12-29&Action=TextToImageLite)

API Explorer 提供了在线调用、签名验证、SDK 代码生成和快速检索接口等能力。您可查看每次调用的请求内容和返回结果以及自动生成 SDK 调用示例。

## 2. 输入参数

以下请求参数列表仅列出了接口请求参数和部分公共参数，完整公共参数列表见 [公共请求参数](https://cloud.tencent.com/document/api/1668/88071)。

| 参数名称       | 必选 | 类型                                                         | 描述                                                         |
| :------------- | :--- | :----------------------------------------------------------- | :----------------------------------------------------------- |
| Action         | 是   | String                                                       | [公共参数](https://cloud.tencent.com/document/api/1668/88071)，本接口取值：TextToImageLite。 |
| Version        | 是   | String                                                       | [公共参数](https://cloud.tencent.com/document/api/1668/88071)，本接口取值：2022-12-29。 |
| Region         | 是   | String                                                       | [公共参数](https://cloud.tencent.com/document/api/1668/88071)，详见产品支持的 [地域列表](https://cloud.tencent.com/document/api/1668/88071#.E5.9C.B0.E5.9F.9F.E5.88.97.E8.A1.A8)。 |
| Prompt         | 是   | String                                                       | 文本描述。将根据输入的文本智能生成与之相关的图像。 不能为空，推荐使用中文。最多可传1024个 utf-8 字符。 示例值：雨中, 竹林, 小路 |
| NegativePrompt | 否   | String                                                       | 反向提示词。 减少生成结果中出现描述内容。 推荐使用中文。最多可传1024个 utf-8 字符。 示例值：黑色 |
| Resolution     | 否   | String                                                       | 生成图分辨率，默认1024:1024。 支持的图像宽高比例: 1:1，3:4，4:3，9:16，16:9。 支持的长边分辨率: 160，200，225，258，512，520，608，768，1024，1080，1280，1600，1620，1920，2048，2400，2560，2592，3440，3840，4096。 示例值：1024:1024 |
| Seed           | 否   | Integer                                                      | 随机种子，默认随机。 0：随机种子生成。 不传：随机种子生成。 正数：固定种子生成。  示例值：1 |
| LogoAdd        | 否   | Integer                                                      | 为生成结果图添加标识的开关，默认为1。 1：添加标识。 0：不添加标识。 其他数值：默认按1处理。 建议您使用显著标识来提示结果图使用了 AI 绘画技术，是 AI 生成的图片。 示例值：1 |
| LogoParam      | 否   | [LogoParam](https://cloud.tencent.com/document/api/1668/88067#LogoParam) | 标识内容设置。 默认在生成结果图右下角添加“图片由 AI 生成”字样，您可根据自身需要替换为其他的标识图片。 示例值：{"LogoUrl": "https://cos.ap-guangzhou.myqcloud.com/logo.jpg", "LogoRect": {"X": 10, "Y": 10, "Width": 20, "Height": 20}} |
| RspImgType     | 否   | String                                                       | 返回图像方式（base64 或 url），二选一，默认为 base64。url 有效期为1小时。 示例值：url |

## 3. 输出参数

| 参数名称    | 类型    | 描述                                                         |
| :---------- | :------ | :----------------------------------------------------------- |
| ResultImage | String  | 根据入参 RspImgType 填入不同，返回不同的内容。 如果传入 base64 则返回生成图 Base64 编码。 如果传入 url 则返回的生成图 URL , 有效期1小时，请及时保存。 示例值：https://xxx.cos.ap-guangzhou.myqcloud.com/xxx.jpg |
| Seed        | Integer | Seed 示例值：1                                               |
| RequestId   | String  | 唯一请求 ID，由服务端生成，每次请求都会返回（若请求因其他原因未能抵达服务端，则该次请求不会获得 RequestId）。定位问题时需要提供该次请求的 RequestId。 |

## 4. 示例

### 示例1 调用示例

#### 输入示例



```
POST / HTTP/1.1
Host: aiart.tencentcloudapi.com
Content-Type: application/json
X-TC-Action: TextToImageLite
<公共请求参数>

{
    "Prompt": "小狗",
    "RspImgType": "url"
}
```



#### 输出示例



```json
{
    "Response": {
        "RequestId": "d5d96b7a-7fe3-4ea2-9dce-504e2c0d63cd",
        "ResultImage": "https://xxx.cos.ap-guangzhou.myqcloud.com/xxx.jpg",
        "Seed": 2068699513
    }
}
```



## 5. 开发者资源

### 腾讯云 API 平台

[腾讯云 API 平台](https://cloud.tencent.com/api) 是综合 API 文档、错误码、API Explorer 及 SDK 等资源的统一查询平台，方便您从同一入口查询及使用腾讯云提供的所有 API 服务。

### API Inspector

用户可通过 [API Inspector](https://cloud.tencent.com/document/product/1278/49361) 查看控制台每一步操作关联的 API 调用情况，并自动生成各语言版本的 API 代码，也可前往 [API Explorer](https://cloud.tencent.com/document/product/1278/46697) 进行在线调试。

### SDK

云 API 3.0 提供了配套的开发工具集（SDK），支持多种编程语言，能更方便的调用 API。

- Tencent Cloud SDK 3.0 for Python: [CNB](https://cnb.cool/tencent/cloud/api/sdk/tencentcloud-sdk-python/-/blob/master/tencentcloud/aiart/v20221229/aiart_client.py), [GitHub](https://github.com/TencentCloud/tencentcloud-sdk-python/blob/master/tencentcloud/aiart/v20221229/aiart_client.py), [Gitee](https://gitee.com/TencentCloud/tencentcloud-sdk-python/blob/master/tencentcloud/aiart/v20221229/aiart_client.py)
- Tencent Cloud SDK 3.0 for Java: [CNB](https://cnb.cool/tencent/cloud/api/sdk/tencentcloud-sdk-java/-/blob/master/src/main/java/com/tencentcloudapi/aiart/v20221229/AiartClient.java), [GitHub](https://github.com/TencentCloud/tencentcloud-sdk-java/blob/master/src/main/java/com/tencentcloudapi/aiart/v20221229/AiartClient.java), [Gitee](https://gitee.com/TencentCloud/tencentcloud-sdk-java/blob/master/src/main/java/com/tencentcloudapi/aiart/v20221229/AiartClient.java)
- Tencent Cloud SDK 3.0 for PHP: [CNB](https://cnb.cool/tencent/cloud/api/sdk/tencentcloud-sdk-php/-/blob/master/src/TencentCloud/Aiart/V20221229/AiartClient.php), [GitHub](https://github.com/TencentCloud/tencentcloud-sdk-php/blob/master/src/TencentCloud/Aiart/V20221229/AiartClient.php), [Gitee](https://gitee.com/TencentCloud/tencentcloud-sdk-php/blob/master/src/TencentCloud/Aiart/V20221229/AiartClient.php)
- Tencent Cloud SDK 3.0 for Go: [CNB](https://cnb.cool/tencent/cloud/api/sdk/tencentcloud-sdk-go/-/blob/master/tencentcloud/aiart/v20221229/client.go), [GitHub](https://github.com/TencentCloud/tencentcloud-sdk-go/blob/master/tencentcloud/aiart/v20221229/client.go), [Gitee](https://gitee.com/TencentCloud/tencentcloud-sdk-go/blob/master/tencentcloud/aiart/v20221229/client.go)
- Tencent Cloud SDK 3.0 for Node.js: [CNB](https://cnb.cool/tencent/cloud/api/sdk/tencentcloud-sdk-nodejs/-/blob/master/src/services/aiart/v20221229/aiart_client.ts), [GitHub](https://github.com/TencentCloud/tencentcloud-sdk-nodejs/blob/master/src/services/aiart/v20221229/aiart_client.ts), [Gitee](https://gitee.com/TencentCloud/tencentcloud-sdk-nodejs/blob/master/src/services/aiart/v20221229/aiart_client.ts)
- Tencent Cloud SDK 3.0 for .NET: [CNB](https://cnb.cool/tencent/cloud/api/sdk/tencentcloud-sdk-dotnet/-/blob/master/TencentCloud/Aiart/V20221229/AiartClient.cs), [GitHub](https://github.com/TencentCloud/tencentcloud-sdk-dotnet/blob/master/TencentCloud/Aiart/V20221229/AiartClient.cs), [Gitee](https://gitee.com/TencentCloud/tencentcloud-sdk-dotnet/blob/master/TencentCloud/Aiart/V20221229/AiartClient.cs)
- Tencent Cloud SDK 3.0 for C++: [CNB](https://cnb.cool/tencent/cloud/api/sdk/tencentcloud-sdk-cpp/-/blob/master/aiart/src/v20221229/AiartClient.cpp), [GitHub](https://github.com/TencentCloud/tencentcloud-sdk-cpp/blob/master/aiart/src/v20221229/AiartClient.cpp), [Gitee](https://gitee.com/TencentCloud/tencentcloud-sdk-cpp/blob/master/aiart/src/v20221229/AiartClient.cpp)
- Tencent Cloud SDK 3.0 for Ruby: [CNB](https://cnb.cool/tencent/cloud/api/sdk/tencentcloud-sdk-ruby/-/blob/master/tencentcloud-sdk-aiart/lib/v20221229/client.rb), [GitHub](https://github.com/TencentCloud/tencentcloud-sdk-ruby/blob/master/tencentcloud-sdk-aiart/lib/v20221229/client.rb), [Gitee](https://gitee.com/TencentCloud/tencentcloud-sdk-ruby/blob/master/tencentcloud-sdk-aiart/lib/v20221229/client.rb)

### 命令行工具

- [Tencent Cloud CLI 3.0](https://cloud.tencent.com/document/product/440/6176)

## 6. 错误码

以下仅列出了接口业务逻辑相关的错误码，其他错误码详见 [公共错误码](https://cloud.tencent.com/document/api/1668/88076#.E5.85.AC.E5.85.B1.E9.94.99.E8.AF.AF.E7.A0.81)。

| 错误码                                    | 描述                                                         |
| :---------------------------------------- | :----------------------------------------------------------- |
| AuthFailure.UnauthorizedOperation         | 无权执行该操作，请检查您的CAM策略，确保您拥有对应的CAM权限。 |
| FailedOperation.ConsoleServerError        | 控制台服务异常。                                             |
| FailedOperation.GenerateImageFailed       | 生成图片审核不通过，请重试。                                 |
| FailedOperation.ImageDecodeFailed         | 图片解码失败。                                               |
| FailedOperation.ImageDownloadError        | 图片下载错误。                                               |
| FailedOperation.InnerError                | 服务内部错误，请稍后重试。                                   |
| FailedOperation.ModerationFailed          | 审核失败                                                     |
| FailedOperation.RequestEntityTooLarge     | 整个请求体太大（通常主要是图片）。                           |
| FailedOperation.RequestTimeout            | 后端服务超时。                                               |
| FailedOperation.RpcFail                   | RPC请求失败，一般为算法微服务故障。                          |
| FailedOperation.ServerError               | 服务内部错误。                                               |
| FailedOperation.Unknown                   | 未知错误。                                                   |
| InvalidParameter.InvalidParameter         | 参数不合法。                                                 |
| InvalidParameterValue.ImageEmpty          | 图片为空。                                                   |
| InvalidParameterValue.ParameterValueError | 参数字段或者值有误                                           |
| InvalidParameterValue.TextLengthExceed    | 输入文本过长，请更换短一点的文本后重试。                     |
| InvalidParameterValue.UrlIllegal          | URL格式不合法。                                              |
| OperationDenied.ImageIllegalDetected      | 图片包含违法违规信息，审核不通过。                           |
| OperationDenied.TextIllegalDetected       | 文本包含违法违规信息，审核不通过。                           |
| RequestLimitExceeded                      | 请求的次数超过了频率限制。                                   |
| RequestLimitExceeded.JobNumExceed         | 同时处理的任务数过多，请稍后重试。                           |
| ResourceUnavailable.InArrears             | 账号已欠费。                                                 |
| ResourceUnavailable.LowBalance            | 余额不足。                                                   |
| ResourceUnavailable.NotExist              | 计费状态未知，请确认是否已在控制台开通服务。                 |
| ResourceUnavailable.StopUsing             | 账号已停服。                                                 |
| ResourcesSoldOut.ChargeStatusException    | 计费状态异常。                                               |