1. # 获取服务端API授权

2. ## 创建API客户端

3. API客户端是AGC用于管理用户访问AppGallery Connect API的身份凭据。在访问某个API前，必须创建有权访问该API的API客户端。

4. 1. 登录[AppGallery Connect](https://developer.huawei.com/consumer/cn/service/josp/agc/index.html)，点击“开发与服务”。

   2. 在项目列表中选择需要获取凭证的项目，在“项目设置”页面点击“Server SDK”页签。

   3. 点击认证凭据区域内“API客户端”旁的“创建”。

      ![img](https://alliance-communityfile-drcn.dbankcdn.com/FileServer/getFile/cmtyPub/011/111/111/0000000000011111111.20250704165004.59758760941328382750660752966473:50001231000000:2800:67787B55E69C1F7C33FFA1FE14C2159E57FA4004A79FA4D68DDDA18401D69869.png)

   4. 在弹出的提示框内点击“确认”，完成认证凭据创建，点击“下载认证凭据”下载json文件，获取文件中的client_id和client_secret信息。

      ![img](https://alliance-communityfile-drcn.dbankcdn.com/FileServer/getFile/cmtyPub/011/111/111/0000000000011111111.20250704165004.89078122843243412012554002308407:50001231000000:2800:B3B1E8FBFC9C29A727A66325DE8B7D3EF9A267CFA99C4EB01E3DC21170051DEC.png)

5. ## 获取访问API的Token

6. 创建完API客户端后需要到华为AGC平台进行鉴权，鉴权通过后将获得用于访问AppGallery Connect API的Access Token。用户凭借该Access Token即可访问REST API。您可以调用[获取Token](https://developer.huawei.com/consumer/cn/doc/development/AppGallery-connect-References/agcapi-obtain-token-project-0000001477336048)接口来获取Access Token。

7. 

8. # 获取Token（项目级）

9. 更新时间: 2025-08-06 18:02

10. ## 功能介绍

11. 在使用API客户端方式调用Connect API的接口前，需要通过华为开放平台进行鉴权，并获取认证通过后的Token。

12. ## 接口原型

13. | 承载协议 | HTTPS POST                                                   |
    | :------- | ------------------------------------------------------------ |
    | 接口方向 | 开发者服务器 -> 华为服务器                                   |
    | 接口URL  | https://{domain}/api/oauth2/v1/token中国站点的domain：connect-api.cloud.huawei.com德国站点的domain：connect-api-dre.cloud.huawei.com新加坡站点的domain：connect-api-dra.cloud.huawei.com俄罗斯站点的domain：connect-api-drru.cloud.huawei.com注意本接口使用的domain必须是项目设置的数据处理位置对应的domain，例如：项目设置数据处理位置为中国，那么本接口中的domain必须使用“connect-api.cloud.huawei.com”； |
    | 数据格式 | 请求：Content-Type: application/json响应：Content-Type: application/json |

14. ## 请求参数

15. 请求参数以JSON格式传入，包含参数如下。

16. | 参数名称      | 必选(M)/可选(O) | 数据类型     | 参数说明                                                     |
    | :------------ | :-------------- | :----------- | :----------------------------------------------------------- |
    | grant_type    | M               | String(256)  | 固定传入“client_credentials”。                               |
    | client_id     | M               | String(256)  | 客户端ID，即[下载项目级凭证](https://developer.huawei.com/consumer/cn/doc/development/AppGallery-connect-Guides/agc-get-started-server-0000001058092593#section1778162811430)agc-apiclient-*.json文件中的client_id。 |
    | client_secret | M               | String(2048) | 客户端密钥，即[下载项目级凭证](https://developer.huawei.com/consumer/cn/doc/development/AppGallery-connect-Guides/agc-get-started-server-0000001058092593#section1778162811430)agc-apiclient-*.json文件中的client_secret。 |

17. ## 请求示例

18. ```cangjie
    POST /api/oauth2/v1/tokenHost: connect-api.cloud.huawei.comContent-Type: application/json{   "grant_type":"client_credentials",   "client_id":"26********20",   "client_secret":"************************"}
    ```

19. ## 响应参数

20. 返回值为JSON格式的字符串，包含参数如下。

21. | 参数名称     | 必选(M)/可选(O) | 数据类型    | 参数说明                                                     |
    | :----------- | :-------------- | :---------- | :----------------------------------------------------------- |
    | access_token | O               | String      | 认证Token，用于AppGallery Connect API接口调用。此参数只在获取成功时返回。 |
    | expires_in   | O               | Long        | access_token的有效期，单位秒。您需要在过期时间到达时重新调用本接口获取新的access_token。有效期为48小时，如果在有效期内再次调用接口获取access_token时，新老access_token都是有效的。此参数只在获取成功时返回。 |
    | ret          | O               | String(100) | 获取Token失败时的错误信息，包含错误码及描述信息的JSON字符串，格式为{"code":*retcode*, "msg": "*description*"}，retcode为错误码，description为错误码描述信息。 |

22. ## 响应示例

23. ```cangjie
    HTTP/1.1 200 OKContent-Type: application/json; charset=utf-8{    "access_token": "eyJhbGciOiJIUzU****************",        "expires_in": 172800}
    ```

24. ## 调用示例

25. ```typescript
    public static String getToken(String domain, String clientId, String clientSecret) {    String token = null;    try {        HttpPost post = new HttpPost(domain + "/oauth2/v1/token");
            JSONObject keyString = new JSONObject();        keyString.put("client_id", "18893***83957248");        keyString.put("client_secret", "B15B497B44E080EBE2C4DE4E74930***52409516B2A1A5C8F0FCD2C579A8EB14");        keyString.put("grant_type", "client_credentials");
            StringEntity entity = new StringEntity(keyString.toString(), Charset.forName("UTF-8"));        entity.setContentEncoding("UTF-8");        entity.setContentType("application/json");        post.setEntity(entity);
            CloseableHttpClient httpClient = HttpClients.createDefault();        HttpResponse response = httpClient.execute(post);        int statusCode = response.getStatusLine().getStatusCode();        if (statusCode == HttpStatus.SC_OK) {
                BufferedReader br =                new BufferedReader(new InputStreamReader(response.getEntity().getContent(), Consts.UTF_8));            String result = br.readLine();            JSONObject object = JSON.parseObject(result);            token = object.getString("access_token");        }
            post.releaseConnection();        httpClient.close();    } catch (Exception e) {
        }    return token;}
    ```

26. 

27. 

28. # 上传文件

29. ## 功能介绍

30. 此接口用于上传文件。

31. ## 接口原型

32. | 承载协议 | HTTPS PUT                                                    |
    | :------- | ------------------------------------------------------------ |
    | 接口方向 | 开发者服务器->华为服务器                                     |
    | 接口URL  | https://{domain}/{bucket_name}/{object_name}注意{bucket_name}为当前存储实例名称，{object_name}为待上传的文件名称。{domain}为接口域名。中国站点的域名：ops-server-drcn.agcstorage.link/v0德国站点的域名：ops-server-dre.agcstorage.link/v0新加坡站点的域名：ops-server-dra.agcstorage.link/v0俄罗斯站点的域名：ops-server-drru.agcstorage.link/v0调用[获取Token](https://developer.huawei.com/consumer/cn/doc/development/AppGallery-connect-References/agcapi-obtain-token-project-0000001477336048)接口时使用的站点必须与本接口使用的站点保持一致。例如本接口使用的站点是德国，即接口域名为“ops-server-dre.agcstorage.link/v0”，则调用[获取Token](https://developer.huawei.com/consumer/cn/doc/development/AppGallery-connect-References/agcapi-obtain-token-project-0000001477336048)接口也必须使用德国站点，其接口域名需为“connect-api-dre.cloud.huawei.com”。 |
    | 数据格式 | 请求：Content-Type: application/json响应：Content-Type: application/json |

33. ## 请求参数

34. ### Header

35. 说明

36. 单次请求所有的header数量不超过40个。

37. | 参数                      | 类型   | 必选(M)/可选(O) | 说明                                                         |
    | :------------------------ | :----- | :-------------- | :----------------------------------------------------------- |
    | client_id                 | String | M               | 客户端ID，获取方法参考[创建API客户端](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-Guides/agc-storage-getapicredentials-0000001498508514#section8727185210538)。 |
    | productId                 | String | M               | 项目ID，查询方法可参见[查询项目ID](https://developer.huawei.com/consumer/cn/doc/development/AppGallery-connect-Guides/agc-get-developerid-projectid-0000001166543063)。 |
    | Authorization             | String | M               | 认证信息，格式为“Authorization: Bearer ${access_token}”。access_token为[获取Token](https://developer.huawei.com/consumer/cn/doc/development/AppGallery-connect-References/agcapi-obtain-token-project-0000001477336048)中获取的access_token。 |
    | X-Agc-File-Size           | String | O               | 文件大小，断点续传时为必选。                                 |
    | X-Agc-File-Offset         | String | O               | 文件偏移量，断点续传的起始位置非零时为必选。                 |
    | X-Agc-Sha256              | String | O               | 文件的SHA256值，断点续传时为必选。                           |
    | X-Agc-Content-Type        | String | O               | 文件类型。默认值：application/octet-stream                   |
    | X-Agc-Content-Disposition | String | O               | 文件打开方式。                                               |
    | X-Agc-Content-Encoding    | String | O               | HTTP标准头部Content-Encoding。                               |
    | X-Agc-Cache-Control       | String | O               | HTTP标准头部Cache-Control。                                  |
    | X-Agc-Content-Language    | String | O               | HTTP标准头部Content-Language。                               |
    | X-Agc-meta-*              | String | O               | 可以在请求中加入以“X-Agc-meta-”开头的消息头，用于加入自定义的元数据，以便对文件进行自定义管理。当用户获取此文件或查询此文件元数据时，加入的自定义元数据将会在返回消息的头部出现。X-Agc-meta-仅标记此header是传递元数据，并非元数据key的一部分。例如，您传入的是“X-Agc-meta-test: test metadata”，保存的数据实例为“test: test metadata”。说明元数据名称相同则覆盖。自定义的部署不区分大小写，最后记录均为小写的方式。 |
    | X-Agc-Trace-Id            | String | O               | 单个文件请求的Traceid。可不填或者随机生成，用于日志打印跟踪。 |

38. ## 请求示例

39. ```yaml
    PUT /v0/testagc-02reg/test5.jpgclient_id: 84****32064productId: 736430****461998Content-Type: application/jsonX-Agc-Trace-Id: 123X-Agc-File-Offset: 0X-Agc-File-Size: 12X-Agc-Sha256: 11Authorization: Bearer ****User-Agent: PostmanRuntime/7.6.0Accept: */*Host: ops-server-drcn.agcstorage.linkaccept-encoding: gzip, deflatecontent-length: 2536
    ```

40. ## 响应参数

41. ### Header

42. | 参数           | 类型    | 必选(M)/可选(O) | 说明                                                      |
    | :------------- | :------ | :-------------- | :-------------------------------------------------------- |
    | status         | Integer | M               | HTTP响应码，200表示成功。                                 |
    | X-Agc-Trace-Id | String  | O               | 单个文件请求的Traceid，与请求参数X-Agc-Trace-Id保持一致。 |

43. ### Body

44. | 参数         | 类型                                                         | 必选(M)/可选(O) | 说明                                                         |
    | :----------- | :----------------------------------------------------------- | :-------------- | :----------------------------------------------------------- |
    | uploadStatus | String                                                       | M               | 上传状态。resumable：断点续传finalize：上传完成              |
    | receiveBytes | Long                                                         | O               | 已上传字节。从0开始，仅支持顺序上传。文件未上传完毕时返回该字段。 |
    | fileInfo     | [FileInfo](https://developer.huawei.com/consumer/cn/doc/AppGallery-connect-References/storage-restapi-fileinfo-0000001498838610) | O               | 文件的详细信息。                                             |

45. ## 响应示例

46. ```cangjie
    HTTP/1.1 200status: 200Date: Mon, 27 Mar 2023 03:23:25 GMTContent-Type: text/plainTransfer-Encoding: chunkedConnection: keep-aliveX-Agc-Trace-Id: 123Server: elb{"uploadStatus":"finalize","fileInfo":{"updateTime":"2023-03-27T03:23:24Z","bucket":"testagc-02reg","name":"test5.jpg","storageType":"STANDARD","createTime":"2023-03-27T03:23:24Z","contentType":"application\/octet-stream","size":2536,"storageArea":"CN"}}
    ```

47. ## 调用示例

48. ```java
    // 获取Token公共类// TokenServiceTest .javaimport com.alibaba.fastjson.JSON;import com.alibaba.fastjson.JSONObject;
    import org.apache.http.Consts;import org.apache.http.HttpResponse;import org.apache.http.HttpStatus;import org.apache.http.client.methods.HttpPost;import org.apache.http.entity.StringEntity;import org.apache.http.impl.client.CloseableHttpClient;import org.apache.http.impl.client.HttpClients;
    import java.io.BufferedReader;import java.io.IOException;import java.io.InputStreamReader;import java.nio.charset.Charset;
    /** * 获取accessToken * */public class TokenServiceTest {    /**     * @param domain 域名     * @param clientId clientId     * @param clientSecret clientSecret     * @return accessToken     */    public static String getToken(String domain, String clientId, String clientSecret) {        String token = null;        CloseableHttpClient httpClient = HttpClients.createDefault();        HttpPost post = new HttpPost(domain + "/oauth2/v1/token");        try {            JSONObject keyString = new JSONObject();            keyString.put("client_id", clientId);            keyString.put("client_secret", clientSecret);            keyString.put("grant_type", "client_credentials");
                StringEntity entity = new StringEntity(keyString.toString(), Charset.forName("UTF-8"));            entity.setContentEncoding("UTF-8");            entity.setContentType("application/json");            post.setEntity(entity);            HttpResponse response = httpClient.execute(post);            int statusCode = response.getStatusLine().getStatusCode();            if (statusCode == HttpStatus.SC_OK) {                BufferedReader br =                    new BufferedReader(new InputStreamReader(response.getEntity().getContent(), Consts.UTF_8));                String result = br.readLine();                JSONObject object = JSON.parseObject(result);                token = object.getString("access_token");            }
            } catch (Exception e) {            throw new RuntimeException("Get Token Exception");        } finally {            post.releaseConnection();            try {                httpClient.close();            } catch (IOException e) {                throw new RuntimeException("Close httpClient Exception");            }        }        return token;    }}
    // UploadObjectTest.javaimport com.alibaba.fastjson.JSON;import com.alibaba.fastjson.JSONObject;
    import lombok.Builder;import lombok.Getter;import lombok.extern.slf4j.Slf4j;
    import org.apache.commons.lang3.StringUtils;import org.apache.http.Consts;import org.apache.http.HttpStatus;import org.apache.http.client.methods.CloseableHttpResponse;import org.apache.http.client.methods.HttpPut;import org.apache.http.client.utils.URIBuilder;import org.apache.http.entity.ContentType;import org.apache.http.entity.InputStreamEntity;import org.apache.http.impl.client.CloseableHttpClient;import org.apache.http.impl.client.HttpClients;import org.junit.Ignore;
    import java.io.BufferedReader;import java.io.File;import java.io.FileInputStream;import java.io.IOException;import java.io.InputStream;import java.io.InputStreamReader;import java.io.RandomAccessFile;import java.security.MessageDigest;
    import javax.xml.bind.DatatypeConverter;
    /** * 上传文件REST API示例代码 */@Slf4j@Ignorepublic class UploadObjectTest {    /**     * 上传文件     *     * @param storageUrl 云存储url     * @param param 上传文件接口入参     * @param offset 文件偏移量，普通上传置为-1即可。如果是分片上传，则需要填具体的值。     * @param fileSize 文件总大小     * @param inputStreamEntity 文件流     * @throws Exception 异常     */    public static void uploadObject(String storageUrl, UploadObjectParam param, long offset, long fileSize,        InputStreamEntity inputStreamEntity) throws Exception {        URIBuilder uriBuilder = new URIBuilder(storageUrl + param.getBucketName() + "/" + param.getObjectName());        HttpPut httpPut = new HttpPut(uriBuilder.build());        httpPut.setHeader("productId", param.getProjectId());        httpPut.setHeader("client_id", param.getClientId());        httpPut.setHeader("Authorization", "Bearer " + param.getToken());        httpPut.setHeader("X-Agc-File-Size", String.valueOf(fileSize));        if (StringUtils.isNotEmpty(param.getSha256())) {            // 文件的sha256，断点续传、分片上传时为必填            httpPut.setHeader("X-Agc-Sha256", param.getSha256());        }        if (offset >= 0) {            // 文件偏移，，断点续传、分片上传时的起始位置非零时为必填            httpPut.setHeader("X-Agc-File-Offset", String.valueOf(offset));        }        try (CloseableHttpClient httpClient = HttpClients.createDefault()) {            httpPut.setEntity(inputStreamEntity);            CloseableHttpResponse httpResponse = httpClient.execute(httpPut);            int statusCode = httpResponse.getStatusLine().getStatusCode();            if (statusCode == HttpStatus.SC_OK) {                BufferedReader br =                    new BufferedReader(new InputStreamReader(httpResponse.getEntity().getContent(), Consts.UTF_8));                String result = br.readLine();                JSONObject object = JSON.parseObject(result);                log.info("uploadObject result:{}", object.toJSONString());                br.close();            }            httpResponse.close();        }    }
        /**     * 分片上传     *     * @throws Exception 异常     */    public void chunkClient() throws Exception {        String clientToken = TokenServiceTest.getToken("https://connect-api.cloud.huawei.com/api/",            "84903XXXXXX32064", "00E5CCADB655891XXXXXXXXXXXX8CDCC83ACF22");        // 分片的大小        int chunkSize = 1024 * 1024;
            // 获取文件输入流        File file = new File(getClass().getClassLoader().getResource("run.log").getFile());        // 获取文件总大小        long fileSize = file.length();        // 计算分片数量        int chunkCount = (int) Math.ceil((double) fileSize / chunkSize);
            UploadObjectParam param = UploadObjectParam.builder()            .projectId("73643XXXXXX61998")            .clientId("84903XXXXXX32064")            .token(clientToken)            .bucketName("test-q36q0")            .objectName("temp/run.log")            .sha256(getSha256(file.getPath()))            .build();        // 创建一个RandomAccessFile用来读取文件        try (RandomAccessFile raf = new RandomAccessFile(file, "r")) {            // 逐个分片上传            for (int i = 0; i < chunkCount; i++) {                // 计算当前分片的起始位置和长度                long offset = i * chunkSize;                long length = Math.min(chunkSize, fileSize - offset);                // 构造请求实体，包含分片数据                InputStream inputStream = new InputStreamSegment(raf, offset, length);                InputStreamEntity entity = new InputStreamEntity(inputStream, length);                uploadObject("https://ops-server-drcn.agcstorage.link/v0/", param, offset, file.length(), entity);            }        }    }
        /**     * 普通文件上传     *     * @throws Exception     */    public void client() throws Exception {        String clientToken = TokenServiceTest.getToken("https://connect-api.cloud.huawei.com/api/",            "84903XXXXXX32064", "00E5CCADB655891XXXXXXXXXXXX8CDCC83ACF22");        UploadObjectParam param = UploadObjectParam.builder()            .projectId("401697XXXXXX27846")            .clientId("84412XXXXXX3648")            .token(clientToken)            .bucketName("test-q36q0")            .objectName("temp/hello.txt")            .build();        File file = new File(getClass().getClassLoader().getResource("hello.txt").getFile());        FileInputStream fis = new FileInputStream(file);        InputStreamEntity inputStreamEntity =            new InputStreamEntity(fis, file.length(), ContentType.APPLICATION_OCTET_STREAM);        uploadObject("https://ops-server-drcn.agcstorage.link/v0/", param, -1, file.length(), inputStreamEntity);    }
        // 获取文件的sha256值    private static String getSha256(String filePath) throws Exception {        FileInputStream fileInputStream = new FileInputStream(filePath);        MessageDigest messageDigest = MessageDigest.getInstance("SHA-256");        byte[] buffer = new byte[1024];        int bytesRead = 0;        while ((bytesRead = fileInputStream.read(buffer)) != -1) {            messageDigest.update(buffer, 0, bytesRead);        }        return DatatypeConverter.printHexBinary(messageDigest.digest());    }
        public static void main(String[] args) throws Exception {        // 文件上传        new UploadObjectTest().client();
            // 分片上传        new UploadObjectTest().chunkClient();    }
        @Builder    @Getter    static class UploadObjectParam {        // 项目ID        String projectId;
            // 客户端ID        String clientId;
            // clientToken        String token;
            // 云存储实例名        String bucketName;
            // 文件名，如果包含 '/' ，则认为是路径分隔符。如：temp/hello.jpg，则会将文件hello.jpg上传到对应存储实例的temp目录下。        String objectName;
            // 文件的sha256，断点续传、分片上传时为必填        String sha256;    }
        static class InputStreamSegment extends InputStream {        private RandomAccessFile raf;
            private long offset;
            private long length;
            private long position;
            public InputStreamSegment(RandomAccessFile raf, long offset, long length) {            this.raf = raf;            this.offset = offset;            this.length = length;            position = 0;        }
            @Override        public int read() throws IOException {            if (position >= length) {                return -1;            }            raf.seek(offset + position);            int result = raf.read();            if (result >= 0) {                position++;            }            return result;        }
            @Override        public int read(byte[] b, int off, int len) throws IOException {            if (position >= length) {                return -1;            }            raf.seek(offset + position);            int bytesToRead = (int) Math.min(len, length - position);            int bytesRead = raf.read(b, off, bytesToRead);            if (bytesRead >= 0) {                position += bytesRead;            }            return bytesRead;        }
            @Override        public void close() throws IOException {        }    }}
    ```
