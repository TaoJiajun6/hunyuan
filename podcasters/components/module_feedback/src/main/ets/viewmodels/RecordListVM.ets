import { AppStorageV2 } from '@kit.ArkUI';
import { FeedbackModel } from '../common/FeedbackModel';
import { FeedbackService } from '../services/FuncService';
import { FeedbackResponseParams } from '../services/ResponseModel';

@ObservedV2
export class RecordListVM {
  @Trace feedbackModel: FeedbackModel = AppStorageV2.connect(FeedbackModel, () => new FeedbackModel())!;
  @Trace list: FeedbackResponseParams[] = [];
  @Trace loading: boolean = false;
  @Trace gridCount: number = 3;
  @Trace breakpoint: string = 'sm';

  constructor() {
    this.queryListInfo();
  }

  queryListInfo() {
    this.loading = true;
    FeedbackService.queryFeedbackList().then((resp) => {
      this.list = resp;
    }).finally(() => {
      this.loading = false;
    });
  }

  onBreakpointChange(bp: string) {
    this.breakpoint = bp;
    if (bp === 'sm') {
      this.gridCount = 3;
    } else if (bp === 'md') {
      this.gridCount = 6;
    } else {
      this.gridCount = 8;
    }
  }
}
