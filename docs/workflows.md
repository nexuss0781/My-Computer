# My-Computer Workflows

## Telegram ingestion

A source adapter receives a Telegram update and normalizes it into a My-Computer event. The adapter must preserve the Telegram chat ID, message ID, file name, media type, file size, and source URL or reference without making Telegram-specific fields part of the core contract.

The ingestion workflow creates an object ID, streams a SHA-256 checksum, records the object in the control plane, and schedules classification. Large files must be read once and retained in a durable local or staging path until all required storage writes finish.

## Hugging Face synchronization

The Hugging Face adapter maps a project manifest to a Dataset repository or storage destination. It creates deterministic paths from the category path and object ID, checks the existing destination by checksum, uploads only when needed, and writes the returned revision and URL into the object’s storage locations.

A synchronization job is idempotent. Repeating the job after a crash must not create a duplicate object or lose the metadata record. Failed jobs record the provider error, attempt number, and next retry time.

## Catalog generation

The catalog generator writes JSON Lines records because each object can be processed independently and the catalog can be streamed. Category hierarchy is written separately so a dashboard can load the tree without scanning every PDF record.

```json
{"object_id":"obj_123","title":"Example","classification":"scanned","category_path":["Books","Amharic"],"sha256":"...","sync_status":"synced"}
```

## Vercel applications

A Vercel adapter generates or deploys stateless HTTP applications from a project manifest. Applications read the control plane through a narrow API and use storage URLs for large files. Vercel handlers must not proxy multi-gigabyte files through serverless memory or bandwidth when a signed or provider-native URL can be returned.

## Authentication

The identity adapter verifies tokens and returns a stable subject plus claims. Provider-specific token formats stay inside the adapter. Project authorization is evaluated from the subject, project ID, and policy before control-plane mutations or storage promotion.

## AI training exports

The AI workflow consumes synchronized metadata and produces versioned training manifests rather than copying data blindly. A training session records the dataset revision, selected object IDs, checksum list, preprocessing version, split policy, and output artifact locations.

```yaml
session: amharic-archive-training-001
dataset:
  repository: Nexuss0781/Amharic_Archive
  revision: <resolved-revision>
  manifest: metadata/training-manifest.jsonl
selection:
  classification: selectable
preprocessing:
  extraction_version: 1
  tokenizer: <declared-tokenizer>
outputs:
  - type: training-manifest
  - type: evaluation-report
```

## Backup and restore

Backups contain control-plane metadata, categories, sync state, and provider references. They do not silently imply that original files are duplicated. Restore validates schema version, object IDs, checksums, category parents, and storage references before replacing or merging records.

## Public promotion

All projects default to private storage. Promotion is a separate event requiring an explicit policy decision. The promotion job verifies that no secret, personal information, prohibited content, or unauthorized material is present before changing visibility or publishing a URL.

## Recovery

Recovery is driven by the control plane. A worker lists objects in `queued`, `uploading`, `retry_wait`, and `failed` states, claims work using an idempotency key, and retries only according to the provider adapter’s policy. An operator can requeue a quarantined object after inspection.

## Local development

Adapters should support a dry-run mode that validates credentials, repository configuration, paths, and manifests without transferring files. Fixture files and fake provider implementations should be used for contract tests. Real credentials belong in environment variables or a local secret manager, never in fixtures.
