/** A single decision at a time; closing or unmounting always cancels it. */
export class ConfirmationGate {
  private resolve: ((accepted: boolean) => void) | null = null;

  begin(): Promise<boolean> | null {
    if (this.resolve) return null;
    return new Promise<boolean>((resolve) => { this.resolve = resolve; });
  }

  finish(accepted: boolean): void {
    const resolve = this.resolve;
    this.resolve = null;
    resolve?.(accepted);
  }
}
