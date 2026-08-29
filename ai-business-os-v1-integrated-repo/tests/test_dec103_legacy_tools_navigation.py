from app.global_navigation import GLOBAL_STYLE, NAV_CONTENT, navigation_markup


def test_current_and_previous_tools_are_visually_separated():
    assert "관리·제작 도구" in NAV_CONTENT
    assert "이전 버전 도구" in NAV_CONTENT
    assert "보조·확인·복구용" in NAV_CONTENT
    assert '<details class="aios-legacy-tools">' in NAV_CONTENT
    assert "aios-legacy-menu" in GLOBAL_STYLE


def test_previous_tools_keep_their_proven_routes():
    assert 'href="/image-studio">이전 이미지 생성기' in NAV_CONTENT
    assert 'href="/detail-pages">이전 상세페이지 생성기' in NAV_CONTENT
    assert 'href="/dashboard">이전 운영 대시보드' in NAV_CONTENT


def test_navigation_contains_previous_tools_on_desktop_and_mobile():
    html = navigation_markup(False)
    assert html.count("이전 버전 도구") == 2
    assert html.count("이전 이미지 생성기") == 2
