import { ActionRenderProps, FrontendAction } from '@hw-agconnect/copilot'

export const weatherAction : FrontendAction = {
  name: 'get_weather',
  description: 'Get the weather for a given location.',
  available: 'enabled',
  parameters: [{
    name: 'location',
    type: 'string',
    description: '城市名称',
    required: true,
  }],
  handler: async (args) => {
    console.log('handle action : ' + args.location)
    return `{\'temperature\': \'15\', \'unit\': \'celsius\', \'description\': \'晴朗\'}`;
  },
  // render: wrapBuilder(weatherWaitCard)
}

@Builder
function weatherWaitCard(props: ActionRenderProps) {
  if (props.status === 'complete') {
    Column() {
      Text(props.args.location)
        .backgroundColor($r('sys.color.background_primary'))
        .width('100%')
      Text(props.result)
        .backgroundColor($r('sys.color.background_secondary'))
        .width('100%')
    }
  }
}