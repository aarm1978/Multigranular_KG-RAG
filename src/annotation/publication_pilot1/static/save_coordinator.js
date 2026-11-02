"use strict";

(function expose(factory) {
  const Coordinator = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = Coordinator;
  if (typeof window !== "undefined") window.BoundSaveCoordinator = Coordinator;
})(function buildCoordinator() {
  /** Serialize source-unit-bound snapshots across debounce, save, and navigation. */
  return class BoundSaveCoordinator {
    constructor(saveSnapshot, delayMilliseconds = 650) {
      this.saveSnapshot = saveSnapshot;
      this.delayMilliseconds = delayMilliseconds;
      this.pending = null;
      this.timer = null;
      this.chain = Promise.resolve();
      this.lastTask = Promise.resolve();
      this.inFlight = 0;
      this.dirty = false;
    }

    /** Capture a detached snapshot so later form changes cannot mutate this save. */
    schedule(request) {
      if (!request || !request.sourceUnitID) return;
      if (this.timer !== null) clearTimeout(this.timer);
      this.pending = JSON.parse(JSON.stringify(request));
      this.dirty = true;
      this.timer = setTimeout(() => {
        this.flush().catch(() => {});
      }, this.delayMilliseconds);
    }

    /** Cancel a queued snapshot when a newer explicit snapshot supersedes it. */
    clearPending() {
      if (this.timer !== null) clearTimeout(this.timer);
      this.timer = null;
      this.pending = null;
    }

    /** Flush the exact queued unit/snapshot before navigation may continue. */
    async flush() {
      if (this.pending === null) return this.lastTask;
      const request = this.pending;
      this.clearPending();
      return this.enqueue(request);
    }

    /** Persist an explicit snapshot after discarding an older queued debounce. */
    async saveNow(request) {
      this.clearPending();
      this.dirty = true;
      return this.enqueue(JSON.parse(JSON.stringify(request)));
    }

    /** Wait for persistence, then and only then replace the displayed unit. */
    async navigate(sourceUnitID, loadUnit) {
      await this.flush();
      return loadUnit(sourceUnitID);
    }

    /** Report whether close/reload could still discard local form state. */
    hasUnsavedChanges() {
      return this.dirty || this.pending !== null || this.inFlight > 0;
    }

    /** Serialize network saves and retain dirty state after a failure. */
    enqueue(request) {
      this.inFlight += 1;
      const task = this.chain.catch(() => {}).then(() => this.saveSnapshot(request));
      this.lastTask = task;
      this.chain = task.catch(() => {});
      return task.then(result => {
        this.inFlight -= 1;
        if (this.pending === null && this.inFlight === 0) this.dirty = false;
        return result;
      }, error => {
        this.inFlight -= 1;
        this.dirty = true;
        throw error;
      });
    }
  };
});
