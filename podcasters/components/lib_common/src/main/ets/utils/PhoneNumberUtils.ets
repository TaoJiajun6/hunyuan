/**
 * 手机号码utils
 */
export class PhoneNumberUtils {
  /**
   * 手机号格式是否正确
   * @param phone
   * @returns
   */
  public static isPhoneNumberValid(phone: string): boolean {
    const PHONE_REG = /^[1][3,4,5,6,7,8,9][0-9]{9}$/;
    return PHONE_REG.test(phone);
  }

  /**
   * 加密显示手机号中间四位
   * @param phone
   * @param maskChar
   * @returns
   */
  public static encryptPhone(phone: string, maskChar: string = '*'): string {
    return phone.replace(/(\d{3})(\d{4})(\d{4})/, `$1${maskChar.repeat(4)}$3`);
  }
}