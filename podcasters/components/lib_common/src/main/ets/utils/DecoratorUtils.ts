/**
 * 打印日志，method装饰器
 * @param target
 * @param propertyKey
 * @param descriptor
 * @returns
 */
export function logMethod(target: any, propertyKey: string, descriptor: PropertyDescriptor): PropertyDescriptor {
  const originalMethod = descriptor.value;

  descriptor.value = function (...args: any[]): any {
    console.info(`[Method Call] ${target.constructor.name}.${propertyKey}() with args:`, args);

    // 执行原方法
    const result = originalMethod.apply(this, args);

    console.info(`[Method Result] ${target.constructor.name}.${propertyKey}() returned:`, result);
    return result;
  };

  return descriptor;
}