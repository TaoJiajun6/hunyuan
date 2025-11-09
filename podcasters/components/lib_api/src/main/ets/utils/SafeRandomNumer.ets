import { SafeRandom } from '@hw-agconnect/petal-aegis';

/*
 * 生成安全随机数
 * */
export class SafeRandomGenerate {
  public static generate() {
    let hexString =  SafeRandom.ohAegRandomHex(2)
    let decimalValue = 0;
    const hexChars = '0123456789ABCDEF';

    for (let char of hexString) {
      const value = hexChars.indexOf(char);
      decimalValue = decimalValue * 16 + value;
    }
    return Math.abs(decimalValue);
  }
}