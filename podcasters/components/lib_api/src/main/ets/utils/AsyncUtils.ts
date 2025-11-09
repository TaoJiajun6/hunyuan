export const excludeMethods = [
  'queryRootComment',
];

/**
 * 类所有方法异步 装饰器
 * @param constructor
 */
export function AsyncClass(constructor): void {
  const originalPrototype = constructor.prototype;

  // 获取所有方法名
  const methodNames = Object.getOwnPropertyNames(originalPrototype)
    .filter(name => name !== 'constructor' && typeof originalPrototype[name] === 'function');

  // 修改每个方法
  methodNames
    .filter(v => !excludeMethods.includes(v))
    .forEach(methodName => {
      const originalMethod = originalPrototype[methodName];

      originalPrototype[methodName] = function (...args: any[]): Promise<any> {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve(originalMethod.apply(this, args));
          }, 200)
        })
      };
    });
}

/**
 * 单个方法异步 装饰器
 * @param target
 * @param propertyKey
 * @param descriptor
 * @returns
 */
export function AsyncFunc(target: any, propertyKey: string, descriptor: PropertyDescriptor): PropertyDescriptor {
  const originalMethod = descriptor.value;

  descriptor.value = function (...args: any[]): Promise<any> {
    // 执行原方法并将结果包装为Promise
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(originalMethod.apply(this, args));
      }, 200)
    })
  };

  return descriptor;
}