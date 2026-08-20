from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.services.product_image_fact import ProductImageFactError


_DEFAULT_MODEL = "u2netp"
_CHILD_CODE = r'''
import os
import sys
from rembg import new_session, remove

model = os.environ.get("PRODUCT_IMAGE_FACT_REMBG_MODEL", "u2netp")
session = new_session(model)
content = sys.stdin.buffer.read()
result = remove(content, session=session)
if not result:
    raise SystemExit(3)
sys.stdout.buffer.write(bytes(result))
'''


def isolated_remove_background(content: bytes) -> bytes:
    """Run rembg outside uvicorn so inference memory is released after each image."""
    if not content:
        raise ProductImageFactError("배경제거할 이미지가 비어 있습니다.")

    env = os.environ.copy()
    env.setdefault("PRODUCT_IMAGE_FACT_REMBG_MODEL", _DEFAULT_MODEL)
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("MALLOC_ARENA_MAX", "2")
    env.setdefault("U2NET_HOME", "/app/data/rembg-models")

    try:
        Path(env["U2NET_HOME"]).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ProductImageFactError("배경제거 모델 저장소를 준비할 수 없습니다.") from exc

    try:
        completed = subprocess.run(
            [sys.executable, "-c", _CHILD_CODE],
            input=content,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=int(os.getenv("PRODUCT_IMAGE_FACT_REMBG_TIMEOUT_SECONDS", "180")),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProductImageFactError("배경제거 처리 시간이 초과되었습니다.") from exc
    except OSError as exc:
        raise ProductImageFactError("배경제거 프로세스를 시작할 수 없습니다.") from exc

    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1200:].strip()
        message = "배경제거 처리에 실패했습니다."
        if detail:
            message += f" ({detail})"
        raise ProductImageFactError(message)

    if not completed.stdout:
        raise ProductImageFactError("배경제거 결과가 비어 있습니다.")
    return bytes(completed.stdout)


def install_product_image_fact_oom_patch() -> None:
    """Protect the API process from ONNX/rembg memory spikes."""
    from app.services import product_image_fact as target

    target.remove_background = isolated_remove_background
