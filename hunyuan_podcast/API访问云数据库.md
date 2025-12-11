# 通过REST API接口使用云数据库

更新时间: 2025-07-14 16:43







云数据库提供了REST API接口，您只需要访问相关URL，构造相关请求体即可调用该接口，完成数据管理的操作。

## 开发前准备

使用REST API管理数据，需要完成以下准备工作：

示例应用使用了认证用户的相关权限，需要开通AGC认证服务中“匿名账号”服务，详细请参见[开通认证服务](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-auth-enable-service-0000001274125746)。

## 获取客户端API授权

访问端侧网关的客户端需要具备有效的Client ID以及Client Secret，才能通过端侧网关的鉴权校验并对业务接口发起有效调用。

1. 登录[AppGallery Connect](https://developer.huawei.com/consumer/cn/service/josp/agc/index.html)，选择“开发与服务”。

2. 在项目列表中选择需要获取凭证的项目，在“项目设置”页面点击“常规”页签。

3. 记录“常规”页签“项目”栏下的“Client ID”和“Client Secret”。

   ![img](https://alliance-communityfile-drcn.dbankcdn.com/FileServer/getFile/cmtyPub/011/111/111/0000000000011111111.20250714155713.33631643783189539959549745482549:50001231000000:2800:9FF36C6451BEB98565483A5ECEA764E6D48F0A8512D0C9C29B08D694ECA5195E.png)

4. 调用**[获取Token](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-obtaintoken-rest-0000001446607602)**接口，获取访问客户端REST API的Access Token。您在[3](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-clouddb-restapi-0000001518509166#ZH-CN_TOPIC_0000001518509166__li230415547508)中记录的“Client ID”和“Client Secret”将作为请求参数在调用时传入。

## 获取Token

您可使用客户端REST API调用**[获取Token](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-obtaintoken-rest-0000001446607602)**接口，通过华为开放平台进行鉴权，并获取认证通过后的Token。

1. 根据请求参数获取对应参数值，构造获取Token请求体。

   ```cangjie
   POST /agc/apigw/oauth2/v1/tokenHost: connect-drcn.dbankcloud.cnContent-Type: application/json{   "useJwt":"1",   "grant_type":"client_credentials",   "client_id":"26********20",   "client_secret":"************************"}
   ```

2. 发送获取Token请求，收到请求响应体。

   ```cangjie
   HTTP/1.1 200 OKContent-Type: application/json; charset=utf-8{    "access_token": "eyJhbGciOiJIUzU****************",    "expires_in": 172800}
   ```

## 用户登录

您可使用客户端REST API调用**[用户登录](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-signin-rest-0000001496447669)**接口，根据客户端认证Token和用户名密码登录，并获取登录通过后的用户认证accessToken。

1. 根据请求参数获取对应参数值，构造用户登录请求体。

   ```cangjie
   POST agc/apigw/oauth2/third/v1/user-signincontent-type: application/jsonproductId: 99************83client_id: 680************560Authorization: Bearer ***host: connect-drcn.dbankcloud.cn{    "provider": 0,    "token": "string",    "extraData": "string",    "autoCreateUser": 0,    "useJwt": 1,    "channelId": "string",    "aaId": "string"}
   ```

2. 发送用户登录请求，收到请求响应体。

   ```cangjie
   {    "ret": {        "code": 0,        "msg": "string"    },    "accessToken": {        "token": "string",        "validPeriod": 0    },    "refreshToken": {        "token": "string",        "validPeriod": 0    },    "userInfo": {        "uid": "string",        "importUid": "string",        "displayName": "string",        "photoUrl": "string",        "provider": 0,        "emailVerified": 0,        "passwordSetted": 0,        "email": "string",        "phone": "string"    },    "providers": [{        "uid": "string",        "displayName": "string",        "photoUrl": "string",        "provider": 0,        "openId": "string",        "email": "string",        "phone": "string",        "extId": "string"    }]}
   ```

## 查询数据

REST API通过构造HTTP请求的方式**[查询数据](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573)**，并提供了丰富的谓词查询，比如equalTo、notEqualTo、in等。通过单个或者多个链式过滤条件，您可以从云侧数据库查询到满足特定条件的对象，也可以通过限定查询返回数量谓词限定查询结果返回的数量，还可以支持聚合查询，例如查询平均值、最大值、最小值等。

**示例代码：**

构造查询数据请求。查询存储区为cloudDBZone，对象类型为StudentInfo，“id”为1的数据对象。

```swift
POST agc/apigw/clouddb/clouddbservice/sync/query?_v=4content-type: application/jsonclient_id: 74************40Authorization: Bearer ***productId: 24************51access_token: ******host: connect-drcn.dbankcloud.cn{  "msgInfo": {    "type": 5,    "opStore": {      "storeName": "cloudDBZone"    }  },  "clientInfo": {    "appVer": 1  },  "queryReqMsg": {    "queryType" : 0,    "queryTable" : "StudentInfo",    "queryCond" : "{\"queryConditions\":[{\"conditionType\":\"EqualTo\",\"fieldName\":\"id\",\"value\":\"1\"},{\"conditionType\":\"Limit\",\"value\":{\"number\":10,\"offset\":0}}]}"  }}
```

## 更新数据

REST API通过构造HTTP请求的方式**[更新数据](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706)**，支持数据的新增和更新。若更新数据时，如果在Cloud DB zone已经存在主键值相同的对象，则更新已有的对象；如果不存在，则写入一个新的对象。

**示例代码：**

构造更新数据请求。在存储区为cloudDBZone，对象类型为StudentInfo中新增一条“id”为1的数据对象。

```cangjie
POST agc/apigw/clouddb/clouddbservice/sync/upsert?_v=4content-type: application/jsonclient_id: 74************40Authorization: Bearer ***productId: 99************83access_token: ***host: connect-drcn.dbankcloud.cn{  "msgInfo": {    "type": 3,    "opStore": {      "storeName": "cloudDBZone"    }  },  "clientInfo": {    "appVer": 1  },  "schemas": [    {      "n": "StudentInfo",      "fs": [        {          "n": "id",          "t": "TYPE_INT32"        },        {          "n": "name",          "t": "TYPE_STRING"        },        {          "n": "age",          "t": "TYPE_INT32"        },        {          "n": "naturalbase_version",          "t": "TYPE_LONG"        },        {          "n": "naturalbase_deleted",          "t": "TYPE_BOOLEAN"        }      ]    }  ],  "opData": [    {      "os": [        {          "fs": [            {              "i": 1            },            {              "s": "string"            },            {              "i": 18            },            {              "l": null            },            {              "bl": false            }          ]        }      ],      "t": 1    }  ]}
```

## 删除数据

REST API通过构造HTTP请求的方式**[删除数据](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714)**。删除数据时，请求接口会根据传入对象主键删除相应的数据，不会比对该对象其他属性与存储的数据是否一致。

注意

删除数据对象时，该组中的对象必须属于同一个对象类型，否则会导致删除失败。

**示例代码：**

构造删除数据请求。删除存储区为cloudDBZone，对象类型为StudentInfo中的，删除一条“id”为1的数据对象。

```
POST agc/apigw/clouddb/clouddbservice/sync/upsert?_v=4content-type: application/jsonclient_id: 74************40Authorization: Bearer ***productId: 99************83access_token: ***host: connect-drcn.dbankcloud.cn{  "msgInfo": {    "type": 3,    "opStore": {      "storeName": "cloudDBZone"    }  },  "clientInfo": {    "appVer": 1  },  "schemas": [    {      "n": "StudentInfo",      "fs": [        {          "n": "id",          "t": "TYPE_INT32"        },        {          "n": "naturalbase_version",          "t": "TYPE_LONG"        },        {          "n": "naturalbase_deleted",          "t": "TYPE_BOOLEAN"        }      ]    }  ],  "opData": [    {      "i": 0,      "os": [        {          "fs": [            {              "i": 1            },            {              "l": null            },            {              "bl": true            }          ],          "i": 0        }      ],      "t": 1    }  ]}
```

# 获取Token

更新时间: 2024-08-19 17:20







## 功能介绍

在使用客户端REST API调用业务接口前，需要通过华为开放平台进行鉴权，并获取认证通过后的Token。

## 接口原型

| 承载协议 | HTTPS POST                                                   |
| :------- | ------------------------------------------------------------ |
| 接口方向 | 应用客户端 -> 华为认证服务器                                 |
| 接口URL  | https://connect-drcn.dbankcloud.cn/agc/apigw/oauth2/v1/token |
| 数据格式 | 请求：Content-Type: application/json响应：Content-Type: application/json |

## 请求参数

请求参数以JSON格式传入，包含参数如下。

| 参数名称      | 必选(M)/可选(O) | 参数类型 | 参数说明                                                     |
| :------------ | :-------------- | :------- | :----------------------------------------------------------- |
| useJwt        | M               | integer  | 是否使用自有账号凭据JWT(Json Web Token)：“1”：固定值，表示使用JWT。 |
| grant_type    | M               | String   | 固定传入“client_credentials”。                               |
| client_id     | M               | String   | 客户端ID，即[获取客户端API授权](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-clouddb-restapi-0000001518509166#section18502104612500)中的“Client ID”。 |
| client_secret | M               | String   | 客户端密钥，即[获取客户端API授权](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-clouddb-restapi-0000001518509166#section18502104612500)中的“Client Secret”。 |

**请求示例**

```cangjie
POST /agc/apigw/oauth2/v1/tokenHost: connect-drcn.dbankcloud.cnContent-Type: application/json{   "useJwt":"1",   "grant_type":"client_credentials",   "client_id":"26********20",   "client_secret":"************************"}
```

## 响应参数

返回值为JSON格式的字符串，包含参数如下。

| 参数名称     | 必选(M)/可选(O) | 参数类型 | 参数说明                                                     |
| :----------- | :-------------- | :------- | :----------------------------------------------------------- |
| access_token | O               | String   | 认证Token，用于API接口调用。此参数只在获取成功时返回。       |
| expires_in   | O               | Long     | access_token的有效期，单位为秒。您需要在过期时间到达时重新调用本接口获取新的access_token。有效期为48小时，如果在有效期内再次调用接口获取access_token时，新老access_token都是有效的。此参数只在获取成功时返回。 |

**响应示例**

```cangjie
HTTP/1.1 200 OKContent-Type: application/json; charset=utf-8{    "access_token": "eyJhbGciOiJIUzU****************",    "expires_in": 172800}
```



# 查询数据

更新时间: 2025-10-30 15:46







## 功能介绍

该接口用于用户查询数据，云数据库提供了丰富的谓词查询，比如equalTo、notEqualTo、in等，通过单个或者多个链式过滤条件，您可以从云侧数据库查询到满足特定条件的对象，也可以通过限定查询返回数量谓词限定查询结果返回的数量，还可以支持聚合查询，例如查询平均值、最大值、最小值等。

## 接口原型

| 承载协议 | HTTPS POST                                                   |
| :------- | :----------------------------------------------------------- |
| 接口方向 | 应用客户端 -> CloudDB服务器                                  |
| 接口URL  | https://connect-drcn.dbankcloud.cn/agc/apigw/clouddb/clouddbservice/sync/query |
| 数据格式 | 请求：Content-Type: application/json响应：Content-Type: application/json |

## 请求参数

### Query

| 参数名称 | 必选(M)/可选(O) | 参数类型 | 参数说明                                                     |
| :------- | :-------------- | :------- | :----------------------------------------------------------- |
| _v       | M               | integer  | 数据版本类型，入参需为“4”表示protobuf v2 版本类型的json字符串。 |

### Header

| 参数名称      | 必选(M)/可选(O) | 参数类型 | 参数说明                                                     |
| :------------ | :-------------- | :------- | :----------------------------------------------------------- |
| client_id     | M               | String   | 客户端ID，获取方法参考[获取客户端API授权](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-clouddb-restapi-0000001518509166#section18502104612500)。 |
| Authorization | M               | String   | 认证信息。格式为“Authorization: Bearer ${client_token}”。client_token为[获取Token](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-obtaintoken-rest-0000001446607602)中获取的access_token。 |
| productId     | M               | String   | 项目ID，查询方法可参见[查询项目ID](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-get-developerid-projectid-0000001166543063)。 |
| access_token  | O               | String   | 认证凭据。用户登录成功后，在登录接口的[响应参数](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-signin-rest-0000001496447669#section101441919542)“accessToken”中获取。该值为空时，则表示匿名账号登录。 |

### Body

| 参数名称    | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                                            |
| :---------- | :------------------ | :----------------------------------------------------------- | :-------------------------------------------------- |
| msgInfo     | M                   | [MsgInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section42449327218) | 消息的基本信息，具体请参见MsgInfo。                 |
| clientInfo  | M                   | [ClientInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section448214662111) | 客户端的基本信息，具体请参见ClientInfo。            |
| queryReqMsg | M                   | [QueryRequestMessage](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section18423962213) | 查询请求的基本信息，具体请参见QueryRequestMessage。 |

### MsgInfo

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明                                                     |
| :------- | :------------------ | :------- | :----------------------------------------------------------- |
| type     | M                   | integer  | 查询请求。入参需为“5”。“3”：更新数据或删除数据请求。“5”：查询数据请求。 |
| opStore  | M                   | Json     | JSON字符串。格式为{"storeName": "cloudDBZone"}。cloudDBZone为存储区名。 |

### ClientInfo

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明                                                     |
| :------- | :------------------ | :------- | :----------------------------------------------------------- |
| appVer   | M                   | integer  | 对象类型对应的版本号，获取请参考[导出对象类型步骤4](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-clouddb-agcconsole-objecttypes-0000001127675459#ZH-CN_TOPIC_0000001569011701__li89603794812)中的版本号。 |

### QueryRequestMessage

| 参数名称   | 必选（M）/可选（O） | 参数类型 | 参数说明                                                     |
| :--------- | :------------------ | :------- | :----------------------------------------------------------- |
| queryType  | M                   | integer  | 查询类型。涉及到的查询值类型如下：0：默认值，普通查询。1：AVG、Average，平均值查询。2：SUM，总和查询。3：MAX，最大值查询。4：MIN，最小值查询。5：COUNT，计数查询。 |
| queryTable | M                   | String   | 查询的对象类型名称。                                         |
| queryCond  | M                   | String   | 查询条件。Json格式的字符串，例如："{\"queryConditions\":[{\"conditionType\":\"EqualTo\",\"fieldName\":\"id\",\"value\":\"3\"},{\"conditionType\":\"Limit\",\"value\":{\"number\":10,\"offset\":0}}]}"说明当queryType不为0时，queryCond的conditionType参数必须设置为与queryType取值一致的查询条件，否则会导致接口返回错误。例如：queryType取值为2时，conditionType必须设置为SUM。 |

**请求示例**

预定义一个存储区(cloudDBZone)、对象类型StudentInfo(id integer primary key, name string, age integer);

```swift
POST agc/apigw/clouddb/clouddbservice/sync/query?_v=4content-type: application/jsonclient_id: 74************40Authorization: Bearer ***productId: 24************51access_token: ******host: connect-drcn.dbankcloud.cn{  "msgInfo": {    "type": 5,    "opStore": {      "storeName": "cloudDBZone"    }  },  "clientInfo": {    "appVer": 15  },  "queryReqMsg": {    "queryType" : 0,    "queryTable" : "StudentInfo",    "queryCond" : "{\"queryConditions\":[{\"conditionType\":\"EqualTo\",\"fieldName\":\"id\",\"value\":\"1\"},{\"conditionType\":\"Limit\",\"value\":{\"number\":10,\"offset\":0}}]}"  }}
```

**聚合查询QueryRequestMessage请求消息体示例**

```swift
{  "queryReqMsg": {    "queryType" : 1,    "queryTable" : "StudentInfo",    "queryCond" : "{\"queryConditions\":[{\"conditionType\":\"Average\",\"fieldName\":\"age\"}]}"  }}
```

## 响应参数

| 参数        | 必选（M）/可选（O） | 参数类型                                                     | 描述                                                   |
| :---------- | :------------------ | :----------------------------------------------------------- | :----------------------------------------------------- |
| msgInfo     | O                   | [MsgInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section42449327218) | 消息的基本信息，具体请参见MsgInfo。                    |
| resInfo     | O                   | [ResponseInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section15813132391810) | 返回响应的基本状态信息，具体请参见ResponseInfo。       |
| schemas     | O                   | list<[Schema](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section1032114611816)> | 对象类型基本信息，具体请见Schema。                     |
| opData      | O                   | list<[OperatorData](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section32691439191911)> | 对象类型中数据信息，具体请见OperatorData。             |
| queryResMsg | O                   | [QueryResponseMessage](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section15908236202019) | 聚合查询响应基本信息，具体请参见QueryResponseMessage。 |

### ResponseInfo

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明       |
| :------- | :------------------ | :------- | :------------- |
| resCode  | O                   | integer  | 响应状态码。   |
| resInfo  | O                   | String   | 响应描述信息。 |

### Schema

| 参数名称 | 必选（M）/可选（O） | 参数类型                                                     | 参数说明       |
| :------- | :------------------ | :----------------------------------------------------------- | :------------- |
| n        | O                   | String                                                       | 对象类型名称。 |
| fs       | O                   | List<[SchemaField](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section4778145911810)> | 字段名称。     |

### SchemaField

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明                                                     |
| :------- | :------------------ | :------- | :----------------------------------------------------------- |
| n        | O                   | String   | 字段名信息。                                                 |
| t        | O                   | String   | 字段类型，取值包含如下字段类型：1：TYPE_BOOLEAN，布尔类型。2：TYPE_BYTE，byte类型。3：TYPE_SHORT，short类型。4：TYPE_INT32，int类型。5：TYPE_LONG，long类型。6：TYPE_FLOAT，float类型。7：TYPE_DOUBLE，double类型。8：TYPE_BYTE_ARRAY，byte数组类型。9：TYPE_STRING，String类型。10：TYPE_DATE，date类型。11：TYPE_TEXT，文本类型。12：TYPE_AUTO_INCREMENT_INT，int自增类型。13：TYPE_AUTO_INCREMENT_LONG，long自增类型。 |

### OperatorData

| 参数名称 | 必选（M）/可选（O） | 参数类型                                                     | 参数说明       |
| :------- | :------------------ | :----------------------------------------------------------- | :------------- |
| os       | O                   | List<[Field](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section10292165113308)> | 数据对象信息。 |

### Field

| 参数名称 | 必选（M）/可选（O） | 参数类型                                                     | 参数说明           |
| :------- | :------------------ | :----------------------------------------------------------- | :----------------- |
| fs       | O                   | List<[FieldValue](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section86139207207)> | 单条数据对象信息。 |

### FieldValue

| 参数名称 | 必选（M）/可选（O） | 参数类型  | 参数说明        |
| :------- | :------------------ | :-------- | :-------------- |
| n        | O                   | boolean   | 是否设置为null  |
| bl       | O                   | boolean   | boolean类型值   |
| b        | O                   | byte      | byte类型值      |
| st       | O                   | short     | short类型值     |
| i        | O                   | int       | int类型值       |
| l        | O                   | long      | long类型值      |
| f        | O                   | float     | float类型值     |
| d        | O                   | double    | double类型值    |
| ba       | O                   | byteArray | byteArray类型值 |
| s        | O                   | String    | String类型值    |

### QueryResponseMessage

| 参数名称    | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                                                     |
| :---------- | :------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- |
| queryType   | O                   | integer                                                      | 查询类型，涉及到的查询值类型如下：0：默认值，普通查询。1：AVG、Average，平均值查询。2：SUM，总和查询。3：MAX，最大值查询。4：MIN，最小值查询。5：COUNT，计数查询。 |
| aggQueryRes | O                   | [AggregateQueryResult](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-query-data-rest-0000001496647573#section138011958202015) | 聚合查询结果信息。                                           |

### AggregateQueryResult

| 参数名称  | 必选（M）/可选（O） | 参数类型 | 参数说明                                                    |
| :-------- | :------------------ | :------- | :---------------------------------------------------------- |
| isNull    | O                   | boolean  | 聚合查询结果是否为空。                                      |
| longRes   | O                   | long     | 字段类型为int、long的MAX、MIN、SUM查询结果或COUNT查询结果。 |
| doubleRes | O                   | double   | 字段类型为double的MAX、MIN、Average、SUM查询结果。          |

**响应示例**

```cangjie
{    "msgInfo": {        "type": 5,        "opStore": {            "storeName": "cloudDBZone"        }    },    "resInfo": {},    "schemas": [        {            "n": "StudentInfo",            "fs": [                {                    "n": "id",                    "t": 4                },                {                    "n": "name",                    "t": 9                },                {                    "n": "age",                    "t": 4                },                {                    "n": "naturalbase_creator",                    "t": 9                },                {                    "n": "naturalbase_version",                    "t": 5                }            ]        }    ],    "opData": [        {            "os": [                {                    "fs": [                        {                            "i": 0                        },                        {                            "s": "string"                        },                        {                            "i": "0"                        },                        {                            "s": "string"                        },                        {                            "l": "0"                        }                    ]                }            ]        }    ],    "queryResMsg": {        "aggQueryRes": {            "isNull": true        }    }}
```



# 更新数据

更新时间: 2025-10-30 15:46







## 功能介绍

该接口用于用户更新数据，支持数据的新增和更新。更新数据时，如果在CloudDBZone已经存在主键值相同的对象，则更新已有的对象；如果不存在，则写入一个新的对象。更新操作需要设置naturalbase_deleted字段为false，具体请参见[SchemaField](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section3658142019245)字段设置。

## 接口原型

| 承载协议 | HTTPS POST                                                   |
| :------- | :----------------------------------------------------------- |
| 接口方向 | 应用客户端 -> CloudDB服务器                                  |
| 接口URL  | https://connect-drcn.dbankcloud.cn/agc/apigw/clouddb/clouddbservice/sync/upsert |
| 数据格式 | 请求：Content-Type: application/json响应：Content-Type: application/json |

## 请求参数

### Query

| 参数名称 | 必选(M)/可选(O) | 参数类型 | 参数说明                                                     |
| :------- | :-------------- | :------- | :----------------------------------------------------------- |
| _v       | M               | integer  | 数据版本类型，入参需为“4”表示protobuf v2 版本类型的json字符串。 |

### Header

| 参数名称      | 必选(M)/可选(O) | 参数类型 | 参数说明                                                     |
| :------------ | :-------------- | :------- | :----------------------------------------------------------- |
| client_id     | M               | String   | 客户端ID，即[获取客户端API授权](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-clouddb-restapi-0000001518509166#section18502104612500)中的“Client ID”。 |
| Authorization | M               | String   | 认证信息，格式为“Authorization: Bearer ${authorization_token}”。authorization_token为[获取Token](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-obtaintoken-rest-0000001446607602)中获取的access_token。 |
| productId     | M               | String   | 项目ID，查询方法可参见[查询项目ID](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-get-developerid-projectid-0000001166543063)。 |
| access_token  | O               | String   | 认证凭据。用户登录成功后，在登录接口的[响应参数](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-signin-rest-0000001496447669#section101441919542)“accessToken”中获取。该值为空时，则表示匿名账号登录。 |

### Body

| 参数名称   | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                                   |
| :--------- | :------------------ | :----------------------------------------------------------- | :----------------------------------------- |
| msgInfo    | M                   | [MsgInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section1295143742319) | 消息的基本信息，具体请参见MsgInfo。        |
| clientInfo | M                   | [ClientInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section10559951122313) | 客户端的基本信息，具体请参见ClientInfo。   |
| schemas    | M                   | List<[Schema](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section1344310632417)> | 表对象信息，具体请参见Schema。             |
| opData     | M                   | List<[OperatorData](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section090964114246)> | 更新数据对象信息，具体请参见OperatorData。 |

### MsgInfo

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明                                                     |
| :------- | :------------------ | :------- | :----------------------------------------------------------- |
| type     | M                   | integer  | 更新请求，入参需为“3”。“3”：更新数据或删除数据请求。“5”：查询数据请求。 |
| opStore  | M                   | Json     | JSON字符串。格式为{"storeName": "cloudDBZone"}。cloudDBZone为存储区名。 |

### ClientInfo

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明                                                     |
| :------- | :------------------ | :------- | :----------------------------------------------------------- |
| appVer   | M                   | integer  | 对象类型对应的版本号，获取请参考[导出对象类型步骤4](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-clouddb-agcconsole-objecttypes-0000001127675459#ZH-CN_TOPIC_0000001569011701__li89603794812)中的版本号。 |

### Schema

| 参数名称 | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                                                     |
| :------- | :------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- |
| n        | M                   | String                                                       | 对象类型名称。                                               |
| fs       | M                   | List<[SchemaField](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section3658142019245)> | 字段名称。更新字段时，该字段必须属于同一个对象类型，否则会导致更新失败。 |

### SchemaField

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明                                                     |
| :------- | :------------------ | :------- | :----------------------------------------------------------- |
| n        | M                   | String   | 字段名。更新操作时必须有如下两个字段，并遵循如下约束：long类型的naturalbase_version字段：该字段不生效，可设置为任意值。布尔类型的naturalbase_deleted字段：需设置为固定值“false”。 |
| t        | M                   | String   | 字段类型，取值包含如下字段类型：1：TYPE_BOOLEAN，布尔类型。2：TYPE_BYTE，byte类型。3：TYPE_SHORT，short类型。4：TYPE_INT32，int类型。5：TYPE_LONG，long类型。6：TYPE_FLOAT，float类型。7：TYPE_DOUBLE，double类型。8：TYPE_BYTE_ARRAY，byte数组类型。9：TYPE_STRING，String类型。10：TYPE_DATE，date类型。11：TYPE_TEXT，文本类型。12：TYPE_AUTO_INCREMENT_INT，int自增类型。13：TYPE_AUTO_INCREMENT_LONG，long自增类型。 |

### OperatorData

| 参数名称 | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                                                     |
| :------- | :------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- |
| os       | M                   | List<[Field](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section101441056257)> | 操作对象信息。该对象必须属于同一个对象类型，且仅支持传入一个Field。 |
| t        | M                   | integer                                                      | 更新操作类型，入参为“1”。                                    |

### Field

| 参数名称 | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                                                     |
| :------- | :------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- |
| fs       | M                   | List<[FieldValue](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section153514306256)> | 单条对象信息。说明更新操作包含naturalbase_deleted的字段固定设置值为false。 |

### FieldValue

说明

更新数据时，更新字段的数据类型与[SchemaField](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section3658142019245)中的参数类型需保持一致。

| 参数名称 | 必选（M）/可选（O） | 参数类型  | 参数说明        |
| :------- | :------------------ | :-------- | :-------------- |
| n        | O                   | boolean   | 是否设置为null  |
| bl       | O                   | boolean   | boolean类型值   |
| b        | O                   | byte      | byte类型值      |
| st       | O                   | short     | short类型值     |
| i        | O                   | int       | int类型值       |
| l        | O                   | long      | long类型值      |
| f        | O                   | float     | float类型值     |
| d        | O                   | double    | double类型值    |
| ba       | O                   | byteArray | byteArray类型值 |
| s        | O                   | String    | String类型值    |

**请求示例**

预定义一个存储区(cloudDBZone)、对象类型StudentInfo(id integer primary key, name string, age integer);

```cangjie
POST agc/apigw/clouddb/clouddbservice/sync/upsert?_v=4content-type: application/jsonclient_id: 74************40Authorization: Bearer ***productId: 99************83access_token: ***host: connect-drcn.dbankcloud.cn{  "msgInfo": {    "type": 3,    "opStore": {      "storeName": "cloudDBZone"    }  },  "clientInfo": {    "appVer": 1  },  "schemas": [    {      "n": "StudentInfo",      "fs": [        {          "n": "id",          "t": "TYPE_INT32"        },        {          "n": "name",          "t": "TYPE_STRING"        },        {          "n": "age",          "t": "TYPE_INT32"        },        {          "n": "naturalbase_version",          "t": "TYPE_LONG"        },        {          "n": "naturalbase_deleted",          "t": "TYPE_BOOLEAN"        }      ]    }  ],  "opData": [    {      "os": [        {          "fs": [            {              "i": 1            },            {              "s": "string"            },            {              "i": 18            },            {              "l": null            },            {              "bl": false            }          ]        }      ],      "t": 1    }  ]}
```

## 响应参数

| 参数名称     | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                 |
| :----------- | :------------------ | :----------------------------------------------------------- | :----------------------- |
| msgInfo      | O                   | [MsgInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section1295143742319) | 返回消息的基本信息。     |
| resInfo      | O                   | [ResponseInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section346211104269) | 返回响应的基本状态信息。 |
| updateResMsg | O                   | [UpdateResponseMessage](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-update-data-rest-0000001446287706#section1996242232611) | 返回响应的更新信息。     |

### ResponseInfo

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明       |
| :------- | :------------------ | :------- | :------------- |
| resCode  | O                   | integer  | 响应状态码。   |
| resInfo  | O                   | String   | 响应描述信息。 |

### UpdateResponseMessage

| 参数名称        | 必选（M）/可选（O） | 参数类型 | 参数说明       |
| :-------------- | :------------------ | :------- | :------------- |
| successRecCount | O                   | integer  | 成功更新条数。 |

**响应示例**

```cangjie
{    "msgInfo": {        "type": 3,        "opStore": {            "storeName": "String"        }    },    "resInfo": {},    "updateResMsg": {        "successRecCount": 1    }}
```



# 删除数据

更新时间: 2025-10-30 15:46







## 功能介绍

该接口用于用户删除数据，根据您传入对象主键删除相应的数据，不会比对该对象其他属性与存储的数据是否一致，删除操作需要设置naturalbase_deleted字段为true，具体请参见[SchemaField](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section129653168386)字段设置。

## 接口原型

| 承载协议 | HTTPS POST                                                   |
| :------- | :----------------------------------------------------------- |
| 接口方向 | 应用客户端 -> CloudDB服务器                                  |
| 接口URL  | https://connect-drcn.dbankcloud.cn/agc/apigw/clouddb/clouddbservice/sync/upsert |
| 数据格式 | 请求：Content-Type: application/json响应：Content-Type: application/json |

## 请求参数

### Query

| 参数名称 | 必选(M)/可选(O) | 参数类型 | 参数说明                                                     |
| :------- | :-------------- | :------- | :----------------------------------------------------------- |
| _v       | M               | integer  | 数据版本类型，入参需为“4”表示protobuf v2 版本类型的json字符串。 |

### Header

| 参数名称      | 必选(M)/可选(O) | 参数类型 | 参数说明                                                     |
| :------------ | :-------------- | :------- | :----------------------------------------------------------- |
| client_id     | M               | String   | 客户端ID，即[获取客户端API授权](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-clouddb-restapi-0000001518509166#section18502104612500)中的“Client ID”。 |
| Authorization | M               | String   | 认证信息，格式为“Authorization: Bearer ${authorization_token}”。authorization_token为[获取Token](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-obtaintoken-rest-0000001446607602)中获取的access_token。 |
| productId     | M               | String   | 项目ID，查询方法可参见[查询项目ID](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-get-developerid-projectid-0000001166543063)。 |
| access_token  | O               | String   | 认证凭据。用户登录成功后，在登录接口的[响应参数](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-signin-rest-0000001496447669#section101441919542)“accessToken”中获取。该值为空时，则表示匿名账号登录。 |

### Body

| 参数名称   | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                                 |
| :--------- | :------------------ | :----------------------------------------------------------- | :--------------------------------------- |
| msgInfo    | M                   | [MsgInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section19632115714018) | 消息的基本信息，具体请参见MsgInfo。      |
| clientInfo | M                   | [ClientInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section177593293713) | 客户端的基本信息，具体请参见ClientInfo。 |
| schemas    | M                   | List<[Schema](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section18342205718374)> | 对象类型信息。                           |
| opData     | M                   | List<[OperatorData](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section7855744143812)> | 更新数据的对象信息。                     |

### ClientInfo

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明                                                     |
| :------- | :------------------ | :------- | :----------------------------------------------------------- |
| appVer   | M                   | integer  | 对象类型对应的版本号，获取请参考[导出对象类型步骤4](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-clouddb-agcconsole-objecttypes-0000001127675459#ZH-CN_TOPIC_0000001569011701__li89603794812)中的版本号。 |

### Schema

| 参数名称 | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                                                     |
| :------- | :------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- |
| n        | M                   | String                                                       | 对象类型名称。                                               |
| fs       | M                   | List<[SchemaField](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section129653168386)> | 字段名称。删除字段时，该对象必须属于同一个对象类型，且只能传入一个SchemaField。 |

### SchemaField

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明                                                     |
| :------- | :------------------ | :------- | :----------------------------------------------------------- |
| n        | M                   | String   | 字段名。删除操作时必须有如下两个字段，并遵循相关约束：long类型的naturalbase_version字段：该字段不生效，可设置为任意值。boolean类型的naturalbase_deleted字段：需设置为固定值“true”。 |
| t        | M                   | String   | 字段类型，取值包含如下字段类型：1：TYPE_BOOLEAN，布尔类型。2：TYPE_BYTE，byte类型。3：TYPE_SHORT，short类型。4：TYPE_INT32，int类型。5：TYPE_LONG，long类型。6：TYPE_FLOAT，float类型。7：TYPE_DOUBLE，double类型。8：TYPE_BYTE_ARRAY，byte数组类型。9：TYPE_STRING，String类型。10：TYPE_DATE，date类型。11：TYPE_TEXT，文本类型。12：TYPE_AUTO_INCREMENT_INT，int自增类型。13：TYPE_AUTO_INCREMENT_LONG，long自增类型。 |

### OperatorData

| 参数名称 | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                                                     |
| :------- | :------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- |
| os       | M                   | List<[Field](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section156861057163820)> | 操作对象信息。该对象必须属于同一个对象类型，且仅支持传入一个Field。 |
| t        | M                   | integer                                                      | 删除操作类型，入参为“1”。                                    |

### Field

| 参数名称 | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                                                     |
| :------- | :------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- |
| fs       | M                   | List<[FieldValue](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section1176810453917)> | 单条对象信息。说明删除操作中包含主键、naturalbase_deleted的字段固定设置值为true。 |

### FieldValue

说明

删除数据时，删除字段的数据类型与[SchemaField](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section129653168386)中的参数类型需保持一致。

| 参数名称 | 必选（M）/可选（O） | 参数类型  | 参数说明        |
| :------- | :------------------ | :-------- | :-------------- |
| n        | O                   | boolean   | 是否设置为null  |
| bl       | O                   | boolean   | boolean类型值   |
| b        | O                   | byte      | byte类型值      |
| st       | O                   | short     | short类型值     |
| i        | O                   | int       | int类型值       |
| l        | O                   | long      | long类型值      |
| f        | O                   | float     | float类型值     |
| d        | O                   | double    | double类型值    |
| ba       | O                   | byteArray | byteArray类型值 |
| s        | O                   | String    | String类型值    |

**请求示例**

预定义一个存储区(cloudDBZone)、对象类型StudentInfo(id integer primary key, name string, age integer);

```cangjie
POST agc/apigw/clouddb/clouddbservice/sync/upsert?_v=4content-type: application/jsonclient_id: 74************40Authorization: Bearer ***productId: 99************83access_token: ***host: connect-drcn.dbankcloud.cn{  "msgInfo": {    "type": 3,    "opStore": {      "storeName": "cloudDBZone"    }  },  "clientInfo": {    "appVer": 1  },  "schemas": [    {      "n": "StudentInfo",      "fs": [        {          "n": "id",          "t": "TYPE_INT32"        },        {          "n": "naturalbase_version",          "t": "TYPE_LONG"        },        {          "n": "naturalbase_deleted",          "t": "TYPE_BOOLEAN"        }      ]    }  ],  "opData": [    {      "os": [        {          "fs": [            {              "i": 1            },            {              "l": null            },            {              "bl": true            }          ]        }      ],      "t": 1    }  ]}
```

## 响应参数

| 参数名称     | 必选（M）/可选（O） | 参数类型                                                     | 参数说明                 |
| :----------- | :------------------ | :----------------------------------------------------------- | :----------------------- |
| msgInfo      | O                   | [MsgInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section19632115714018) | 返回消息的基本信息。     |
| resInfo      | O                   | [ResponseInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section1851916379417) | 返回响应的基本状态信息。 |
| updateResMsg | O                   | [UpdateResponseMessage](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/clouddb-delete-data-rest-0000001449956714#section06631914426) | 返回响应的更新信息。     |

### MsgInfo

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明                                                     |
| :------- | :------------------ | :------- | :----------------------------------------------------------- |
| type     | M                   | integer  | 更新请求，入参需为“3”。“3”：更新数据或删除数据请求。“5”：查询数据请求。 |
| opStore  | M                   | Json     | JSON字符串。格式为{"storeName": "cloudDBZone"}。cloudDBZone为存储区名。 |

### ResponseInfo

| 参数名称 | 必选（M）/可选（O） | 参数类型 | 参数说明       |
| :------- | :------------------ | :------- | :------------- |
| resCode  | O                   | integer  | 响应状态码。   |
| resInfo  | O                   | String   | 响应描述信息。 |

### UpdateResponseMessage

| 参数名称        | 必选（M）/可选（O） | 参数类型 | 参数说明       |
| :-------------- | :------------------ | :------- | :------------- |
| successRecCount | O                   | integer  | 成功更新条数。 |

**响应示例**

```cangjie
{    "msgInfo": {        "id": "1",        "type": 3,        "opStore": {            "storeName": "string"        }    },    "resInfo": {},    "updateResMsg": {        "successRecCount": 1    }}
```

# 错误码

更新时间: 2024-08-19 17:20







| 错误码（errorCode） | 错误描述（errorMsg）                     |
| :------------------ | :--------------------------------------- |
| 0                   | 成功。                                   |
| 203816961           | 内部错误。                               |
| 203817219           | 无效产品ID。                             |
| 203817221           | PROVIDER不能为空。                       |
| 203817223           | EMAIL格式校验失败。                      |
| 203817224           | 手机号格式校验失败。                     |
| 203817730           | 获取用户信息失败。                       |
| 203817988           | 第三方认证方式关闭。                     |
| 203817989           | 获取第三方信息失败。                     |
| 203818032           | 用户未注册。                             |
| 203818034           | 邮箱或者手机登录的时候鉴权信息不能为空。 |
| 203818053           | 验证码发送到达限制。                     |
| 203818054           | 项目hash值不存在。                       |
| 203818069           | 请求参数为空。                           |
| 203818080           | 更新信息请求错误。                       |
| 203818129           | 验证码格式错误。                         |
| 203818130           | 用户已注册。                             |
| 203818135           | 验证码和密码都为空。                     |
| 203818241           | 发送消息失败。                           |
| 203818260           | 自动创建用户错误。                       |