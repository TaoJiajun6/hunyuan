import { media } from '@kit.MediaKit';
import { photoAccessHelper } from '@kit.MediaLibraryKit';

export interface MediaParams {
  type: photoAccessHelper.PhotoViewMIMETypes
  maxLimit: number
  maxSize?: number
}

export class VideoSizeData {
  public photoSize: media.PixelMapParams = {
    width: 0,
    height: 0,
  };
  public totalTime: number = 0;
}

@ObservedV2
export class CoverUri {
  id:string = ''
  @Trace uri:string = ''
}