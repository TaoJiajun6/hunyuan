
// 创作者接口
export { AuthorServiceApi } from './src/main/ets/services/AuthorService'

// 我的接口
export { MineServiceApi } from './src/main/ets/services/MineService'

// 基础类型
export { NavInfo, PostImgList, } from './src/main/ets/params/base/BaseModel';

// 请求参数
export {
  ModifyPersonalInfoRequest,
} from './src/main/ets/params/request/CommonRequest';

// 作者响应模型
export { AuthorResponse } from './src/main/ets/params/response/AuthorResponse'

// 播客服务
export {
  podcastService,
  PodcastService,
  PodcastConfig,
  CharacterInfo,
  MultiRoleRequest,
  CharacterRequest,
  DeepPodcastRequest,
  ApiResponse,
  PodcastResult
} from './src/main/ets/services/PodcastService'