import auth from '@hw-agconnect/auth';
import { promptAction, router } from '@kit.ArkUI';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { HuaweiAuth } from '../utils/HuaweiAuth';
import { AccountApi } from '../services/AccountApi';

@Builder
export function HuaweiLoginPageBuilder() {
  HuaweiLoginPage()
}
// 定义 SignInResult 接口
interface SignInResult {
  getUser(): AuthUser;
}

// 定义 AuthUser 接口 对象类型
interface AuthUser {
  getUid(): string;

  getDisplayName(): string;

  getPhotoUrl(): string;
}

interface HuaweiProfile {
  avatarUri?: string;
  nickName?: string;
}

interface LoginErrorInfo {
  code?: number | string;
  message: string;
}


@Component
export struct HuaweiLoginPage {
  //@Link isLoading: boolean
  private accountApi: AccountApi = new AccountApi();

  signInWithHuawei(huaweiProfile?: HuaweiProfile) {
    auth.signIn({
      autoCreateUser: true,
      "credentialInfo": {
        "kind": 'hwid'
      }
    }).then((signInResult: SignInResult) => {
      hilog.info(0x0000, 'testTag', '%{public}s', `signInHwid success. result: ${signInResult.getUser().getUid()}`);
      // 登录成功后的处理逻辑
      this.handleLoginSuccess(signInResult, huaweiProfile); // <--- 必须传递 huaweiProfile
    })
      .catch((error: BusinessError | Error ) => {
        const normalized = this.normalizeError(error);
        hilog.error(0x0000, 'testTag', '%{public}s',
          `signInHwid error, Code: ${normalized.code ?? 'UNKNOWN'}, message: ${normalized.message}`);
        // 登录失败后的处理逻辑
        this.handleLoginError(normalized);
      });
  }

  // 处理登录成功
  handleLoginSuccess(signInResult: SignInResult, huaweiProfile?: HuaweiProfile) {
    const user: AuthUser = signInResult.getUser();
    const uid: string = user.getUid();
    const displayName: string = user.getDisplayName();
    const userPhotoUrl: string = user.getPhotoUrl();

    // 保存用户信息到本地存储
    AppStorage.setOrCreate('userUid', uid);
    AppStorage.setOrCreate('userDisplayName', huaweiProfile?.nickName || displayName);
    AppStorage.setOrCreate('userPhotoUrl', huaweiProfile?.avatarUri || userPhotoUrl);
    AppStorage.setOrCreate('isLoggedIn', true);

    console.log('存储后的 userPhotoUrl:', AppStorage.get('userPhotoUrl'));

    const description = this.accountApi.getUserInfo().authorDesc || '华为账号用户';
    this.accountApi.huaweiLogin('', {
      uid,
      nickName: huaweiProfile?.nickName || displayName,
      avatarUri: huaweiProfile?.avatarUri || userPhotoUrl,
      phone: '--',
      description
    });

    // 跳转到主页面
    router.replaceUrl({ url: 'pages/Index' });
  }

  // 处理登录失败
  handleLoginError(error: LoginErrorInfo) {
    // 显示错误信息给用户
    AlertDialog.show({
      title: '登录失败',
      message: error.code !== undefined ? `错误代码: ${error.code}, 错误信息: ${error.message}` : `错误信息: ${error.message}`,
      confirm: {
        value: '确定',
        action: () => {
          // 用户确认后的处理
        }
      }
    });
  }

  private normalizeError(error: BusinessError | Error ): LoginErrorInfo {
    if (error && typeof error === 'object') {
      const maybeBusiness = error as BusinessError;
      const code = (maybeBusiness as BusinessError).code;
      const message = (maybeBusiness as BusinessError).message ?? (maybeBusiness as Error).message;
      if (message) {
        return { code, message };
      }
    }
    if (typeof error === 'string') {
      return { message: error };
    }
    return { message: '登录失败，请稍后重试' };
  }

  // 检查登录状态
  checkLoginStatus(): Promise<boolean> {
    return auth.getCurrentUser().then((user: AuthUser | null) => {
      return user !== null;
    }).catch((error: Error) => {
      return false;
    });
  }

  build() {
    NavDestination(){
      Column() {
        Stack() {
          Column() {
            Button() {
              Row() {
                // 华为Logo
                Image($r('app.media.ic_huawei'))
                  .width(30)
                  .height(30)

                Text('华为账号登录')
                  .fontSize(16)
                  .fontWeight(FontWeight.Medium)
                  .fontColor(Color.White)
                  .margin({ left: 10 })
              }
              .justifyContent(FlexAlign.Center)
              .alignItems(VerticalAlign.Center)
            }
            .width(320)
            .height(56)
            .backgroundColor('#CE0E2D')
            .borderRadius(28)
            .width(300)
            .height(50)
            .onClick(async () => {
              //this.isLoading = !this.isLoading
              // 1. 获取华为账号头像和昵称
              let huaweiProfile: HuaweiProfile | null = null
              try {
                huaweiProfile = await HuaweiAuth.authRequest(this.getUIContext()) as HuaweiProfile
                // this.isLoading = !this.isLoading
                console.log('huaweiProfile', JSON.stringify(huaweiProfile))
              } catch (e) {
                //this.isLoading = !this.isLoading
                promptAction.showToast({ message: '获取华为账号信息失败' })
                return
              }

              // 2. 云端登录
              this.signInWithHuawei(huaweiProfile)
              //this.isLoading = false

            })
          }.width('100%')

        }

      }
      .width('100%')
      .height('100%')
      //.backgroundColor('#F5F5F5')
    }

  }
}