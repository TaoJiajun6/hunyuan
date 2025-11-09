export enum BreakPointValue {
  SM = 'sm', // [0, 600)
  MD = 'md', // [600, 840)
  LG = 'lg', // [840, +∞)
}

export class BreakPointType<T> {
  private data: Record<string, T>;

  constructor(data: any) {
    this.data = data;
  }

  public getValue(key: string): T {
    return (this.data && key) ? this.data[key] : undefined;
  }
}