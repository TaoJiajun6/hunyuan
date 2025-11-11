import { Logger } from '@hw-agconnect/hmcore';
import { authentication } from '@kit.AccountKit';
import { util } from '@kit.ArkTS';
import auth from '@hw-agconnect/auth';

// 定义 AuthUser 接口
interface AuthUser {
  getUid(): string;

  getDisplayName(): string;

  getPhotoUrl(): string;
}

export class HuaweiAuth {
  // 检查华为账号登录状态
  static async checkHuaweiLoginStatus(): Promise<boolean> {
    try {
      const user = await auth.getCurrentUser();
      return user !== null;
    } catch (error) {
      console.error('检查华为账号登录状态失败:', error);
      return false;
    }
  }

  // 获取当前华为账号用户信息
  static async getCurrentHuaweiUser(): Promise<AuthUser | null> {
    try {
      const user = await auth.getCurrentUser();
      return user;
    } catch (error) {
      console.error('获取华为账号用户信息失败:', error);
      return null;
    }
  }

  // 统一的登录状态检查方法
  static async checkLoginStatus(): Promise<boolean> {
    try {
      const user = await auth.getCurrentUser();
      if (user) {
        // 如果用户已登录，确保用户信息被正确存储
        AppStorage.setOrCreate('user', user);
        AppStorage.setOrCreate('isLoggedIn', true);
        AppStorage.setOrCreate('userUid', user.getUid());
        AppStorage.setOrCreate('userDisplayName', user.getDisplayName());
        AppStorage.setOrCreate('userPhotoUrl', user.getPhotoUrl());

        console.log('HuaweiAuth: 登录状态检查成功，用户信息已更新');
        return true;
      }

      // 用户未登录，重置状态
      AppStorage.setOrCreate('isLoggedIn', false);
      AppStorage.setOrCreate('user', null);
      console.log('HuaweiAuth: 用户未登录，状态已重置');
      return false;
    } catch (error) {
      console.error('HuaweiAuth: 检查登录状态失败:', error);
      // 出错时重置状态
      AppStorage.setOrCreate('isLoggedIn', false);
      AppStorage.setOrCreate('user', null);
      return false;
    }
  }

  // 华为登录，返回 Promise
  static async authRequest(uiContext: UIContext): Promise<authentication.AuthorizationWithHuaweiIDCredential> {
    try {
      console.log('HuaweiAuth: 开始华为账号授权请求...');

      // 1.创建授权请求，并设置参数
      const authRequest = new authentication.HuaweiIDProvider().createAuthorizationWithHuaweiIDRequest();
      // 获取头像昵称需要传如下scope
      authRequest.scopes = ['profile'];
      // 若开发者需要进行服务端开发以获取头像昵称，则需传如下permission获取authorizationCode
      authRequest.permissions = ['serviceauthcode'];
      // 用户是否需要登录授权，该值为true且用户未登录或未授权时，会拉起用户登录或授权页面
      authRequest.forceAuthorization = true;
      // 用于防跨站点请求伪造
      authRequest.state = util.generateRandomUUID();

      console.log('HuaweiAuth: 授权请求参数设置完成');

      // 2.执行授权请求
      const controller = new authentication.AuthenticationController(uiContext.getHostContext());
      const authResponse: authentication.AuthorizationWithHuaweiIDResponse = await controller.executeRequest(authRequest)
      const avatarUri = authResponse.data?.avatarUri;
      const nickName = authResponse.data?.nickName;
      return { avatarUri, nickName }
    } catch (e) {
      console.error('HuaweiAuth: 授权请求失败:', e);
      Logger.info(e, "error")
      if (e instanceof Error) {
        throw e;
      } else {
        throw new Error(String(e));
      }
    }
  }

  static async cancelAuth(uiContext: UIContext): Promise<boolean> {
    try {
      //1.创建一个Account Kit授权请求对象,通过返回值设置请求参数
      const huaweiIdProvider = new authentication.HuaweiIDProvider()
      const authCancelRequest = huaweiIdProvider.createCancelAuthorizationRequest()
      //2.取消授权
      const authController = new authentication.AuthenticationController(uiContext.getHostContext())
      await authController.executeRequest(authCancelRequest)
      return true
    } catch (e) {
      console.log('logger', JSON.stringify(e))
    }
    return false
  }
}

