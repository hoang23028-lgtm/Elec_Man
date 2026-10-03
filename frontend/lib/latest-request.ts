/** Invalidates responses from a previous selection or an overlapping request. */
export class LatestRequest {
  private revision = 0;

  begin(): number {
    return ++this.revision;
  }

  isCurrent(revision: number): boolean {
    return revision === this.revision;
  }

  invalidate(): void {
    this.revision++;
  }
}
