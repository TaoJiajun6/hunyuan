import { cloudCommon } from '@kit.CloudFoundationKit';
import { http } from '@kit.NetworkKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { BusinessError } from '@kit.BasicServicesKit';
import auth from '@hw-agconnect/auth';

let accessToken = '';

/**
 * 自定义AuthProvider
 * 使用华为账号服务的获取用户级凭证接口获取refresh_token，然后基于refresh_token换取access_token
 */
export class MyAuthProvider implements cloudCommon.AuthProvider {
  async getAccessToken(isForceRefresh: boolean): Promise<string> {
    let data =
      "grant_type=refresh_token&client_id=xxxx&client_secret=xxxx&refresh_token=";
    let refreshToken =
      encodeURIComponent('xxxx'); // xxxx为使用华为账号服务获取用户级凭证接口获取的refresh_token

    // access_token过期则强制刷新
    if (isForceRefresh) {
      data = data + refreshToken;
      try {
        let httpRequest = http.createHttp();
        let ohosOptions: http.HttpRequestOptions = {
          method: http.RequestMethod.POST,
          header: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          extraData: data,
        };
        let url = "https://oauth-login.cloud.huawei.com/oauth2/v3/token";
        let resp = await httpRequest.request(url, ohosOptions);
        accessToken = JSON.parse(resp.result.toString()).access_token;
      } catch (err) {
        hilog.error(0x0000, 'testTag', `Failed to get accessToken, code: ${err.code}, message: ${err.message}`);
      }
    }

    return Promise.resolve(accessToken);
  }
}

/**
 * 认证服务类
 * 提供云存储初始化功能
 */
export class AuthService {
  private static isInitialized: boolean = false;
  private static initPromise: Promise<boolean> | null = null;



  /**
   * 登出用户
   */
  static async signOut(): Promise<void> {
    try {
      await auth.signOut();
      AuthService.isInitialized = false;
      AuthService.initPromise = null;
      hilog.info(0x0000, 'AuthService', '用户已登出');
    } catch (error) {
      const err = error as BusinessError;
      hilog.error(0x0000, 'AuthService', `登出失败: code=${err.code}, message=${err.message}`);
    }
  }
}

