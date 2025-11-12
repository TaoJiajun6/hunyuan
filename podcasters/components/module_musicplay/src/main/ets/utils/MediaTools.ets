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
import { common } from '@kit.AbilityKit';
import { resourceManager } from '@kit.LocalizationKit';
import { http } from '@kit.NetworkKit';
import { Logger } from './Logger';
import ImageUtils from './ImageUtils';

export class MediaTools {
  static async getPixelMapBylabel(context: common.UIAbilityContext,
    label: resourceManager.Resource | string): Promise<PixelMap> {
    try {
      if (typeof label === 'string' && label.startsWith('http')) {
        return MediaTools.getPixelMapFromNetwork(label);
      } else {
        return MediaTools.getPixelMapFromResource(context, label);
      }
    } catch (error) {
      // 处理可能的异常情况
      throw new Error(`Failed to create pixel map: ${error.message}`);
    }
  }

  /**
   * 从网络URL创建PixelMap对象
   * @param url 网络图片URL
   * @returns Promise<PixelMap> PixelMap对象
   */
  static async getPixelMapFromNetwork(url: string): Promise<PixelMap> {
    let httpRequest = http.createHttp();
    try {
      // 发起网络请求获取图片数据
      const response = await httpRequest.request(url, {
        method: http.RequestMethod.GET,
        expectDataType: http.HttpDataType.ARRAY_BUFFER
      });

      // 检查响应状态
      if (response.responseCode !== http.ResponseCode.OK) {
        throw new Error(`HTTP request failed with status code: ${response.responseCode}`);
      }

      // 检查返回的数据类型
      if (!response.result || !(response.result instanceof ArrayBuffer)) {
        throw new Error('Invalid response data or data type is not ArrayBuffer');
      }

      // 创建图像源并生成PixelMap
      let imageSource = image.createImageSource(response.result as ArrayBuffer);
      try {
        return await imageSource.createPixelMap();
      } finally {
        // 确保资源被释放
        if (imageSource.release) {
          imageSource.release();
        }
      }
    } catch (error) {
      // 处理可能的异常情况
      throw new Error(`Failed to create pixel map from network: ${error.message}`);
    } finally {
      // 销毁HTTP请求对象
      httpRequest.destroy();
    }
  }

  static async getPixelMapFromResource(context: common.UIAbilityContext,
    name: resourceManager.Resource | string): Promise<PixelMap> {
    try {
      let resourceMgr = context.resourceManager;
      if (!name) {
        throw new Error('Resource name is invalid');
      }

      if (typeof name === 'string') {
        let value = context.resourceManager.getMediaByNameSync(name as string)
        let pixelMap = image.createImageSource(value.buffer).createPixelMapSync();
        if (value.buffer.byteLength > 2048 * 1024) {
          pixelMap = await ImageUtils.compressImage(pixelMap, 2048);
        }
        return pixelMap;
      }

      let fileData: Uint8Array = await resourceMgr.getMediaContent(name as resourceManager.Resource);
      let imageSource = image.createImageSource(fileData.buffer as ArrayBuffer);
      try {
        return await imageSource.createPixelMap();
      } finally {
        // 确保资源被释放
        if (imageSource.release) {
          imageSource.release();
        }
      }
    } catch (error) {
      // 处理可能的异常情况
      throw new Error(`Failed to create pixel map: ${error.message}`);
    }
  }

  static async getPixelMapFromFile(path: string): Promise<image.PixelMap> {
    return await image.createImageSource(path).createPixelMap();
  }

  private static fill(value: number): string {
    return value.toString().padStart(2, '0');
  }

  static msToCountdownTime(ms: number): string {
    if (!ms) {
      return '00:00';
    }
    const days = Math.floor(ms / (1000 * 60 * 60 * 24));
    const hours = Math.floor((ms % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((ms % (1000 * 60)) / 1000);
    return `${(days ? MediaTools.fill(days) + ':' : '')}${(hours ? MediaTools.fill(hours) + ':' : '')}
      ${MediaTools.fill(minutes)}:${MediaTools.fill(seconds)} `.trim();
  }

  /**
   * 计算当前时间往后 N小时N分钟的目标时间毫秒数
   * @param hours 往后的小时数（≥0，支持整数/字符串）
   * @param minutes 往后的分钟数（0-59，支持整数/字符串）
   * @returns 目标时间毫秒数（非法值返回当前时间毫秒数）
   */
  static getFutureTimeMs(hours: number | string, minutes: number | string): number {
    // 1. 类型转换：统一转为数字（适配接口/输入的字符串格式）
    const hourNum = typeof hours === 'string' ? Number(hours) : hours;
    const minuteNum = typeof minutes === 'string' ? Number(minutes) : minutes;

    // 2. 合法性校验：排除负数、非数字、分钟超60的情况
    if (isNaN(hourNum) || isNaN(minuteNum) || hourNum < 0 || minuteNum < 0 || minuteNum > 60) {
      Logger.warn(`无效时间偏移：小时=${hours}，分钟=${minutes}，默认返回当前时间`);
      return Date.now(); // 非法值返回当前时间，避免业务异常
    }

    // 3. 计算时间偏移量（小时→毫秒 + 分钟→毫秒）
    const timeOffsetMs = hourNum * 60 * 60 * 1000 + minuteNum * 60 * 1000;

    // 4. 当前时间 + 偏移量 = 未来目标时间
    return Date.now() + timeOffsetMs;
  }

  static formatMsToTime(ms: number): string {
    const date = new Date(ms);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0'); // 月份0-11，补0
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    const second = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
  }

  /**
   * 计算未来时间点距离当前时间的剩余时间
   * @param futureTime 未来的时间戳（毫秒）
   * @returns 包含小时和分钟的对象
   */
  static getRemainingTime(futureTime: number): string {
    const currentTime = Date.now();
    const remainingMilliseconds = futureTime - currentTime;

    // 确保时间有效（未来时间必须大于当前时间）
    if (remainingMilliseconds <= 0) {
      return '00:00';
    }

    // 转换为小时和分钟
    const totalMinutes = Math.floor(remainingMilliseconds / (1000 * 60));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    return `${(hours ? MediaTools.fill(hours) : '00')}:${MediaTools.fill(minutes)}`.trim();
  }

  /**
   * 计算未来时间点距离当前时间的剩余时间（分钟:秒格式）
   * @param futureTime 未来的时间戳（毫秒）
   * @returns 包含分钟和秒的字符串（MM:SS格式）
   */
  static getRemainingTimeMMSS(futureTime: number): string {
    const currentTime = Date.now();
    const remainingMilliseconds = futureTime - currentTime;

    // 确保时间有效（未来时间必须大于当前时间）
    if (remainingMilliseconds <= 0) {
      return '00:00';
    }

    // 转换为分钟和秒
    const totalSeconds = Math.floor(remainingMilliseconds / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    return `${MediaTools.fill(minutes)}:${MediaTools.fill(seconds)}`;
  }
}