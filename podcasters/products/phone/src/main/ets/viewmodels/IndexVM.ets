import { display, uiObserver, window } from '@kit.ArkUI';
import { BaseViewModel, BreakpointUtils, Logger, PreferenceUtils, RouterMap, RouterUtils } from 'lib_common';
import { LoginSheetUtils } from 'lib_account';
import { agreePrivacyKey, REQUIRE_LOGIN_PAGE_LIST } from '../common/Constants';

const TAG = 'IndexVM';

@ObservedV2
export class IndexVM extends BaseViewModel {
  // todo: 自行调整是否支持开屏广告
  @Trace isShowAd: boolean = false;
  breakpoint: BreakpointUtils | null = null;

  redirect() {
    if (this.isAgreePrivacy()) {
      const targetPage = this.isShowAd ? RouterMap.SPLASH_PAGE : RouterMap.INDEX_PAGE;
      RouterUtils.replacePathByName(targetPage);
    } else {
      RouterUtils.replacePathByName(RouterMap.SAFE_PAGE);
    }
  }

  isAgreePrivacy() {
    return PreferenceUtils.getInstance().get(agreePrivacyKey) as boolean;
  }

  setInterception() {
    RouterUtils.getStack().setInterception({
      willShow: (from: NavDestinationContext | NavBar, to: NavDestinationContext | NavBar,
        operation: NavigationOperation, animated: boolean) => {
        if (typeof to === 'string') {
          Logger.info(TAG, 'target page is navigation home page.');
          return;
        }
        let target: NavDestinationContext = to as NavDestinationContext;

        // 拦截依赖登录的页面
        if (!this.userInfoModel.isLogin && REQUIRE_LOGIN_PAGE_LIST.includes(target?.pathInfo?.name as RouterMap)) {
          target.pathStack.pop();
          LoginSheetUtils.open();
        }
      },
    })
  }

  registerBreakpointListener(context: UIContext) {
    this.breakpoint = new BreakpointUtils(context.getMediaQuery());
    this.breakpoint?.register();
  }

  unregisterBreakpointListener() {
    this.breakpoint?.unRegister();
  }

  // 监听NavDestination组件的状态变化
  navDestinationListener() {
    // 无感监听路由变化
    uiObserver.on('navDestinationUpdate', (info: uiObserver.NavDestinationInfo) => {
      this.navRouteModel.navDestinationUpdateListeners.forEach((callback) => {
        callback(info)
      })
    })
  }

  // 监听WindowStage生命周期变化
  windowStageEventListener() {
    let windowStage = AppStorage.get('windowStage') as window.WindowStage;
    windowStage.on('windowStageEvent', (type: window.WindowStageEventType) => {
      this.windowStageModel.windowStageEventListeners.forEach((callback) => {
        callback(type)
      })
    });
  }

  // 监听设备屏幕方向改变
  displayOrientationListener() {
    this.displayModel.isFoldable = display.isFoldable();
    display.on('change', (type: number) => {
      let displayClass = display.getDisplayByIdSync(type);
      // 横屏
      let landscapeType = [display.Orientation.LANDSCAPE, display.Orientation.LANDSCAPE_INVERTED]
      this.displayModel.isLandscape = landscapeType.includes(displayClass.orientation);
    })
  }
}
