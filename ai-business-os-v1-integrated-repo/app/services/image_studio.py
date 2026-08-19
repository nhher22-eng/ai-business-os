from __future__ import annotations

import base64
import mimetypes
import re
import struct
import uuid
from pathlib import Path

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    ImageGeneratedAsset,
    ImageGenerationJob,
    ImageQAResult,
    ImageReferenceAsset,
    ImageReviewEvent,
    Product,
    ProductDetail,
)


IMAGE_TYPES = {"HERO", "LIFESTYLE", "EXPLANATION", "BANNER", "SPEC_SIZE"}
STYLE_PRESETS = {
    "PRODUCT_PHOTO",
    "LIFESTYLE_PHOTO",
    "ADVERTISING",
    "WHITE_BACKGROUND",
    "THREE_D",
    "TECHNICAL_LINE_DRAWING",
}
USAGE_CONTEXTS = {
    "SMARTSTORE",
    "DETAIL_PAGE",
    "SNS",
    "AD_BANNER",
    "BROCHURE",
    "CATALOG",
    "LEAFLET",
    "USER_MANUAL",
    "PRODUCT_GUIDE",
    "PACKAGE_INSERT",
}
ASPECT_RATIOS = {"1:1", "4:3", "3:4", "16:9", "9:16", "ORIGINAL", "CUSTOM"}
REFERENCE_ROLES = {
    "PRODUCT_REFERENCE",
    "COMPONENT_REFERENCE",
    "MANUFACTURER_REFERENCE",
    "INTERNAL_REFERENCE",
    "STYLE_REFERENCE",
    "EXTERNAL_REFERENCE",
}
LOCK_LEVELS = {"hard_lock", "guided", "creative"}


class ImageStudioError(RuntimeError):
    pass


class ProviderNotConfigured(ImageStudioError):
    pass


class ImageProviderError(ImageStudioError):
    pass


def _round16(value: int) -> int:
    return max(16, int(round(value / 16.0) * 16))


def _validate_size(width: int, height: int) -> tuple[int, int]:
    width = _round16(width)
    height = _round16(height)
    if max(width, height) > 3840:
        raise ImageStudioError("image edge must be <= 3840px")
    if max(width, height) / min(width, height) > 3:
        raise ImageStudioError("image aspect ratio must not exceed 3:1")
    pixels = width * height
    if pixels < 655_360:
        scale = (655_360 / pixels) ** 0.5
        width = _round16(int(width * scale))
        height = _round16(int(height * scale))
    if width * height > 8_294_400:
        raise ImageStudioError("image pixel count exceeds provider maximum")
    return width, height


def _image_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            i += 2
            if marker in {0xD8, 0xD9}:
                continue
            if i + 2 > len(data):
                break
            length = int.from_bytes(data[i:i+2], "big")
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                if i + 7 > len(data):
                    break
                height = int.from_bytes(data[i+3:i+5], "big")
                width = int.from_bytes(data[i+5:i+7], "big")
                return width, height
            if length < 2:
                break
            i += length
    raise ImageStudioError("ORIGINAL 비율을 읽을 수 없는 기준 이미지 형식입니다.")


def _size_for_ratio(width: int, height: int, *, final: bool) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        raise ImageStudioError("invalid reference image size")
    ratio = width / height
    target_pixels = 3_145_728 if final else 983_040
    out_w = int((target_pixels * ratio) ** 0.5)
    out_h = int(out_w / ratio)
    return _validate_size(out_w, out_h)


def output_size(
    job: ImageGenerationJob,
    stage: str,
    *,
    reference_path: Path | None = None,
) -> tuple[int, int]:
    final = stage == "final"
    sizes = {
        "1:1": (2048, 2048) if final else (1024, 1024),
        "4:3": (2048, 1536) if final else (1024, 768),
        "3:4": (1536, 2048) if final else (768, 1024),
        "16:9": (2048, 1152) if final else (1280, 720),
        "9:16": (1152, 2048) if final else (720, 1280),
    }
    if job.aspect_ratio == "CUSTOM":
        if not job.custom_width or not job.custom_height:
            raise ImageStudioError("custom width and height are required")
        return _validate_size(job.custom_width, job.custom_height)
    if job.aspect_ratio == "ORIGINAL":
        if reference_path is None:
            raise ImageStudioError("ORIGINAL 비율에는 관리형 기준 이미지가 필요합니다.")
        width, height = _image_dimensions(reference_path)
        return _size_for_ratio(width, height, final=final)
    if job.aspect_ratio not in sizes:
        raise ImageStudioError("unsupported aspect ratio")
    return sizes[job.aspect_ratio]


def media_root() -> Path:
    root = Path(settings.media_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_name(name: str) -> str:
    name = Path(name).name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return stem or f"asset-{uuid.uuid4().hex[:8]}.bin"


def save_reference_upload(
    *, product_id: str, job_id: str | None, filename: str, content: bytes
) -> str:
    root = media_root()
    target_dir = root / "references" / product_id
    if job_id:
        target_dir = target_dir / job_id
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        safe = f"{uuid.uuid4().hex[:10]}-{_safe_name(filename)}"
        path = target_dir / safe
        path.write_bytes(content)
    except OSError as exc:
        raise ImageStudioError(
            "이미지 저장소에 쓸 수 없습니다. 서버 media_data 권한을 확인해 주세요."
        ) from exc
    rel = path.relative_to(root).as_posix()
    return f"media://{rel}"


def resolve_media_uri(uri: str) -> Path:
    if not uri.startswith("media://"):
        raise ImageStudioError("only managed media:// assets can be used for generation")
    rel = uri[len("media://"):].lstrip("/")
    root = media_root()
    path = (root / rel).resolve()
    if root != path and root not in path.parents:
        raise ImageStudioError("invalid media asset path")
    if not path.exists() or not path.is_file():
        raise ImageStudioError("media asset file is missing")
    return path


_LEGACY_REVISION_RE = re.compile(r"\n\s*수정\s*요청\s*[:：]", re.IGNORECASE)


def clean_original_brief(value: str | None) -> str:
    """Return the immutable original user brief from legacy concatenated request text."""
    text = (value or "").strip()
    if not text:
        return ""
    match = _LEGACY_REVISION_RE.search(text)
    if match:
        text = text[: match.start()].rstrip()
    return text


def build_p0_summary(
    db: Session, job: ImageGenerationJob, references: list[ImageReferenceAsset]
) -> str:
    product = db.scalar(select(Product).where(Product.id == job.product_id))
    detail = db.scalar(select(ProductDetail).where(ProductDetail.product_id == job.product_id))
    locked = [r for r in references if r.lock_level == "hard_lock"]
    lines = [
        f"상품: {product.name if product else job.product_id}",
        f"이미지 유형: {job.image_type}",
        f"스타일: {job.style_preset}",
        f"용도: {job.usage_context}",
        f"비율: {job.aspect_ratio}",
        f"제품보존: {job.protection_mode}",
        f"기준 이미지: {len(references)}장 / HARD LOCK {len(locked)}장",
    ]
    canonical = [r for r in references if r.asset_role in {"PRODUCT_REFERENCE", "COMPONENT_REFERENCE"} and r.lock_level == "hard_lock"]
    if job.protection_mode == "hard_lock" and len(canonical) < 2:
        lines.append("정확도 경고: HARD LOCK 기준세트가 1장뿐입니다. 부속품 기준사진을 추가하면 미확인 연결구 생성 위험을 줄일 수 있습니다.")
    if detail and detail.specification:
        lines.append(f"확정 스펙: {detail.specification}")
    original_brief = clean_original_brief(job.request_text)
    if original_brief:
        lines.append(f"요청사항: {original_brief}")
    return "\n".join(lines)


def build_generation_prompt(
    db: Session,
    job: ImageGenerationJob,
    references: list[ImageReferenceAsset],
    *,
    stage: str,
) -> str:
    product = db.scalar(select(Product).where(Product.id == job.product_id))
    detail = db.scalar(select(ProductDetail).where(ProductDetail.product_id == job.product_id))
    product_name = product.name if product else "the selected product"
    request = clean_original_brief(job.request_text) or "Create a clear commerce-ready product image."
    revision_events = db.scalars(
        select(ImageReviewEvent)
        .where(
            ImageReviewEvent.job_id == job.id,
            ImageReviewEvent.action == "request_revision",
        )
        .order_by(ImageReviewEvent.created_at)
    ).all()
    revision_instructions = [
        (event.comment or "").strip() for event in revision_events if (event.comment or "").strip()
    ]
    prompt = [
        f"Create a {stage} image for the commerce product '{product_name}'.",
        f"Image type: {job.image_type}. Style: {job.style_preset}. Usage: {job.usage_context}.",
        f"Original user brief: {request}",
    ]
    if revision_instructions:
        prompt.append("Apply these revision instructions in order, without replacing the original brief: " + " | ".join(revision_instructions))
    if job.protection_mode == "hard_lock":
        prompt.extend(
            [
                "PRODUCT ACCURACY IS A HARD CONSTRAINT.",
                "Treat the supplied product/component reference images as canonical truth and as an explicit component whitelist.",
                "Do not redesign, substitute, recolor, add, remove, or change the geometry of the product or its components.",
                "NEVER invent or include an unreferenced connector, fitting, adapter, valve, clip, clamp, cap, nozzle, timer, hose accessory, or other product part.",
                "If a connector or accessory is not clearly visible in the canonical product/component references or confirmed product facts, OMIT IT rather than guessing.",
                "For lifestyle images, show the product installed in use. Do not scatter loose kit components or extra accessories in the scene unless the user explicitly requests a contents-layout image.",
                "Preserve connector shapes, locking rings, nozzle/stick proportions, hose diameter appearance, connection topology, component count where visible, and product colors from the references.",
                "You may change only the environment, lighting, camera framing, and non-product background elements unless explicitly requested.",
                "If the reference images conflict with generic product assumptions, follow the reference images. When uncertain, leave the uncertain component out instead of hallucinating it.",
            ]
        )
    if detail:
        facts = [detail.specification, detail.usage, detail.installation_method]
        facts = [x.strip() for x in facts if x and x.strip()]
        if facts:
            prompt.append("Confirmed product facts: " + " | ".join(facts))
    if job.image_type == "SPEC_SIZE":
        prompt.extend(
            [
                "Do not invent measurements or numeric specifications.",
                "Generate the product visual/line drawing only; exact numeric labels are applied from the product database as a separate overlay.",
            ]
        )
    if references:
        product_refs = [r for r in references if r.asset_role in {"PRODUCT_REFERENCE", "COMPONENT_REFERENCE"}]
        prompt.append(
            f"Reference set contains {len(product_refs)} canonical product/component images. Preserve their visible details faithfully."
        )
    return "\n".join(prompt)


class OpenAIImageProvider:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ProviderNotConfigured(
                "OPENAI_API_KEY is not configured; generation is fail-closed."
            )
        self.base = settings.openai_api_base.rstrip("/")
        self.headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        self.timeout = settings.image_request_timeout_seconds

    def generate(self, *, prompt: str, size: str, quality: str) -> bytes:
        payload = {
            "model": settings.openai_image_model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "output_format": "png",
            "background": "opaque",
            "moderation": "auto",
            "n": 1,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base}/images/generations",
                    headers={**self.headers, "Content-Type": "application/json"},
                    json=payload,
                )
            response.raise_for_status()
            data = response.json()
            return base64.b64decode(data["data"][0]["b64_json"])
        except Exception as exc:  # provider boundary
            detail = getattr(getattr(exc, "response", None), "text", "")
            raise ImageProviderError(f"OpenAI image generation failed: {detail or type(exc).__name__}") from exc

    def edit(self, *, prompt: str, size: str, quality: str, image_paths: list[Path]) -> bytes:
        handles = []
        files = []
        try:
            for path in image_paths:
                handle = path.open("rb")
                handles.append(handle)
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                files.append(("image[]", (path.name, handle, mime)))
            form = {
                "model": settings.openai_image_model,
                "prompt": prompt,
                "size": size,
                "quality": quality,
                "output_format": "png",
                "background": "opaque",
                "moderation": "auto",
            }
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base}/images/edits",
                    headers=self.headers,
                    data=form,
                    files=files,
                )
            response.raise_for_status()
            data = response.json()
            return base64.b64decode(data["data"][0]["b64_json"])
        except Exception as exc:  # provider boundary
            detail = getattr(getattr(exc, "response", None), "text", "")
            raise ImageProviderError(f"OpenAI image edit failed: {detail or type(exc).__name__}") from exc
        finally:
            for handle in handles:
                handle.close()


def references_for_job(db: Session, job: ImageGenerationJob) -> list[ImageReferenceAsset]:
    rows = db.scalars(
        select(ImageReferenceAsset)
        .where(
            ImageReferenceAsset.tenant_id == job.tenant_id,
            ImageReferenceAsset.product_id == job.product_id,
            (ImageReferenceAsset.job_id == job.id) | (ImageReferenceAsset.job_id.is_(None)),
        )
        .order_by(ImageReferenceAsset.sort_order, ImageReferenceAsset.created_at)
    ).all()
    return list(rows)


def prepare_job(db: Session, job: ImageGenerationJob) -> ImageGenerationJob:
    refs = references_for_job(db, job)
    if job.protection_mode == "hard_lock":
        has_canonical = any(
            r.lock_level == "hard_lock"
            and r.asset_role in {"PRODUCT_REFERENCE", "COMPONENT_REFERENCE"}
            for r in refs
        )
        if not has_canonical:
            raise ImageStudioError(
                "HARD LOCK 작업에는 PRODUCT_REFERENCE 또는 COMPONENT_REFERENCE 기준 이미지가 필요합니다."
            )
    if job.image_type == "SPEC_SIZE":
        detail = db.scalar(select(ProductDetail).where(ProductDetail.product_id == job.product_id))
        if detail is None or not (detail.specification or "").strip():
            raise ImageStudioError("SPEC_SIZE 작업에는 확정 상품 스펙이 필요합니다.")
    job.p0_summary = build_p0_summary(db, job, refs)
    job.status = "p0_ready"
    db.commit()
    db.refresh(job)
    return job


def _managed_reference_paths(references: list[ImageReferenceAsset]) -> list[Path]:
    paths = []
    for ref in references:
        if ref.internal_reference_only:
            continue
        if not ref.asset_uri.startswith("media://"):
            continue
        paths.append(resolve_media_uri(ref.asset_uri))
    return paths


def _next_asset_version(db: Session, job_id: str, stage: str) -> int:
    current = db.scalar(
        select(func.max(ImageGeneratedAsset.version_no)).where(
            ImageGeneratedAsset.job_id == job_id,
            ImageGeneratedAsset.asset_stage == stage,
        )
    )
    return int(current or 0) + 1


def _save_generated(job: ImageGenerationJob, stage: str, version: int, data: bytes) -> str:
    directory = media_root() / "generated" / job.id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stage}-v{version}.png"
    path.write_bytes(data)
    return f"media://{path.relative_to(media_root()).as_posix()}"


def run_image_qa(
    db: Session, job: ImageGenerationJob, asset: ImageGeneratedAsset
) -> list[ImageQAResult]:
    db.execute(
        delete(ImageQAResult).where(ImageQAResult.generated_asset_id == asset.id)
    )
    refs = references_for_job(db, job)
    checks: list[tuple[str, str, str, str]] = []

    if job.protection_mode == "hard_lock":
        canonical = any(
            r.lock_level == "hard_lock"
            and r.asset_role in {"PRODUCT_REFERENCE", "COMPONENT_REFERENCE"}
            for r in refs
        )
        checks.append(
            (
                "REFERENCE_LOCK",
                "PASS" if canonical else "FAIL",
                "error" if not canonical else "info",
                "HARD LOCK 기준 이미지가 등록되어 있습니다." if canonical else "HARD LOCK 기준 이미지가 없습니다.",
            )
        )
        canonical_refs = [
            r for r in refs
            if r.lock_level == "hard_lock"
            and r.asset_role in {"PRODUCT_REFERENCE", "COMPONENT_REFERENCE"}
        ]
        checks.append(
            (
                "REFERENCE_COVERAGE",
                "PASS" if len(canonical_refs) >= 2 else "REVIEW",
                "info" if len(canonical_refs) >= 2 else "warning",
                f"HARD LOCK 기준 이미지 {len(canonical_refs)}장 등록." if len(canonical_refs) >= 2 else "HARD LOCK 기준 이미지가 1장뿐입니다. 부속품 기준사진 추가를 권장합니다.",
            )
        )
        checks.append(
            (
                "UNKNOWN_COMPONENTS",
                "REVIEW",
                "warning",
                "기준사진에 없는 연결구·어댑터·클립·밸브·기타 부속이 생성되었다면 승인하지 말고 수정 요청하세요.",
            )
        )
        checks.append(
            (
                "HUMAN_PRODUCT_ACCURACY",
                "REVIEW",
                "warning",
                "실제 판매상품과 부속품 형상은 최종 사용자 육안 검토가 필요합니다.",
            )
        )
    else:
        checks.append(("REFERENCE_LOCK", "PASS", "info", "Creative/Guided 작업 규칙을 적용했습니다."))

    ref_paths = _managed_reference_paths(refs)
    expected = output_size(
        job, asset.asset_stage,
        reference_path=ref_paths[0] if (job.aspect_ratio == "ORIGINAL" and ref_paths) else None,
    )
    size_ok = asset.width == expected[0] and asset.height == expected[1]
    checks.append(
        (
            "ASPECT_RATIO",
            "PASS" if size_ok else "FAIL",
            "error" if not size_ok else "info",
            f"출력 크기 {asset.width}x{asset.height}; 목표 {expected[0]}x{expected[1]}",
        )
    )

    if job.image_type == "SPEC_SIZE":
        detail = db.scalar(select(ProductDetail).where(ProductDetail.product_id == job.product_id))
        has_spec = bool(detail and (detail.specification or "").strip())
        checks.append(
            (
                "SPEC_SOURCE",
                "PASS" if has_spec else "FAIL",
                "error" if not has_spec else "info",
                "확정 상품 DB 스펙을 사용합니다." if has_spec else "확정 상품 스펙이 없습니다.",
            )
        )

    rows = []
    for code, status, severity, message in checks:
        row = ImageQAResult(
            tenant_id=job.tenant_id,
            job_id=job.id,
            generated_asset_id=asset.id,
            check_code=code,
            status=status,
            severity=severity,
            message=message,
        )
        db.add(row)
        rows.append(row)

    statuses = {x[1] for x in checks}
    asset.qa_status = "fail" if "FAIL" in statuses else "review" if "REVIEW" in statuses else "pass"
    db.commit()
    return rows


def generate_stage(db: Session, job: ImageGenerationJob, stage: str) -> ImageGeneratedAsset:
    if stage not in {"preview", "final"}:
        raise ImageStudioError("stage must be preview or final")
    if stage == "preview" and job.preview_count >= settings.image_max_preview_generations:
        raise ImageStudioError("이 작업의 Preview 생성 한도에 도달했습니다. 비용/요청사항을 검토한 뒤 새 작업으로 진행하세요.")
    if stage == "final" and job.final_count >= settings.image_max_final_generations:
        raise ImageStudioError("이 작업의 FINAL 생성 한도에 도달했습니다. 추가 고비용 생성을 중단했습니다.")
    if not job.p0_summary:
        prepare_job(db, job)

    refs = references_for_job(db, job)
    input_paths = _managed_reference_paths(refs)

    if stage == "final":
        preview = db.scalar(
            select(ImageGeneratedAsset)
            .where(
                ImageGeneratedAsset.job_id == job.id,
                ImageGeneratedAsset.asset_stage == "preview",
                ImageGeneratedAsset.status == "approved",
            )
            .order_by(ImageGeneratedAsset.version_no.desc())
        )
        if preview is None:
            raise ImageStudioError("FINAL 생성 전 승인된 P1 Preview가 필요합니다.")
        input_paths.append(resolve_media_uri(preview.asset_uri))

    if job.protection_mode == "hard_lock" and not input_paths:
        raise ImageStudioError("HARD LOCK 생성에 사용할 관리형 기준 이미지가 없습니다.")

    width, height = output_size(
        job, stage,
        reference_path=input_paths[0] if (job.aspect_ratio == "ORIGINAL" and input_paths) else None,
    )
    size = f"{width}x{height}"
    quality = settings.image_final_quality if stage == "final" else settings.image_preview_quality
    prompt = build_generation_prompt(db, job, refs, stage=stage)
    provider = OpenAIImageProvider()

    job.status = f"{stage}_generating"
    db.commit()
    try:
        if input_paths:
            image_bytes = provider.edit(
                prompt=prompt,
                size=size,
                quality=quality,
                image_paths=input_paths[:10],
            )
        else:
            image_bytes = provider.generate(prompt=prompt, size=size, quality=quality)
    except Exception:
        job.status = "failed"
        db.commit()
        raise

    version = _next_asset_version(db, job.id, stage)
    uri = _save_generated(job, stage, version, image_bytes)
    asset = ImageGeneratedAsset(
        tenant_id=job.tenant_id,
        job_id=job.id,
        asset_stage=stage,
        version_no=version,
        status="review",
        asset_uri=uri,
        width=width,
        height=height,
        provider_name="openai",
        model_name=settings.openai_image_model,
    )
    db.add(asset)
    if stage == "preview":
        job.preview_count += 1
        job.estimated_cost_micros += settings.image_preview_estimated_cost_micros
        job.status = "preview_review"
    else:
        job.final_count += 1
        job.estimated_cost_micros += settings.image_final_estimated_cost_micros
        job.status = "final_review"
    db.commit()
    db.refresh(asset)
    run_image_qa(db, job, asset)
    db.refresh(asset)
    return asset


def approve_asset(
    db: Session,
    *,
    job: ImageGenerationJob,
    asset: ImageGeneratedAsset,
    approved_by: str | None,
    acknowledge_review: bool,
) -> ImageGeneratedAsset:
    results = db.scalars(
        select(ImageQAResult).where(ImageQAResult.generated_asset_id == asset.id)
    ).all()
    if any(r.status == "FAIL" and not r.resolved for r in results):
        raise ImageStudioError("FAIL QA가 있어 승인할 수 없습니다.")
    if any(r.status == "REVIEW" and not r.resolved for r in results) and not acknowledge_review:
        raise ImageStudioError("REVIEW 항목을 확인했다는 승인이 필요합니다.")
    asset.status = "approved"
    asset.approved_by = approved_by
    from app.db.models import utcnow

    asset.approved_at = utcnow()
    job.status = "final_approved_to_generate" if asset.asset_stage == "preview" else "approved"
    db.add(
        ImageReviewEvent(
            tenant_id=job.tenant_id,
            job_id=job.id,
            generated_asset_id=asset.id,
            action="approve",
            created_by=approved_by,
        )
    )
    db.commit()
    db.refresh(asset)
    return asset
