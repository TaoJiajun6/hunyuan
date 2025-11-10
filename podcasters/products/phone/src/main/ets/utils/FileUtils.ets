import { picker } from '@kit.CoreFileKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { promptAction } from '@kit.ArkUI';
import { fileIo } from '@kit.CoreFileKit';
import { util } from '@kit.ArkTS';
import { common } from '@kit.AbilityKit';
import fs from '@ohos.file.fs';

/**
 * 文件工具类
 */
export class FileUtils {
  // 文件大小限制（10MB）
  private static readonly MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

  /**
   * 选择音频文件
   * 使用DocumentViewPicker从文件系统中选择音频文件
   * @param context UIAbility上下文，如果未提供则使用getContext()获取
   */
  static async pickAudioFile(context?: common.UIAbilityContext): Promise<Uint8Array | null> {
    try {
      // 获取上下文
      let uiContext: common.UIAbilityContext;
      if (context) {
        uiContext = context;
      } else {
        // 使用getContext()获取当前上下文
        const currentContext = getContext();
        if (!currentContext) {
          throw new Error('无法获取上下文，请传入context参数');
        }
        uiContext = currentContext as common.UIAbilityContext;
      }
      
      // 使用DocumentViewPicker选择文件（需要传入context）
      const documentViewPicker = new picker.DocumentViewPicker(uiContext);
      const documentSelectOptions = new picker.DocumentSelectOptions();
      
      // 设置文件类型过滤器，只显示音频文件（使用文件扩展名）
      documentSelectOptions.fileSuffixFilters = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma', '.amr', '.mp4', '.3gp'];
      documentSelectOptions.maxSelectNumber = 1;

      const documentSelectResult = await documentViewPicker.select(documentSelectOptions);
      // DocumentViewPicker返回的是字符串数组（URI数组）
      if (documentSelectResult && documentSelectResult.length > 0) {
        const fileUri = documentSelectResult[0];
        
        // 使用fs模块读取文件内容（更可靠）
        let file: fs.File | null = null;
        try {
          file = fs.openSync(fileUri, fs.OpenMode.READ_ONLY);
          const stat = fs.statSync(file.fd);
          const fileSize = stat.size;
          const fileSizeMB = fileSize / (1024 * 1024);
          
          // 检查文件大小
          if (fileSize > FileUtils.MAX_FILE_SIZE) {
            promptAction.showToast({
              message: `文件过大: ${fileSizeMB.toFixed(2)}MB，最大支持10MB`,
              duration: 3000
            });
            return null;
          }
          
          const buffer = new ArrayBuffer(stat.size);
          fs.readSync(file.fd, buffer);
          fs.closeSync(file);
          file = null;
          
          promptAction.showToast({
            message: `文件选择成功 (${fileSizeMB.toFixed(2)}MB)`,
            duration: 1500
          });
          
          return new Uint8Array(buffer);
        } finally {
          if (file) {
            fs.closeSync(file);
          }
        }
      }
      return null;
    } catch (error) {
      const err = error as BusinessError;
      const errorMessage = err.message || String(error);
      promptAction.showToast({
        message: `选择文件失败: ${errorMessage}`,
        duration: 2000
      });
      return null;
    }
  }

  /**
   * 将Uint8Array转换为base64字符串
   */
  static uint8ArrayToBase64(uint8Array: Uint8Array): string {
    try {
      const base64Helper = new util.Base64Helper();
      // 使用util.Type.MIME进行base64编码
      return base64Helper.encodeToStringSync(uint8Array, util.Type.MIME);
    } catch (error) {
      const err = error as BusinessError;
      promptAction.showToast({
        message: `Base64编码失败: ${err.message || String(err)}`,
        duration: 2000
      });
      return '';
    }
  }

  /**
   * 将base64字符串转换为Uint8Array
   */
  static base64ToUint8Array(base64: string): Uint8Array {
    try {
      // 移除可能的数据URI前缀（如 data:audio/wav;base64,）
      let base64Data = base64;
      if (base64.includes(',')) {
        base64Data = base64.split(',')[1];
      }
      
      const base64Helper = new util.Base64Helper();
      return base64Helper.decodeSync(base64Data);
    } catch (error) {
      const err = error as BusinessError;
      promptAction.showToast({
        message: `Base64解码失败: ${err.message || String(err)}`,
        duration: 2000
      });
      return new Uint8Array(0);
    }
  }
}

