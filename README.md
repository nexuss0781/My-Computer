# My-Computer

**My-Computer** is a provider-neutral personal data and deployment fabric. It connects sources, metadata, storage, applications, automation, authentication, and AI workflows through stable contracts and replaceable adapters.

The framework is designed around one principle:

> One identity, one event model, one metadata plane, multiple storage planes, and reproducible deployment.

## Why it exists

My-Computer turns fragmented personal infrastructure into reusable project workflows. Telegram can ingest documents, Paradox-DB can manage metadata and synchronization state, Hugging Face can host research datasets and large files, Vercel can expose stateless applications, GitHub Actions can test and release projects, and the authentication framework can provide a shared identity layer.

My-Computer does not make any one provider the permanent center of the system. Providers are adapters. Projects depend on contracts, not vendor-specific implementation details.

## Core workflow

```text
Source event
    -> normalize into an object and event
    -> persist metadata and sync state
    -> classify or transform
    -> enqueue durable work
    -> write to one or more storage targets
    -> publish application indexes
    -> expose status and audit history
```

## First supported bridge

The first production workflow is Telegram-to-Hugging-Face synchronization:

```text
Telegram PDF
    -> source adapter
    -> checksum and metadata
    -> classification
    -> category assignment
    -> sync queue
    -> Hugging Face Dataset repository
    -> searchable catalog and public/private URL
```

## Repository structure

```text
packages/
  core/             Canonical objects, events, state machine, and provider contracts
  adapters/         Telegram, Paradox-DB, Hugging Face, auth, and Vercel adapters
  workflows/        Reusable ingestion, synchronization, backup, and training workflows
  cli/              Project initialization and diagnostics
projects/
  examples/         Example My-Computer project manifests
schemas/             Versioned JSON schemas and event contracts
docs/                Architecture, security, operations, and integration guides
.github/workflows/   Reproducible validation and release automation
```

## Project model

A My-Computer project is declared with a manifest. The manifest identifies the control plane, storage targets, source adapters, application targets, automation, and AI outputs without embedding secrets.

```yaml
project: amharic-archive
control_plane:
  provider: paradox-db
storage:
  - name: archive
    provider: huggingface
    type: dataset
    repository: Nexuss0781/Amharic_Archive
    visibility: private
sources:
  - provider: telegram
applications:
  - provider: vercel
automation:
  - provider: github-actions
ai:
  text_extraction: true
  training_manifests: true
privacy:
  default_visibility: private
```

## Security

Secrets belong only in deployment secret stores or local secret managers. They must never enter Git, public repositories, manifests, dataset files, backups, workflow logs, or generated catalogs. Public promotion is explicit and reversible where the destination supports it.

## Data integrity

Every object receives a stable ID and SHA-256 checksum. Every synchronization attempt is recorded. A file is marked `SYNCED` only after the destination confirms the object and the control plane records the destination path, revision, and checksum.

## Development

The first release is intentionally contract-first. Provider adapters can be added independently, and the core package remains usable without any external credentials. See `docs/architecture.md`, `docs/workflows.md`, and `projects/examples/amharic-archive.yaml`.

## Roadmap

1. Establish contracts and manifests.
2. Implement Telegram and Hugging Face synchronization.
3. Add Paradox-DB persistence and durable job recovery.
4. Add searchable catalog and project dashboard.
5. Add dataset preparation and training-session manifests.
6. Add authentication, project management, quotas, audit, and promotion workflows.

## License

This repository is currently an architectural foundation. Add the project license before distributing framework code or adapters publicly.
