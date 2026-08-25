# My-Computer Architecture

## 1. Platform boundary

My-Computer is a framework and workflow runtime, not a replacement for Telegram, Hugging Face, Vercel, GitHub, Paradox-DB, or an authentication provider. It coordinates those systems through adapter interfaces.

The framework has five boundaries:

| Boundary | Purpose | Canonical responsibility |
|---|---|---|
| Source | Ingest events and objects. | Telegram and future upload/API adapters. |
| Control plane | Own identity, metadata, state, categories, checksums, and audit records. | Paradox-DB adapter. |
| Data plane | Store original objects and derived assets. | Hugging Face Dataset/Bucket and future object-storage adapters. |
| Execution | Run synchronous handlers and asynchronous jobs. | Local worker, hosted worker, or CI runner. |
| Delivery | Expose applications and automation. | Vercel and GitHub Actions adapters. |

## 2. Control plane versus data plane

The control plane stores references and state, not necessarily the original file bytes. A PDF record can remain useful even when a storage provider changes because the object ID, checksum, metadata, category path, and event history remain stable.

The data plane stores original PDFs, extracted text, OCR derivatives, thumbnails, and training assets. Storage paths are provider-specific and are represented through a normalized `storage_locations` collection.

## 3. Canonical event envelope

Every adapter converts provider-specific events into this shape:

```ts
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
```

The `idempotency_key` must be stable for retries. An adapter must be safe to run more than once for the same event.

## 4. Canonical object

```ts
export type MyComputerObject = {
  object_id: string;
  project_id: string;
  source: string;
  source_ref?: string;
  original_filename?: string;
  media_type: string;
  size_bytes?: number;
  sha256?: string;
  classification?: 'scanned' | 'selectable' | 'unknown';
  category_path?: string[];
  metadata: Record<string, unknown>;
  storage_locations: StorageLocation[];
  sync_status: SyncStatus;
  created_at: string;
  updated_at: string;
};

export type StorageLocation = {
  provider: string;
  repository?: string;
  path: string;
  revision?: string;
  url?: string;
  checksum?: string;
};

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
```

## 5. Synchronization state machine

```text
RECEIVED
  -> STORED
  -> CLASSIFIED
  -> INDEXED
  -> QUEUED
  -> UPLOADING
  -> SYNCED
  -> PUBLISHED
```

A failure must not erase the object. It transitions to `RETRY_WAIT` with attempt count, error code, next-attempt time, and provider response. Permanent or suspicious failures transition to `QUARANTINED` for inspection.

## 6. Adapter contracts

Adapters should expose capabilities, not provider implementation details:

```ts
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
```

## 7. First bridge: Telegram to Hugging Face

The bridge must download or access the Telegram file once, calculate a streaming SHA-256, persist the object record, classify the PDF, and enqueue one idempotent Hugging Face upload. Retries must reuse the local or staged file and must not request the same Telegram file repeatedly.

The Hugging Face destination should initially be private. A separate promotion workflow can publish an approved object or category after rights and privacy review.

## 8. Deployment independence

Vercel should host stateless HTTP handlers and lightweight dashboards. Background transfers need a durable execution host or persistent worker. GitHub Actions can perform scheduled or manually triggered migrations, but it should not be assumed to be a real-time queue or permanent file storage layer.

This separation allows My-Computer to run on a local machine, a hosted worker, a CI runner, or another compatible environment without changing project manifests or provider contracts.

## 9. Project manifest requirements

A manifest must declare providers and policy but never contain secrets:

```yaml
project: example
control_plane:
  provider: paradox-db
sources: []
storage: []
applications: []
automation: []
privacy:
  default_visibility: private
  public_promotion_required: true
```

## 10. Non-goals for the first release

The first release will not attempt to provide a universal database replacement, a general-purpose cloud, unlimited storage, a training scheduler for every AI provider, or automatic public publishing. Those are future adapters and product layers.
