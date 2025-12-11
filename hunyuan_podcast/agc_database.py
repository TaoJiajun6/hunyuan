"""
华为AGC云数据库客户端（使用REST API）
用于存储和读取播客元数据
"""
import os
import json
import logging
import requests
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# 尝试导入AGC认证相关函数
try:
    from .upload_client import get_agc_token, _find_agc_client_json, _load_agc_credentials_from_file
    HAS_AGC_AUTH = True
except ImportError:
    HAS_AGC_AUTH = False
    logger.warning("无法导入AGC认证模块，云数据库功能可能不可用")


class AGCDatabaseClient:
    """AGC云数据库客户端（使用REST API）"""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        product_id: Optional[str] = None,
        domain: Optional[str] = None,
        cloud_db_zone: str = "cloudDBZone",
        api_key: Optional[str] = None
    ):
        """
        初始化AGC云数据库客户端
        
        Args:
            client_id: AGC Client ID（用于获取access_token，如果使用OAuth认证）
            client_secret: AGC Client Secret（用于获取access_token，如果使用OAuth认证）
            product_id: AGC Product ID（项目ID）
            domain: AGC API域名，默认 connect-drcn.dbankcloud.cn
            cloud_db_zone: CloudDB存储区名称，默认 cloudDBZone
            api_key: 服务端 API Key（用于CloudDB REST API，优先级高于OAuth client_id）
        
        注意：CloudDB REST API 需要使用服务端 API Key，而不是 OAuth client_id。
        请在 AGC 控制台 > 我的项目 > API管理 > 凭据 中创建服务端 API Key。
        """
        # 优先使用 API Key（服务端认证）
        self.api_key = api_key or os.getenv('AGC_API_KEY')
        
        # OAuth 凭证（用于获取 token，如果未提供 API Key）
        # 云数据库优先使用专用的client_id和client_secret，如果没有则使用通用的
        self.client_id = client_id or os.getenv('AGC_DATABASE_CLIENT_ID') or os.getenv('AGC_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('AGC_DATABASE_CLIENT_SECRET') or os.getenv('AGC_CLIENT_SECRET')
        self.product_id = product_id or os.getenv('AGC_PRODUCT_ID')
        # CloudDB 优先使用专用域名，如果没有则使用通用域名
        # CloudDB 和 Token 获取必须使用 connect-drcn.dbankcloud.cn
        env_domain = domain or os.getenv('AGC_DATABASE_DOMAIN') or os.getenv('AGC_DOMAIN', 'connect-drcn.dbankcloud.cn')
        if env_domain == 'connect-api.cloud.huawei.com':
            # 自动修正为正确的 CloudDB 域名
            logger.warning(f"检测到域名 {env_domain}，CloudDB 需要使用 connect-drcn.dbankcloud.cn，已自动修正")
            self.domain = 'connect-drcn.dbankcloud.cn'
        else:
            self.domain = env_domain
        # 优先使用环境变量，如果没有环境变量则使用参数值或默认值
        self.cloud_db_zone = os.getenv('AGC_CLOUD_DB_ZONE') or cloud_db_zone or 'cloudDBZone'
        
        # 如果没有提供认证信息，尝试从文件读取
        if not self.api_key and (not self.client_id or not self.client_secret):
            if HAS_AGC_AUTH:
                cfg_path = _find_agc_client_json()
                if cfg_path:
                    cid, csecret, proj = _load_agc_credentials_from_file(cfg_path)
                    self.client_id = self.client_id or cid
                    self.client_secret = self.client_secret or csecret
                    self.product_id = self.product_id or proj
        
        # CloudDB REST API基础URL
        self.base_url = f"https://{self.domain}/agc/apigw/clouddb/clouddbservice/sync"
        
        # 对象类型名称（表名）
        self.object_type = "PodcastInfo"
        
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
    
    def _get_access_token(self) -> Optional[str]:
        """
        获取AGC access token
        
        如果配置了 API Key，直接返回 API Key（服务端认证）
        否则使用 OAuth 客户端凭证获取 token
        """
        # 如果使用 API Key，直接返回（不需要 token）
        if self.api_key:
            return self.api_key
        
        # 使用 OAuth 认证
        if not HAS_AGC_AUTH:
            logger.warning("AGC认证模块不可用，且未配置 API Key，无法获取access token")
            return None
        
        # 如果token未过期，直接返回
        if self._access_token and self._token_expires_at:
            import time
            if time.time() < self._token_expires_at - 60:  # 提前1分钟刷新
                return self._access_token
        
        try:
            # 使用客户端凭证获取token（云数据库使用 connect-drcn.dbankcloud.cn）
            token, expires_in = get_agc_token(
                domain=self.domain,
                client_id=self.client_id,
                client_secret=self.client_secret,
                timeout=30,
                service_type='database'  # 云数据库使用不同的Token接口
            )
            
            if token:
                self._access_token = token
                import time
                self._token_expires_at = time.time() + expires_in
                return token
        except Exception as e:
            error_msg = str(e)
            if "type of clientId not match" in error_msg or "203886599" in error_msg:
                logger.error(
                    "获取 access token 失败：clientId 类型不匹配。\n"
                    "CloudDB REST API 需要使用服务端 API Key，而不是 OAuth client_id。\n"
                    "请在 AGC 控制台 > 我的项目 > API管理 > 凭据 中创建服务端 API Key，\n"
                    "然后设置环境变量 AGC_API_KEY=你的API_KEY"
                )
            else:
                logger.error(f"获取AGC access token失败: {e}")
        
        return None
    
    def _get_schema(self) -> Dict:
        """
        获取PodcastInfo对象的Schema定义
        
        Returns:
            Schema定义字典
        """
        return {
            "n": self.object_type,
            "fs": [
                {"n": "id", "t": "TYPE_STRING"},  # 主键
                {"n": "title", "t": "TYPE_STRING"},
                {"n": "audio_url", "t": "TYPE_STRING"},
                {"n": "local_file", "t": "TYPE_STRING"},
                {"n": "created_at", "t": "TYPE_LONG"},
                {"n": "duration", "t": "TYPE_LONG"},
                {"n": "category", "t": "TYPE_STRING"},
                {"n": "status", "t": "TYPE_STRING"},
                {"n": "script", "t": "TYPE_TEXT"},  # 改为TEXT类型，支持长文本
                {"n": "file_size_mb", "t": "TYPE_DOUBLE"},
                {"n": "topic", "t": "TYPE_STRING"},
                {"n": "roles", "t": "TYPE_STRING"},  # JSON字符串
                {"n": "naturalbase_version", "t": "TYPE_LONG"},
                {"n": "naturalbase_deleted", "t": "TYPE_BOOLEAN"}
            ]
        }
    
    def _convert_to_clouddb_format(self, podcast_data: Dict[str, Any]) -> Dict:
        """
        将播客数据转换为CloudDB格式
        
        Args:
            podcast_data: 播客数据字典
        
        Returns:
            CloudDB格式的数据字典
        """
        # 处理roles字段（如果是列表，转换为JSON字符串）
        roles_str = podcast_data.get('roles', '[]')
        if isinstance(roles_str, list):
            roles_str = json.dumps(roles_str, ensure_ascii=False)
        elif roles_str is None:
            roles_str = '[]'
        
        # 处理duration字段（确保是整数或None）
        duration = podcast_data.get('duration')
        if duration is not None:
            try:
                duration = int(duration)
            except (ValueError, TypeError):
                duration = None
        
        # 处理file_size_mb字段（确保是浮点数或None）
        file_size_mb = podcast_data.get('file_size_mb')
        if file_size_mb is not None:
            try:
                file_size_mb = float(file_size_mb)
            except (ValueError, TypeError):
                file_size_mb = None
        
        return {
            "fs": [
                {"s": str(podcast_data.get('id', ''))},  # id (主键)
                {"s": str(podcast_data.get('title', ''))},  # title
                {"s": str(podcast_data.get('audio_url') or '')},  # audio_url
                {"s": str(podcast_data.get('local_file') or '')},  # local_file
                {"l": int(podcast_data.get('created_at', 0))},  # created_at
                {"l": duration},  # duration (整数或None)
                {"s": str(podcast_data.get('category') or '')},  # category
                {"s": str(podcast_data.get('status', 'completed'))},  # status
                {"s": str(podcast_data.get('script') or '')},  # script
                {"d": file_size_mb},  # file_size_mb (浮点数或None)
                {"s": str(podcast_data.get('topic') or '')},  # topic
                {"s": str(roles_str)},  # roles (JSON字符串)
                {"l": None},  # naturalbase_version
                {"bl": False}  # naturalbase_deleted
            ]
        }
    
    def _convert_from_clouddb_format(self, clouddb_data: Dict) -> Dict[str, Any]:
        """
        将CloudDB格式转换为播客数据格式
        
        Args:
            clouddb_data: CloudDB格式的数据字典
        
        Returns:
            播客数据字典
        """
        fs = clouddb_data.get('fs', [])
        logger.debug(f"转换CloudDB数据，字段数量: {len(fs)}")
        
        # 字段数量应该至少是12个（不包括naturalbase_version和naturalbase_deleted）
        # 但为了兼容性，我们允许更少的字段
        if len(fs) < 12:
            logger.warning(f"字段数量不足: {len(fs)} < 12，原始数据: {json.dumps(clouddb_data, ensure_ascii=False)}")
            return {}
        
        # 解析roles字段（索引11）
        roles = '[]'
        if len(fs) > 11:
            roles = fs[11].get('s', '[]')
        try:
            roles = json.loads(roles) if roles else []
        except:
            roles = []
        
        # 安全地获取字段值，使用索引访问
        podcast = {
            'id': fs[0].get('s', '') if len(fs) > 0 else '',
            'title': fs[1].get('s', '') if len(fs) > 1 else '',
            'audio_url': fs[2].get('s', '') if len(fs) > 2 else '',
            'local_file': fs[3].get('s', '') if len(fs) > 3 else '',
            'created_at': fs[4].get('l', 0) if len(fs) > 4 else 0,
            'duration': fs[5].get('l') if len(fs) > 5 else None,
            'category': fs[6].get('s', '') if len(fs) > 6 else '',
            'status': fs[7].get('s', 'completed') if len(fs) > 7 else 'completed',
            'script': fs[8].get('s', '') if len(fs) > 8 else '',
            'file_size_mb': fs[9].get('d') if len(fs) > 9 else None,
            'topic': fs[10].get('s', '') if len(fs) > 10 else '',
            'roles': roles
        }
        
        logger.debug(f"转换后的播客数据: {json.dumps(podcast, ensure_ascii=False, default=str)}")
        return podcast
    
    def save_podcast(self, podcast_data: Dict[str, Any]) -> bool:
        """
        保存播客数据到云数据库（新增或更新）
        
        Args:
            podcast_data: 播客数据字典，必须包含 'id' 字段
        
        Returns:
            是否保存成功
        """
        if not podcast_data.get('id'):
            logger.error("播客数据缺少 'id' 字段")
            return False
        
        token = self._get_access_token()
        if not token:
            logger.error("无法获取access token，跳过云数据库操作")
            return False
        
        try:
            # 确保时间戳是整数
            if 'created_at' in podcast_data and isinstance(podcast_data['created_at'], float):
                podcast_data['created_at'] = int(podcast_data['created_at'])
            
            # 转换为CloudDB格式
            clouddb_data = self._convert_to_clouddb_format(podcast_data)
            
            # 构造upsert请求
            url = f"{self.base_url}/upsert?_v=4"
            
            # 如果使用 API Key，在 headers 中使用 API Key
            # 如果使用 OAuth token，使用 Bearer token
            if self.api_key:
                headers = {
                    "content-type": "application/json",
                    "client_id": self.api_key,  # 使用 API Key 作为 client_id
                    "productId": self.product_id,
                    "host": self.domain
                }
            else:
                # 根据官方文档，需要同时使用 Authorization: Bearer 和 access_token
                # Authorization: Bearer 是必须的（客户端token）
                # access_token 是可选的（用户登录token，匿名账号可以为空）
                headers = {
                    "content-type": "application/json",
                    "client_id": self.client_id,
                    "Authorization": f"Bearer {token}",
                    "productId": self.product_id,
                    "access_token": "",  # 匿名账号，设置为空字符串
                    "host": self.domain
                }
            
            payload = {
                "msgInfo": {
                    "type": 3,  # upsert操作
                    "opStore": {
                        "storeName": self.cloud_db_zone
                    }
                },
                "clientInfo": {
                    "appVer": 1
                },
                "schemas": [self._get_schema()],
                "opData": [
                    {
                        "os": [clouddb_data],
                        "t": 1  # 对象类型索引（对应schemas中的索引）
                    }
                ]
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            
            result = resp.json()
            
            # 检查响应状态：云数据库可能返回 ret.code 或 resInfo.resCode
            ret_code = result.get('ret', {}).get('code')
            res_code = result.get('resInfo', {}).get('resCode')
            
            # resCode 1002000 表示成功
            if ret_code == 0 or res_code == 1002000:
                logger.info(f"播客数据已保存到云数据库: {podcast_data['id']}")
                return True
            else:
                ret_msg = result.get('ret', {}).get('msg', '未知错误')
                res_msg = result.get('resInfo', {}).get('resMsg', '')
                error_msg = ret_msg if ret_msg != '未知错误' else res_msg if res_msg else '未知错误'
                
                logger.error(f"保存播客数据到云数据库失败:")
                logger.error(f"  ret.code: {ret_code}")
                logger.error(f"  resInfo.resCode: {res_code}")
                logger.error(f"  错误信息: {error_msg}")
                logger.error(f"  完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                logger.error(f"  播客数据ID: {podcast_data.get('id')}")
                logger.error(f"  播客数据标题: {podcast_data.get('title')}")
                return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"保存播客数据到云数据库时HTTP错误: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"  响应状态码: {e.response.status_code}")
                    logger.error(f"  响应内容: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
                except:
                    logger.error(f"  响应内容: {e.response.text[:500]}")
            return False
        except Exception as e:
            logger.error(f"保存播客数据到云数据库时出错: {e}", exc_info=True)
            logger.error(f"  播客数据: {json.dumps(podcast_data, ensure_ascii=False, indent=2, default=str)}")
            return False
    
    def get_podcast(self, podcast_id: str) -> Optional[Dict[str, Any]]:
        """
        从云数据库获取单个播客数据
        
        Args:
            podcast_id: 播客ID
        
        Returns:
            播客数据字典，如果不存在则返回None
        """
        token = self._get_access_token()
        if not token:
            logger.error("无法获取access token，跳过云数据库操作")
            return None
        
        try:
            # 构造查询请求
            url = f"{self.base_url}/query?_v=4"
            
            # 如果使用 API Key，在 headers 中使用 API Key
            if self.api_key:
                headers = {
                    "content-type": "application/json",
                    "client_id": self.api_key,  # 使用 API Key 作为 client_id
                    "productId": self.product_id,
                    "host": self.domain
                }
            else:
                # 根据官方文档，需要同时使用 Authorization: Bearer 和 access_token
                # Authorization: Bearer 是必须的（客户端token）
                # access_token 是可选的（用户登录token，匿名账号可以为空）
                headers = {
                    "content-type": "application/json",
                    "client_id": self.client_id,
                    "Authorization": f"Bearer {token}",
                    "productId": self.product_id,
                    "access_token": "",  # 匿名账号，设置为空字符串
                    "host": self.domain
                }
            
            # 构造查询条件：id等于指定值
            query_conditions = [
                {
                    "conditionType": "EqualTo",
                    "fieldName": "id",
                    "value": podcast_id
                },
                {
                    "conditionType": "EqualTo",
                    "fieldName": "naturalbase_deleted",
                    "value": False
                },
                {
                    "conditionType": "Limit",
                    "value": {
                        "number": 1,
                        "offset": 0
                    }
                }
            ]
            
            payload = {
                "msgInfo": {
                    "type": 5,  # 查询操作
                    "opStore": {
                        "storeName": self.cloud_db_zone
                    }
                },
                "clientInfo": {
                    "appVer": 1
                },
                "queryReqMsg": {
                    "queryType": 0,
                    "queryTable": self.object_type,
                    "queryCond": json.dumps({"queryConditions": query_conditions})
                }
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            
            result = resp.json()
            # 检查响应状态
            ret_code = result.get('ret', {}).get('code')
            if ret_code == 0 or ret_code is None:  # 成功时 code 可能为 0 或不存在
                # 根据文档，数据在 opData 中
                op_data_list = result.get('opData', [])
                if op_data_list:
                    # 获取第一个 OperatorData 中的对象列表
                    objects = op_data_list[0].get('os', [])
                    if objects and len(objects) > 0:
                        # 转换第一个对象
                        return self._convert_from_clouddb_format(objects[0])
            else:
                error_msg = result.get('ret', {}).get('msg', '未知错误')
                logger.debug(f"查询单个播客失败，错误码: {ret_code}, 错误信息: {error_msg}")
            return None
        except Exception as e:
            logger.debug(f"从云数据库获取播客数据时出错: {e}")
            return None
    
    def list_podcasts(
        self,
        limit: Optional[int] = 50,
        category: Optional[str] = None,
        order_by: str = "created_at",
        order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        从云数据库获取播客列表
        
        Args:
            limit: 返回数量限制。如果为 None，则使用一个很大的值（10000）来获取所有数据
            category: 分类筛选（可选）
            order_by: 排序字段
            order: 排序方向（asc/desc）
        
        Returns:
            播客数据列表
        """
        token = self._get_access_token()
        if not token:
            logger.error("无法获取access token，跳过云数据库操作")
            return []
        
        try:
            # 构造查询请求
            url = f"{self.base_url}/query?_v=4"
            
            # 如果使用 API Key，在 headers 中使用 API Key
            if self.api_key:
                headers = {
                    "content-type": "application/json",
                    "client_id": self.api_key,  # 使用 API Key 作为 client_id
                    "productId": self.product_id,
                    "host": self.domain
                }
            else:
                # 根据官方文档，需要同时使用 Authorization: Bearer 和 access_token
                # Authorization: Bearer 是必须的（客户端token）
                # access_token 是可选的（用户登录token，匿名账号可以为空）
                headers = {
                    "content-type": "application/json",
                    "client_id": self.client_id,
                    "Authorization": f"Bearer {token}",
                    "productId": self.product_id,
                    "access_token": "",  # 匿名账号，设置为空字符串
                    "host": self.domain
                }
            
            # 构造查询条件
            query_conditions = []
            
            # 首先添加过滤条件：只查询未删除的记录
            # 注意：如果数据中没有 naturalbase_deleted 字段，这个条件可能会导致查询不到数据
            # 为了兼容性，我们先尝试查询所有数据，然后在内存中过滤
            # query_conditions.append({
            #     "conditionType": "EqualTo",
            #     "fieldName": "naturalbase_deleted",
            #     "value": False
            # })
            
            # 如果指定了分类，添加分类过滤
            if category and category != 'all':
                query_conditions.append({
                    "conditionType": "EqualTo",
                    "fieldName": "category",
                    "value": category
                })
            
            # 如果指定了 limit，添加 Limit 条件；否则使用一个很大的值来获取所有数据
            if limit is not None and limit > 0:
                query_conditions.append({
                    "conditionType": "Limit",
                    "value": {
                        "number": limit,
                        "offset": 0
                    }
                })
            else:
                # 如果未指定 limit，使用一个很大的值来获取所有数据
                query_conditions.append({
                    "conditionType": "Limit",
                    "value": {
                        "number": 10000,  # 足够大的值，应该能覆盖所有播客
                        "offset": 0
                    }
                })
            
            # 添加排序（注意：CloudDB的排序可能需要通过其他方式实现）
            # 这里先不实现排序，因为文档中没有明确说明排序的格式
            
            payload = {
                "msgInfo": {
                    "type": 5,  # 查询操作
                    "opStore": {
                        "storeName": self.cloud_db_zone
                    }
                },
                "clientInfo": {
                    "appVer": 1
                },
                "queryReqMsg": {
                    "queryType": 0,
                    "queryTable": self.object_type,
                    "queryCond": json.dumps({"queryConditions": query_conditions})
                }
            }
            
            logger.debug(f"查询播客列表，查询条件: {json.dumps(query_conditions, ensure_ascii=False, indent=2)}")
            logger.debug(f"查询请求URL: {url}")
            logger.debug(f"查询请求Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            
            result = resp.json()
            logger.debug(f"查询响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 检查响应状态
            ret_code = result.get('ret', {}).get('code')
            if ret_code == 0 or ret_code is None:  # 成功时 code 可能为 0 或不存在
                # 根据文档，数据在 opData 中
                op_data_list = result.get('opData', [])
                podcasts = []
                
                logger.debug(f"opData 列表长度: {len(op_data_list)}")
                
                # 遍历 opData 中的每个 OperatorData
                for idx, op_data in enumerate(op_data_list):
                    logger.debug(f"处理 opData[{idx}]: {json.dumps(op_data, ensure_ascii=False, indent=2)}")
                    # 获取对象列表 os
                    objects = op_data.get('os', [])
                    logger.debug(f"  对象数量: {len(objects)}")
                    for obj_idx, obj in enumerate(objects):
                        logger.debug(f"  处理对象[{obj_idx}]: {json.dumps(obj, ensure_ascii=False, indent=2)}")
                        podcast = self._convert_from_clouddb_format(obj)
                        if podcast:
                            # 在内存中过滤：只保留未删除的记录
                            # 检查 naturalbase_deleted 字段（索引13）
                            fs = obj.get('fs', [])
                            is_deleted = False
                            if len(fs) > 13:
                                is_deleted = fs[13].get('bl', False)
                            elif len(fs) == 13:
                                is_deleted = fs[12].get('bl', False)  # 如果只有13个字段，naturalbase_deleted在索引12
                            
                            if not is_deleted:
                                logger.debug(f"  转换后的播客数据: {json.dumps(podcast, ensure_ascii=False, indent=2)}")
                                podcasts.append(podcast)
                            else:
                                logger.debug(f"  跳过已删除的播客: {podcast.get('id')}")
                        else:
                            logger.warning(f"  对象转换失败，原始数据: {json.dumps(obj, ensure_ascii=False, indent=2)}")
                
                # 在内存中排序（如果CloudDB不支持排序）
                if order_by == "created_at":
                    podcasts.sort(key=lambda x: x.get('created_at', 0), reverse=(order == "desc"))
                
                logger.info(f"从云数据库获取到 {len(podcasts)} 个播客")
                return podcasts
            else:
                error_msg = result.get('ret', {}).get('msg', '未知错误')
                logger.error(f"查询失败，错误码: {ret_code}, 错误信息: {error_msg}")
                logger.error(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return []
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg or "auth failed" in error_msg:
                logger.error(
                    f"从云数据库获取播客列表时认证失败: {e}\n"
                    "可能的原因：\n"
                    "1. CloudDB REST API 需要使用服务端 API Key，而不是 OAuth Token\n"
                    "2. 请在 AGC 控制台创建服务端 API Key，并设置环境变量 AGC_API_KEY\n"
                    "3. 或者检查 OAuth client_id 是否有 CloudDB 访问权限"
                )
            else:
                logger.error(f"从云数据库获取播客列表时出错: {e}")
            return []
    
    def delete_podcast(self, podcast_id: str) -> bool:
        """
        从云数据库删除播客数据
        
        Args:
            podcast_id: 播客ID
        
        Returns:
            是否删除成功
        """
        token = self._get_access_token()
        if not token:
            logger.error("无法获取access token，跳过云数据库操作")
            return False
        
        try:
            # 构造删除请求（使用upsert，设置naturalbase_deleted为true）
            url = f"{self.base_url}/upsert?_v=4"
            
            # 如果使用 API Key，在 headers 中使用 API Key
            if self.api_key:
                headers = {
                    "content-type": "application/json",
                    "client_id": self.api_key,  # 使用 API Key 作为 client_id
                    "productId": self.product_id,
                    "host": self.domain
                }
            else:
                # 根据官方文档，需要同时使用 Authorization: Bearer 和 access_token
                # Authorization: Bearer 是必须的（客户端token）
                # access_token 是可选的（用户登录token，匿名账号可以为空）
                headers = {
                    "content-type": "application/json",
                    "client_id": self.client_id,
                    "Authorization": f"Bearer {token}",
                    "productId": self.product_id,
                    "access_token": "",  # 匿名账号，设置为空字符串
                    "host": self.domain
                }
            
            # 删除操作：只需要主键和删除标记字段
            delete_schema = {
                "n": self.object_type,
                "fs": [
                    {"n": "id", "t": "TYPE_STRING"},
                    {"n": "naturalbase_version", "t": "TYPE_LONG"},
                    {"n": "naturalbase_deleted", "t": "TYPE_BOOLEAN"}
                ]
            }
            
            payload = {
                "msgInfo": {
                    "type": 3,  # upsert操作
                    "opStore": {
                        "storeName": self.cloud_db_zone
                    }
                },
                "clientInfo": {
                    "appVer": 1
                },
                "schemas": [delete_schema],
                "opData": [
                    {
                        "i": 0,  # 对象索引
                        "os": [
                            {
                                "fs": [
                                    {"s": podcast_id},  # id
                                    {"l": None},  # naturalbase_version
                                    {"bl": True}  # naturalbase_deleted = true (删除标记)
                                ],
                                "i": 0
                            }
                        ],
                        "t": 1  # 对象类型索引
                    }
                ]
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            
            result = resp.json()
            if result.get('ret', {}).get('code') == 0:
                logger.info(f"播客数据已从云数据库删除: {podcast_id}")
                return True
            else:
                logger.warning(f"从云数据库删除播客数据失败: {result.get('ret', {}).get('msg', '未知错误')}")
                return False
        except Exception as e:
            logger.error(f"从云数据库删除播客数据时出错: {e}", exc_info=True)
            return False


def get_database_client() -> Optional[AGCDatabaseClient]:
    """
    获取AGC云数据库客户端实例
    
    Returns:
        AGCDatabaseClient实例，如果配置不完整则返回None
    """
    try:
        client = AGCDatabaseClient()
        
        # 检查必要的配置
        # 优先检查 API Key，如果没有则检查 OAuth 凭证
        if not client.api_key:
            if not client.client_id or not client.client_secret or not client.product_id:
                logger.debug(
                    "AGC云数据库配置不完整，跳过云数据库功能。\n"
                    "请配置以下之一：\n"
                    "  1. 环境变量 AGC_API_KEY（推荐，用于服务端 API Key）\n"
                    "  2. 环境变量 AGC_CLIENT_ID, AGC_CLIENT_SECRET, AGC_PRODUCT_ID（OAuth认证）\n"
                    "注意：CloudDB REST API 推荐使用服务端 API Key"
                )
                return None
        
        return client
    except Exception as e:
        logger.warning(f"初始化AGC云数据库客户端失败: {e}")
        return None
