# AI Business OS Content Studio v1

This release adds the first production-oriented vertical slice for M05 AI Image Generation and M06 Detail Page Generation while preserving the existing Agent Control, business workspace, product, SKU, worker, scheduler, and operations functions.

## M05 — AI Image Generation

### Implemented
- Authenticated image generation jobs and job history.
- Image types: HERO, LIFESTYLE, EXPLANATION, BANNER, SPEC_SIZE.
- Styles including TECHNICAL_LINE_DRAWING (Product Line Drawing).
- Uses including online sales and brochure/catalog/manual outputs.
- Aspect ratios: 1:1, 4:3, 3:4, 16:9, 9:16, ORIGINAL, CUSTOM.
- Product protection defaults to hard/reference lock.
- Non-locked generation is allowed only when the Product explicitly enables `image_nonlocked_allowed`.
- Managed reference uploads with PRODUCT_REFERENCE / COMPONENT_REFERENCE roles.
- P0 configuration preview, P1 preview generation, revision, final generation, QA and approval gates.
- Preview-first generation limits and configurable estimated-cost fields.
- OpenAI Image API provider implementation through `OPENAI_IMAGE_MODEL`.
- Product-accuracy review gate: hard-locked generated assets require human confirmation before approval.
- Local media persistence through the `media_data` Docker volume.

### Important limitation
Hard/reference lock is fail-closed and reference-driven, but it is not deterministic pixel-level compositing. Product geometry can still require human review. The current v1 therefore marks hard-locked product accuracy for human REVIEW rather than claiming automatic pixel-perfect fidelity.

## M06 — Detail Page Generation

### Implemented
- Detail page jobs, immutable versions, reusable sections and section ordering.
- Brand Style Sheets with reusable color tokens.
- Templates A/B/C and separate page strategies such as Review First and Specs First.
- Required review module structure; review data is sourced only from registered review records.
- Product relations for ADD_ON and RELATED_PRODUCT.
- Conditional add-on / related-product sections: sections are omitted when no active relationship exists.
- Product/SKU/component fact snapshots and fact-hash change detection.
- Approved M05 image asset reuse in detail-page sections.
- COPY vs FACT protection: fact/review/relation sections cannot be overwritten as free-form AI copy.
- Safe section-level revisions, drag/drop reordering and version rollback support.
- QA gates for fact accuracy, review sources, add-on disclosure, related links, ad claims, brand style, image assets and required structure.
- Approval requires QA; FAIL blocks approval and REVIEW requires explicit acknowledgement.
- Structured Canva export package generation after approval.

### Important limitations
- The repository currently produces a structured Canva export package; it does not yet contain server-side Canva OAuth/autofill publishing.
- Marketplace review ingestion is not yet automatic. The review API accepts verified/real review records and the page generator does not fabricate missing reviews.
- Dynamic long-form sales copy is currently template/structured-draft based; a dedicated text-LLM copy provider is not yet wired into this repository.

## User-facing routes
- `/dashboard` — existing business dashboard
- `/image-studio` — M05 AI Image Generation workspace
- `/detail-pages` — M06 Detail Page workspace
- `/operations` — existing Operations UI

## API route groups
- `/api/v1/images/*`
- `/api/v1/detail-pages/*`
- `/api/v1/business/*`

## New migrations
- `0005_image_studio`
- `0006_detail_page_studio`

## Validation completed before packaging
- Python compile validation.
- JavaScript syntax validation for both new UIs.
- Alembic PostgreSQL offline migration SQL generation through `0006_detail_page_studio`.
- Unit/rule tests for M05, M06 and migration chain.
- Existing health, import, run and agent-control tests under an isolated SQLite/test environment.
- FastAPI integration flow for detail-page preparation, QA, approval and Canva export package.
- Image API fail-closed integration flow when no OpenAI API key is configured.

Live EC2/PostgreSQL deployment validation must still be performed after applying the release on the actual server.
