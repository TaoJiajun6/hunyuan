import { bundleManager } from '@kit.AbilityKit';
import { BundleInfo } from '../models/BundleInfo';

export class BundleUtils {
  public static async getBundleInfo() {
    const bundleInfo =
      await bundleManager.getBundleInfoForSelf(bundleManager.BundleFlag.GET_BUNDLE_INFO_WITH_APPLICATION);
    let appName = getContext().resourceManager.getStringSync(bundleInfo.appInfo.labelId);
    let appVersionName = bundleInfo.versionName;
    let appInfo: BundleInfo = {
      appName,
      appVersionName,
    }
    AppStorage.setOrCreate('appInfo', appInfo)
  }
}