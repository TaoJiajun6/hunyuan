# 混元 OpenAI 兼容接口相关调用示例

混元 API 兼容了 OpenAI 的接口规范，这意味着您可以直接使用 OpenAI 官方提供的 SDK 来调用混元大模型。您仅需要将 `base_url` 和 `api_key` 替换成混元的相关配置，不需要对应用做额外修改，即可无缝将您的应用切换到混元大模型。

base_url：https://api.hunyuan.cloud.tencent.com/v1

api_key：需在控制台 [API KEY页面](https://console.cloud.tencent.com/hunyuan/start) 进行创建，操作步骤请参考 [API KEY 管理](https://cloud.tencent.com/document/product/1729/111008)。

接口请求地址完整路径：`https://api.hunyuan.cloud.tencent.com/v1/chat/completions`

第三方软件集成混元，您可参见 [第三方软件集成混元指南](https://cloud.tencent.com/document/product/1729/116755) 。

## 对话(chat completions)

Python

```python
import os
from openai import OpenAI

# 构造 client
client = OpenAI(
    api_key=os.environ.get("HUNYUAN_API_KEY"),  # 混元 APIKey
    base_url="https://api.hunyuan.cloud.tencent.com/v1",  # 混元 endpoint
)

completion = client.chat.completions.create(
    model="hunyuan-turbos-latest",
    messages=[
        {
            "role": "user",
            "content": "Say this is a test."
        }
    ],
    extra_body={
        "enable_enhancement": True,  # <- 自定义参数
    },
)
print(completion.choices[0].message.content)
```

## OpenAI 兼容参数

| 参数名称       | 必选 | 类型     | 默认值 | 描述                                                         |
| -------------- | ---- | -------- | ------ | ------------------------------------------------------------ |
| model          | 是   | string   | 无     | 模型名称，可选值参考 [产品概述](https://cloud.tencent.com/document/product/1729/104753) 中混元生文模型列表。示例值：hunyuan-turbos-latest |
| messages       | 是   | object[] | 无     | 聊天上下文信息。相关字段可参考上文调用示例。说明：长度最多为 40，按对话时间从旧到新在数组中排列。message.role 可选值：system、user、assistant、 tool（ function call 场景）。messages 中 content 总长度不能超过模型输入长度上限（可参考 [产品概述](https://cloud.tencent.com/document/product/1729/104753) 文档），超过则会截断最前面的内容，只保留尾部内容。 |
| stream         | 否   | boolean  | false  | 流式调用开关。说明：未传值时默认为非流式调用（false）。流式调用时以 SSE 协议增量返回结果（返回值取 choices[n].delta 中的值，需要拼接增量数据才能获得完整结果）。非流式调用时： 调用方式与普通 HTTP 请求无异。接口响应耗时较长，如需更低时延建议设置为 true。只返回一次最终结果（返回值取 choices[n].message 中的值）。             示例值：false |
| max_tokens     | 否   | integer  | 4096   | 限制一次请求中模型生成 completion 的最大 token 数。输入 token 和输出 token 的总长度受模型的上下文长度的限制。 |
| seed           | 否   | integer  | 无     | 说明： 1. 确保模型的输出是可复现的。2. 取值区间为非0正整数，最大值10000。 3. 非必要不建议使用，不合理的取值会影响效果。示例值：1 |
| stop           | 否   | string[] | 无     | 自定义结束生成字符串。调用 OpenAI 接口时，如果您指定了 stop 参数, 模型会停止在匹配到 stop 的内容之前。在调用混元接口时，会停止在匹配到 stop 的内容之后。说明：未来我们可能会修改此行为以便和 OpenAI 保持一致。但是目前有使用该参数的情况下，开发者需要注意该参数是否会对应用造成影响，以及未来该行为调整时带来的影响。 |
| temperature    | 否   | number   | 无     | 说明：影响模型输出多样性，模型已有默认参数，不传值时使用各模型推荐值，不推荐用户修改。取值区间为 [0.0, 2.0]。较高的数值会使输出更加多样化和不可预测，而较低的数值会使其更加集中和确定。 |
| top_p          | 否   | number   | 0      | 说明：影响输出文本的多样性。模型已有默认参数，不传值时使用各模型推荐值，不推荐用户修改。取值区间为 [0.0, 1.0]。取值越大，生成文本的多样性越强。 |
| tools          | 否   | object[] | 无     | 可调用的工具列表，相关字段可参考上文调用示例。               |
| tool_choice    | 否   | object   | 无     | 工具使用选项，可选值包括 none、auto、custom。说明：仅对 hunyuan-turbos、hunyuan-functioncall 模型生效。none：不调用工具。     auto：模型自行选择生成回复或调用工具。     custom：强制模型调用指定的工具。未设置时，默认值为 auto。     示例值：auto |
| stream_options | 否   | object   | 无     | 流式输出相关选项。只有在 stream 参数为 true 时，才可设置此参数。 |

﻿

## 混元自定义参数

| 参数名称                     | 必选 | 类型    | 默认值 | 描述                                                         |
| ---------------------------- | ---- | ------- | ------ | ------------------------------------------------------------ |
| citation                     | 否   | boolean | false  | 搜索引文角标开关。说明：配合 enable_enhancement 和 search_info 参数使用。打开后，回答中命中搜索的结果会在片段后增加角标标志，对应 search_info 列表中的链接。false：开关关闭；true：开关打开。未传值时默认开关关闭（false）。 |
| enable_enhancement           | 否   | boolean | false  | 功能增强（如搜索）开关。说明：hunyuan-lite 无功能增强（如搜索）能力，该参数对 hunyuan-lite 版本不生效。未传值时默认关闭开关。关闭时将直接由主模型生成回复内容，可以降低响应时延（对于流式输出时的首字时延尤为明显）。但在少数场景里，回复效果可能会下降。安全审核能力不属于功能增强范围，不受此字段影响。2025年04月20日 00:00:00起，由默认开启状态转为默认关闭状态。 |
| enable_multimedia            | 否   | boolean | false  | 多媒体开关。详细介绍请阅读 [多媒体介绍](https://cloud.tencent.com/document/product/1729/111178) 中的说明。说明：该参数目前仅对白名单内用户生效，如您想体验该功能请 [联系我们](https://cloud.tencent.com/act/event/Online_service)。该参数仅在功能增强（如搜索）开关开启（enable_enhancement=true）并且极速版搜索开关关闭（enable_speed_search=false）时生效。hunyuan-lite 无多媒体能力，该参数对 hunyuan-lite 版本不生效。未传值时默认关闭。开启并搜索到对应的多媒体信息时，会输出对应的多媒体地址，可以定制个性化的图文消息。 |
| enable_recommended_questions | 否   | boolean | false  | 推荐问答开关。说明：未传值时默认关闭。开启后，在返回值的最后一个包中会增加 recommended_questions 字段表示推荐问答， 最多返回3条。 |
| force_search_enhancement     | 否   | boolean | false  | 强制搜索增强开关。说明：未传值时默认关闭。开启后，将强制走AI搜索，当 AI 搜索结果为空时，由大模型回复兜底话术。 |
| search_info                  | 否   | boolean | false  | 在值为 true 且命中搜索时，接口会返回 search_info。           |
| enable_deep_search           | 否   | boolean | false  | 是否开启深度研究该问题，默认是 false，在值为 true 且命中深度研究该问题时，会返回深度研究该问题信息。 |
| enable_deep_read             | 否   | boolean | false  | 文档深度阅读开关。说明：未传值时默认关闭。开启后，需要根据文件的具体类型，指定不同的 prompt 模板。例如：核心速览、论文评价、主要内容、关键问题及回答等。当前仅支持单轮，单文档的深度阅读。 |

## 与OpenAI的差异

### /v1/chat/completions

#### stop

调用 OpenAI 的接口时，如果您指定了 `stop` 参数, 模型会停止在匹配到 `stop` 的内容之前。

在调用混元接口时，会停止在匹配到 `stop` 的内容之后。

以原始输出 “`我是一个AI助手可以帮助您在不同方面做出更好的决策，解答您的疑问并提供可靠的信息。`”为例：

| 类型   | stop 参数 | 模型输出         |
| ------ | --------- | ---------------- |
| OpenAI | 助手      | 我是一个 AI      |
| 混元   | 助手      | 我是一个 AI 助手 |

**说明：**

未来我们可能会修改此行为以便和 OpenAI 保持一致。

但是目前有使用该参数的情况下，开发者需要注意该参数是否会对应用造成影响，以及未来该行为调整时带来的影响。

#### stream_options

当流式返回且 `stream_options.include_usage=true` 时，会在最后一个数据块中返回 `usage` 信息。