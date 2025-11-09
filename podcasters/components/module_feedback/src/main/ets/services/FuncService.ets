import { MockData } from './mockdata/MockData'
import { SubmitFeedbackParams } from './RequestModel'
import { FeedbackResponseParams } from './ResponseModel';

export class FuncService {
  /**
   * 新增提交反馈
   * @param params
   */
  public addFeedback(params: SubmitFeedbackParams): Promise<void> {
    return new Promise((resolve) => {
      const item: FeedbackResponseParams = {
        id: Date.now().toString(),
        createTime: Date.now(),
        problemDesc: params.problemDesc,
        screenShots: params.screenShots,
        contactPhone: params.contactPhone,
      }
      MockData.list.splice(0, 0, item);
      setTimeout(() => {
        resolve();
      }, 500);
    });
  }

  /**
   * 查询反馈记录列表
   * @returns
   */
  public queryFeedbackList(): Promise<FeedbackResponseParams[]> {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(MockData.list);
      }, 500);
    });
  }
}

const instance: FuncService = new FuncService()

export { instance as FeedbackService }