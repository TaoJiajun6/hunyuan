/*
 * Copyright (c) 2024 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { image } from '@kit.ImageKit';
import { effectKit } from '@kit.ArkGraphics2D';
import { Logger } from './Logger';
import { http } from '@kit.NetworkKit';


const TAG = 'ImageUtils';

export class ImageDealData {
  imageColor: string = 'rgba(0, 0, 2, 1.00)';
  imageColorHex: string = '';
  blurPixelMap: PixelMap | undefined = undefined;
  blurPixelMapForCard: PixelMap | undefined = undefined;
}

/**
 * 颜色转换处理类。
 */
class ImageUtils {
  /**
   * Generate an immersive background color for the image.
   * @param rRGB
   * @param gRGB
   * @param bRGB
   * @returns
   */
  public dealColor(rRGB: number, gRGB: number, bRGB: number) {
    let max = Math.max(Math.max(rRGB, gRGB), bRGB);
    let min = Math.min(Math.min(rRGB, gRGB), bRGB);
    let sHSB = max === 0 ? 0 : (max - min) / max;
    let bHSB = max / 255;
    let hHSB = 0;
    if (max === rRGB && gRGB >= bRGB) {
      hHSB = 60 * (gRGB - bRGB) / (max - min) + 0;
    }
    if (max === rRGB && gRGB < bRGB) {
      hHSB = 60 * (gRGB - bRGB) / (max - min) + 360;
    }
    if (max === gRGB) {
      hHSB = 60 * (bRGB - rRGB) / (max - min) + 120;
    }
    if (max === bRGB) {
      hHSB = 60 * (rRGB - gRGB) / (max - min) + 240;
    }

    if (bHSB >= 0.4) {
      bHSB = 0.3;
    } else if (bHSB >= 0.2) {
      bHSB -= 0.1;
    } else {
      bHSB = bHSB + 0.2;
    }

    let i: number = Math.floor((hHSB / 60) % 6);
    let f = (hHSB / 60) - i;
    let p = bHSB * (1 - sHSB);
    let q = bHSB * (1 - f * sHSB);
    let t = bHSB * (1 - (1 - f) * sHSB);
    switch (i) {
      case 0:
        rRGB = bHSB;
        gRGB = t;
        bRGB = p;
        break;
      case 1:
        rRGB = q;
        gRGB = bHSB;
        bRGB = p;
        break;
      case 2:
        rRGB = p;
        gRGB = bHSB;
        bRGB = t;
        break;
      case 3:
        rRGB = p;
        gRGB = q;
        bRGB = bHSB;
        break;
      case 4:
        rRGB = t;
        gRGB = p;
        bRGB = bHSB;
        break;
      case 5:
        rRGB = bHSB;
        gRGB = p;
        bRGB = q;
        break;
      default:
        break;
    }
    return [Math.floor(rRGB * 255.0), Math.floor(gRGB * 255.0), Math.floor(bRGB * 255.0)];
  }

  public async getBlurPixelMap(pixelMap: PixelMap, blur: number): Promise<PixelMap> {
    let filter = effectKit.createEffect(pixelMap);
    filter.blur(blur);
    let blurPixelMap: PixelMap = await filter.getEffectPixelMap();
    return blurPixelMap;
  }

  public getImageDealData(context: Context, imgRes: Resource | string): Promise<ImageDealData> {
    return new Promise(async (resolve, reject) => {
      try {
        if (typeof imgRes === 'string' && imgRes.startsWith('http')) {
          // 根据网络歌曲地址创建图片PixelMap
          let buffer: ArrayBuffer = await this.geArrayBufferFromUrl(imgRes);
          let imageData = await this.getImageDealDataByArr(buffer)
          resolve(imageData);
        } else {
          let value = context.resourceManager.getMediaByNameSync(imgRes as string)
          let imageData = await this.getImageDealDataByArr(value.buffer as ArrayBuffer)

          resolve(imageData);
        }
      } catch (err) {
        Logger.info(TAG, `getImageDealData err :${JSON.stringify(err)}`)
        reject(err);
      }
    });
  }

  public async compressImage(sourcePixelMap: image.PixelMap, maxCompressedImageSize: number): Promise<PixelMap> {
    Logger.info(TAG, 'compressImage');
    let compressedImageData: ArrayBuffer = await this.packing(sourcePixelMap);
    if (compressedImageData.byteLength <= maxCompressedImageSize * 1024) {
      Logger.info(TAG, 'compressImage first');
      return sourcePixelMap;
    }
    let imageScale = 1;
    while (compressedImageData.byteLength > maxCompressedImageSize * 1024) {
      if (imageScale > 0) {
        imageScale = imageScale - 0.05;
        await sourcePixelMap.scale(imageScale, imageScale);
        compressedImageData = await this.packing(sourcePixelMap);
      } else {
        break;
      }
    }
    let afterCompressionSize = (compressedImageData.byteLength / 1024).toFixed(1);
    Logger.info(TAG, `compressImage afterCompressionSize:${afterCompressionSize}`);
    if (compressedImageData.byteLength > maxCompressedImageSize * 1024) {
      Logger.info(TAG, 'compress iamge failed');
    }
    return sourcePixelMap;
  }

  async packing(sourcePixelMap: image.PixelMap): Promise<ArrayBuffer> {
    const imagePackerApi = image.createImagePacker();
    const packOpts: image.PackingOption = { format: 'image/' + 'jpeg', quality: 100 };
    const data: ArrayBuffer = await imagePackerApi.packing(sourcePixelMap, packOpts);
    return data;
  }

  /**
   * 通过ArrayBuffer处理图片数据，提取图片主要颜色并生成模糊效果
   * @param buffer - 图片数据的ArrayBuffer
   * @returns Promise<ImageDealData> - 包含处理后图片数据的Promise对象
   */
  public getImageDealDataByArr(buffer: ArrayBuffer): Promise<ImageDealData> {
    return new Promise(async (resolve, reject) => {
      try {
        // 创建像素图并根据文件大小决定是否压缩
        let pixelMap = image.createImageSource(buffer).createPixelMapSync();
        if (buffer.byteLength > 2048 * 1024) {
          pixelMap = await this.compressImage(pixelMap, 2048);
        }

        // 提取图片主要颜色信息
        let imageData = new ImageDealData();
        let colorPicker = await effectKit.createColorPicker(pixelMap);
        let mainColor = colorPicker.getMainColorSync();
        let colorArr = this.dealColor(mainColor.red, mainColor.green, mainColor.blue);
        let imageColor = `rgba(${colorArr[0]}, ${colorArr[1]}, ${colorArr[2]}, 1)`;
        let imageColorHex = `${colorArr[0].toString(16)}${colorArr[1].toString(16)}${colorArr[2].toString(16)}`;
        Logger.info(TAG, `getImageDealDataByArr imageColor :${imageColor}`);
        Logger.info(TAG, `getImageDealDataByArr imageColorHex :${imageColorHex}`);
        imageData.imageColor = imageColor;
        imageData.imageColorHex = imageColorHex;

        // 生成不同模糊程度的像素图
        imageData.blurPixelMap = await this.getBlurPixelMap(pixelMap, 15);
        imageData.blurPixelMapForCard = await this.getBlurPixelMap(pixelMap, 100);
        Logger.info(TAG, 'getImageDealDataByArr success');
        resolve(imageData);
      } catch (err) {
        Logger.info(TAG, `getImageDealDataByArr err :${JSON.stringify(err)}`)
        reject(err);
      }
    });
  }

  public geArrayBufferFromUrl(url: string): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      // 创建http请求
      let httpRequest = http.createHttp();

      // 发起网络请求获取图片数据
      httpRequest.request(url, {
        method: http.RequestMethod.GET,
        expectDataType: http.HttpDataType.ARRAY_BUFFER
      }).then(response => {
        // 获取图片数据
        let imageData: ArrayBuffer = response.result as ArrayBuffer;
        resolve(imageData);
      }).finally(() => {
        // 确保HTTP连接被关闭
        try {
          httpRequest.destroy();
        } catch (e) {
          // 忽略关闭连接时的错误
        }
      });
    });
  }

  public getPic(value: string | Resource): Resource | string {
    if (typeof value === 'string' && value.startsWith('http')) {
      return value
    }
    return $r(`app.media.${value}`)
  }
}

export default new ImageUtils();