import { RouterUtils } from 'lib_common'
import { IndexVM } from '../viewmodels/IndexVM';

@Entry
@ComponentV2
struct Index {
  vm: IndexVM = new IndexVM();
  @Local isEnabled: boolean = true;
  aboutToAppear(): void {
    this.vm.setInterception();
    this.vm.redirect();
    this.vm.navDestinationListener()
    this.vm.windowStageEventListener()
    this.vm.registerBreakpointListener(this.getUIContext());
    this.vm.displayOrientationListener()
  }

  aboutToDisappear(): void {
    this.vm.unregisterBreakpointListener();
  }

  build() {
    Navigation(RouterUtils.getStack()) {
    }
    .hideNavBar(true)
    .enabled(this.isEnabled)
    .hideTitleBar(true)
    .mode(NavigationMode.Stack)
    .onNavBarStateChange(()=>{
      this.vm.redirect();
    })
  }
}