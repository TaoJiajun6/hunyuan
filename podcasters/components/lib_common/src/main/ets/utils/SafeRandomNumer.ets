import { SafeRandom } from '@hw-agconnect/petal-aegis';

export class SafeRandomGenerate {
  public static generate() {
    let hexString =  SafeRandom.ohAegRandomHex(1)
    let decimalValue = 0;
    const hexChars = '0123456789ABCDEF';

    for (let char of hexString) {
      const value = hexChars.indexOf(char);
      decimalValue = decimalValue * 16 + value;
    }
    return decimalValue;
  }
}