from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_new_front_tool_routes_are_real_pages_and_legacy_generator_is_preserved():
    expected = {
        "/image-assets": "이미지 요소 자산 생성기",
        "/template-maker": "템플릿 제작기",
        "/detail-page-builder": "상세페이지 생성기",
        "/image-studio": "새 이미지 만들기",
    }
    for path, marker in expected.items():
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 200
        assert marker in response.text


def test_product_registration_uses_new_common_front_navigation():
    response = client.get("/product-registration")
    assert response.status_code == 200
    for label in (
        "기본정보",
        "SKU 초기 구성",
        "준비된 원본 자료",
        "상품 생성 후 통합관리로 이동",
    ):
        assert label in response.text
    assert "나머지는 통합상품관리에서 완성" in response.text


def test_front_tools_use_existing_legacy_tenant_data():
    for path in ("/business-home", "/image-assets", "/template-maker", "/detail-page-builder"):
        response = client.get(path)
        assert "__legacy__" in response.text
        assert "tenant-demo" not in response.text


def test_detail_page_builder_exposes_safe_canva_v12_csv_flow():
    response = client.get("/detail-page-builder")
    assert response.status_code == 200
    for marker in (
        "Canva v1.2 · 72개 텍스트 연결",
        "상품 데이터에서 72개 준비 확인",
        "기존 CSV 검증",
        "Canva CSV 다운로드",
        "Canva v1.2 · 이미지 22개 연결",
        "승인 이미지 22개 준비 확인",
        "prepareCanvaV12Images",
        "/images/draft?tenant_id=",
        "22개 슬롯 지정 저장",
        "saveCanvaV12Images",
        "/images/assign?tenant_id=",
        "같은 이미지는 두 슬롯에 중복 지정할 수 없습니다.",
        "Canva v1.2 · 최종 94필드 실행 준비",
        "94개 최종 실행 준비 확인",
        "checkCanvaV12Autofill",
        "/autofill/readiness?tenant_id=",
        "Canva 서버 인증 연결 필요",
        "Canva 승인 이미지 업로드",
        "승인 후 Canva 업로드",
        "uploadCanvaV12Images",
        "syncCanvaV12Uploads",
        "/images/upload-to-canva?tenant_id=",
        "/images/sync-canva-uploads?tenant_id=",
        "Canva v1.2 상세페이지 자동 생성",
        "최종 실행 승인·Canva 생성",
        "startCanvaV12Autofill",
        "syncCanvaV12Autofill",
        "/autofill/start?tenant_id=",
        "/autofill-runs/",
        "Canva 디자인 열기",
        "/api/v1/detail-page-canva/v1.2/products/",
        "/api/v1/detail-page-canva/v1.2/text/import.csv",
        "/api/v1/detail-page-canva/v1.2/text/bulk.csv",
    ):
        assert marker in response.text
