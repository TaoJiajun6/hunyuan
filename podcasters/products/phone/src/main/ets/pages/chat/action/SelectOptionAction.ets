import { ActionWaitRenderProps, FrontendAction } from '@hw-agconnect/copilot';

export const selectOptionAction: FrontendAction = {
  name: 'select_option_card',
  description: '展示选项卡片并等待用户选择（最多四个选项）',
  available: 'enabled',
  parameters: [
    {
      name: 'title',
      type: 'string',
      description: '卡片标题',
      required: true,
    },
    {
      name: 'options',
      type: 'object[]',
      description: '选项列表（每项包含label与value），最多四个',
      required: true,
      attributes: [
        {
          name: 'label',
          type: 'string',
          description: '选项展示文本',
          required: true,
        },
        {
          name: 'value',
          type: 'string',
          description: '选项值',
          required: true,
        },
        {
          name: 'id',
          type: 'string',
          description: '选项唯一标识（可选）',
          required: false,
        },
      ]
    },
  ],
  renderAndWaitForResponse: wrapBuilder(selectOptionWaitCard)
};

// ---------- 选项卡片 Action ----------
interface SelectOptionItem {
  id?: string
  label: string
  value: string
}

interface SelectOptionArgs {
  title?: string
  options: SelectOptionItem[]
}

@Builder
function selectOptionWaitCard(props: ActionWaitRenderProps) {
  if (props.status !== 'inProgress') {
    SelectOptionWaitCard({
      props: props
    })
  }
}

@ComponentV2
struct SelectOptionWaitCard {
  @Param @Require props: ActionWaitRenderProps;
  @Local selectedItem?: SelectOptionItem;
  @Local isConfirm: boolean = false;

  build() {
    Column({ space: 8 }) {
      if (this.props.args?.title) {
        Text(this.props.args.title)
          .fontSize($r('sys.float.Title_M'))
          .fontColor($r('sys.color.font_primary'))
          .margin({ bottom: 8 })
      }

      if (this.isConfirm && this.selectedItem) {
        this.checkItemBuilder(this.selectedItem)
      } else {
        ForEach(this.props.args?.options, (item: SelectOptionItem) => {
          this.checkItemBuilder(item);
        }, (item: SelectOptionItem): string => item.label)

        Button('确定')
          .enabled(this.selectedItem !== undefined)
          .onClick(() => {
            this.props.respond(`用户选择了${this.selectedItem?.label},值为:${this.selectedItem?.value}`);
            this.isConfirm = true;
          })
      }
    }
    .alignItems(HorizontalAlign.Start)
    .width('100%')
    .borderRadius(8)
    .padding(12)
    .backgroundColor('#ffe1fffb')
  }

  @Builder
  checkItemBuilder(item: SelectOptionItem) {
    Row() {
      Radio({
        value: item.label,
        group: 'select_radio_group'
      }).onChange((isChecked) => {
        if (isChecked) {
          this.selectedItem = item;
        }
      })
        .checked(this.selectedItem === item)
      Text(item.label)
        .fontSize($r('sys.float.Body_M'))
        .fontColor($r('sys.color.font_primary'))
        .padding(8)
    }.onClick(() => {
      this.selectedItem = item;
    })
  }
}