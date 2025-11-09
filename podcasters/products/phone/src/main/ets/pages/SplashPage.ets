import { CommonConstants, RouterMap, RouterUtils } from 'lib_common';

@Builder
export function SplashPageBuilder() {
  SplashPage()
}

@ComponentV2
struct SplashPage {
  build() {
    Column() {
    }
    .height(CommonConstants.FULL_PERCENT)
    .width(CommonConstants.FULL_PERCENT)
  }
}