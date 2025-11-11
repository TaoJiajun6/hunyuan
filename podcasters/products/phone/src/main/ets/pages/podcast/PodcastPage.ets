import { RouterMap, RouterUtils } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';

@Builder
export function PodcastPageBuilder() {
  PodcastPage()
}

@ComponentV2
export struct PodcastPage {
  build() {
    NavDestination() {
      Column() {
        NavHeaderBar({
          title: 'AI播客',
          isSubTitle: false,
          showBackBtn: false
        })

        Scroll() {
          Column({ space: 16 }) {
            // 多角色互动播客
            Row() {
              Column({ space: 8 }) {
                Text('多角色互动播客')
                  .fontSize($r('sys.float.Title_M'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)

                Text('将文本素材转化为多角色自然互动的播客音频')
                  .fontSize($r('sys.float.Body_M'))
                  .fontColor($r('sys.color.font_secondary'))
                  .maxLines(2)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
              }
              .alignItems(HorizontalAlign.Start)
              .layoutWeight(1)
            }
            .width('100%')
            .padding(16)
            .borderRadius(12)
            .backgroundColor($r('sys.color.comp_background_tertiary'))
            .onClick(() => {
              RouterUtils.pushPathByName(RouterMap.PODCAST_MULTI_ROLE_PAGE)
            })

            // 自定义角色播客
            Row() {
              Column({ space: 8 }) {
                Text('自定义角色播客')
                  .fontSize($r('sys.float.Title_M'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)

                Text('根据用户自定义的角色人设和音色生成契合风格的播客音频')
                  .fontSize($r('sys.float.Body_M'))
                  .fontColor($r('sys.color.font_secondary'))
                  .maxLines(2)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
              }
              .alignItems(HorizontalAlign.Start)
              .layoutWeight(1)
            }
            .width('100%')
            .padding(16)
            .borderRadius(12)
            .backgroundColor($r('sys.color.comp_background_tertiary'))
            .onClick(() => {
              RouterUtils.pushPathByName(RouterMap.PODCAST_CHARACTER_PAGE)
            })

            // 主题深度播客
            Row() {
              Column({ space: 8 }) {
                Text('主题深度播客')
                  .fontSize($r('sys.float.Title_M'))
                  .fontColor($r('sys.color.font_primary'))
                  .fontWeight(FontWeight.Bold)

                Text('基于指定主题生成有深度、引发思考的播客音频')
                  .fontSize($r('sys.float.Body_M'))
                  .fontColor($r('sys.color.font_secondary'))
                  .maxLines(2)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
              }
              .alignItems(HorizontalAlign.Start)
              .layoutWeight(1)
            }
            .width('100%')
            .padding(16)
            .borderRadius(12)
            .backgroundColor($r('sys.color.comp_background_tertiary'))
            .onClick(() => {
              RouterUtils.pushPathByName(RouterMap.PODCAST_DEEP_PAGE)
            })
          }
          .width('100%')
          .padding({ left: 16, right: 16, top: 16, bottom: 16 })
        }
        .layoutWeight(1)
      }
      .width('100%')
      .height('100%')
      .backgroundColor($r('sys.color.background_primary'))
    }
    .hideTitleBar(true)
  }
}









