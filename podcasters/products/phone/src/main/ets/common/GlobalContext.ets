import { common } from '@kit.AbilityKit';

/**
 * 全局应用上下文管理类
 * 用于在应用全局范围内访问UIAbilityContext
 */
export class GlobalContext {
  private static context: common.UIAbilityContext | null = null;

  /**
   * 初始化全局应用上下文
   * @param context UIAbility上下文
   */
  public static initContext(context: common.UIAbilityContext): void {
    GlobalContext.context = context;
  }

  /**
   * 获取全局应用上下文
   * @returns UIAbility上下文，如果未初始化则返回null
   */
  public static getContext(): common.UIAbilityContext | null {
    return GlobalContext.context;
  }

  /**
   * 检查上下文是否已初始化
   * @returns 如果上下文已初始化返回true，否则返回false
   */
  public static isInitialized(): boolean {
    return GlobalContext.context !== null;
  }
}

