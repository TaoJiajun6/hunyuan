import { AbilityConstant, UIAbility, Want, Configuration } from '@kit.AbilityKit';
import { window, KeyboardAvoidMode } from '@kit.ArkUI';
import { deviceInfo } from '@kit.BasicServicesKit';
import { BundleUtils, Logger } from 'lib_common';
import { NetworkUtils } from '../common/NetworkUtils';
import { WindowUtils } from '../common/WindowUtils';
import { AppUtils } from '../common/AppUtils';
import { GlobalContext } from '../common/GlobalContext';
import { cloudDatabaseService } from 'lib_api';
const TAG = '[EntryAbility]';

export default class EntryAbility extends UIAbility {
  // 标记是否需要执行windowStage.loadContent
  private needLoadContent: boolean = false;

  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam) {
    Logger.info(TAG, 'Ability onCreate');
    GlobalContext.initContext(this.context);
    // 将context存储到AppStorage，供其他模块使用
    AppStorage.setOrCreate('context', this.context);
    // 初始化云数据库服务
    try {
      cloudDatabaseService.initialize();
      Logger.info(TAG, '云数据库服务初始化完成');
    } catch (error) {
      Logger.error(TAG, `云数据库服务初始化失败: ${JSON.stringify(error)}`);
    }
    this.setNeedLoadContent(true);
  }

  onNewWant(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    Logger.info(TAG, 'Ability onNewWant');
    this.setNeedLoadContent(false);
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    Logger.info(TAG, 'Ability onWindowStageCreate');
    this.handleWindowStageCreateOrRestore(windowStage);
  }

  onWindowStageRestore(windowStage: window.WindowStage): void {
    Logger.info(TAG, 'Ability onWindowStageRestore');
    if (this.needLoadContent) {
      this.handleWindowStageCreateOrRestore(windowStage);
    }
  }

  onConfigurationUpdate(newConfig: Configuration): void {
    AppUtils.listenConfigurationUpdate(newConfig);
  }

  onWindowStageDestroy(): void {
    Logger.info(TAG, 'Ability onWindowStageDestroy');
  }

  onDestroy(): void {
    Logger.info(TAG, 'Ability onDestroy');
    WindowUtils.offAvoidAreaChange();
    NetworkUtils.unRegisterNetwork();
  }

  handleWindowStageCreateOrRestore(windowStage: window.WindowStage) {
    WindowUtils.setWinConfig(windowStage);
    windowStage.loadContent('pages/Index', (err) => {
      if (err.code) {
        Logger.error(TAG, 'Failed to load the content. Cause: ' + JSON.stringify(err));
        return;
      }
      Logger.info(TAG, 'Succeeded in loading the content.');
      windowStage.getMainWindowSync().getUIContext().setKeyboardAvoidMode(KeyboardAvoidMode.RESIZE);

      AppUtils.setAppTheme();
      AppUtils.setColorMode();
      BundleUtils.getBundleInfo();
      // 判断是否是模拟器
      let productMode = deviceInfo.productModel;
      if (productMode !== 'emulator') {
        NetworkUtils.initNetwork();
      }
    });
  }

  setNeedLoadContent(value: boolean) {
    this.needLoadContent = value;
  }
};
