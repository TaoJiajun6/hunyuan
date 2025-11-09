import { CopilotChat, CopilotController } from '@hw-agconnect/copilot';
import { markConfig, MarkdownV2 } from '@lidary/markdown';
import { RouterMap, RouterUtils } from 'lib_common';
import { NavHeaderBar } from 'lib_widget';
import { HistoryButton } from '../../components/HistoryButton';
import { selectOptionAction } from './action/SelectOptionAction';
import { weatherAction } from './action/WeatherAction';

@ComponentV2
export struct ChatPage {
  controller: CopilotController = new CopilotController({
    llm: {
      baseUrl: 'https://api.deepseek.com/v1',
      //TODO: 需要替换成真实的apikey，为了安全起见，建议配置在服务端，可以动态下发
      apiKey: '',
      model: 'deepseek-chat'
    },
    storeId: 'Chat',
    systemPrompt: '你是一个AI办公写作助手，可以帮助用户解决写作类的问题'
  });

  aboutToAppear(): void {
    // this.controller.registerAction(weatherAction)
    // this.controller.registerAction(selectOptionAction)

    markConfig.registerLinkClick = (url? : string) => {
      this.getUIContext().getPromptAction().showToast({
        message: `超链接被点击----url:${url}`,
        duration: 1500,
        bottom: 'center',
      })
    }
  }

  build() {
    Column() {
      NavHeaderBar({
        title: '智能对话',
        isSubTitle: false,
        showBackBtn: false,
        rightPartBuilder: () => {
          this.menusBuilder()
        }
      }).expandSafeArea([SafeAreaType.KEYBOARD])

      CopilotChat({
        controller: this.controller,
        options: {
          labels: {
            introduce: '嗨！我是AI办公写作助手',
            initial: '你好，我是你的智能助手，有什么需要帮助的',
            suggestions: [
              '北京的天气怎么样',
              '给我几个城市选项',
              '如何生成一篇800字的作文',
              '如何生成一篇800字的作文',
            ],
            placeholder: '请输入你的问题'
          },
          icons: {
            assistant: $r('app.media.icon_flip_foreground')
          },
          isShowDefaultActionCard: true
        },
        markdownRender: (content: string) => {
          this.markdownRender(content)
        }
      }).layoutWeight(1)
    }
    .justifyContent(FlexAlign.SpaceBetween)
    .width('100%')
    .height('100%')
  }

  @Builder
  markdownRender(content: string) {
    MarkdownV2({
      content: content,
      lineSpace: 4,
      fontStyle: {
        fontSize: $r('sys.float.Body_M'),
        fontColor: $r('sys.color.font_primary')
      }
    })
  }

  @Builder
  menusBuilder() {
    Row({ space: 16 }) {
      SymbolGlyph($r('sys.symbol.message_badge_plus_fill'))
        .fontSize($r('sys.float.Title_M'))
        .fontColor([$r('sys.color.icon_primary')])
        .padding(8)
        .borderRadius(40)
        .backgroundColor($r('sys.color.comp_background_tertiary'))
        .onClick(() => {
          this.controller.reset();
        })
      HistoryButton({
        onEvent: () => {
          RouterUtils.pushPathByName(RouterMap.CHAT_HISTORY_PAGE, null, (popInfo) => {
            let threadId = popInfo.result.toString()
            if (this.controller.context.threadId !== threadId) {
              this.controller.reload(threadId);
            }
          })
        }
      })
    }
  }
}