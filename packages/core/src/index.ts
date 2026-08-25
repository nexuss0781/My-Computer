export type Classification = 'scanned' | 'selectable' | 'unknown';

export type SyncStatus =
  | 'received'
  | 'stored'
  | 'classified'
  | 'indexed'
  | 'queued'
  | 'uploading'
  | 'synced'
  | 'published'
  | 'retry_wait'
  | 'failed'
  | 'quarantined';

export type StorageLocation = {
  provider: string;
  repository?: string;
  path: string;
  revision?: string;
  url?: string;
  checksum?: string;
};

export type MyComputerObject = {
  object_id: string;
  project_id: string;
  source: string;
  source_ref?: string;
  original_filename?: string;
  media_type: string;
  size_bytes?: number;
  sha256?: string;
  classification?: Classification;
  category_path?: string[];
  metadata: Record<string, unknown>;
  storage_locations: StorageLocation[];
  sync_status: SyncStatus;
  created_at: string;
  updated_at: string;
};

export type MyComputerEvent = {
  event_id: string;
  project_id: string;
  type: string;
  source: string;
  object_id: string;
  occurred_at: string;
  payload: Record<string, unknown>;
  idempotency_key: string;
};

export type JobSpec = {
  job_id: string;
  project_id: string;
  kind: string;
  object_id?: string;
  payload: Record<string, unknown>;
  attempt: number;
  available_at: string;
};

export type JobStatus = {
  job_id: string;
  state: 'queued' | 'running' | 'succeeded' | 'retry_wait' | 'failed' | 'quarantined';
  attempt: number;
  message?: string;
  updated_at: string;
};

export type RepositorySpec = {
  provider: string;
  repository: string;
  type: 'dataset' | 'model' | 'space' | 'bucket' | 'object';
  visibility: 'private' | 'public';
};

export interface SourceAdapter {
  readonly name: string;
  verify(): Promise<void>;
  receive(input: unknown): Promise<MyComputerEvent[]>;
}

export interface ControlPlaneAdapter {
  readonly name: string;
  upsertObject(object: MyComputerObject): Promise<void>;
  getObject(projectId: string, objectId: string): Promise<MyComputerObject | null>;
  appendEvent(event: MyComputerEvent): Promise<void>;
  claimJob(projectId: string, objectId: string): Promise<boolean>;
}

export interface StorageAdapter {
  readonly name: string;
  ensureRepository(input: RepositorySpec): Promise<void>;
  put(object: MyComputerObject, sourcePath: string): Promise<StorageLocation>;
  head(location: StorageLocation): Promise<{ exists: boolean; checksum?: string }>;
}

export interface IdentityAdapter {
  readonly name: string;
  verifyToken(token: string): Promise<{ subject: string; claims: Record<string, unknown> }>;
}

export interface ExecutionAdapter {
  readonly name: string;
  enqueue(job: JobSpec): Promise<string>;
  getStatus(jobId: string): Promise<JobStatus>;
}

export function isTerminalSyncStatus(status: SyncStatus): boolean {
  return status === 'synced' || status === 'published' || status === 'quarantined';
}

export function nextRetryDelayMs(attempt: number, baseDelayMs = 1500, maxDelayMs = 15 * 60 * 1000): number {
  const exponent = Math.max(0, Math.min(attempt - 1, 10));
  return Math.min(maxDelayMs, baseDelayMs * 2 ** exponent);
}
