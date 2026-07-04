from data.health import check_required_packages

def test_package_check_returns_dict():
    result = check_required_packages()
    assert isinstance(result, dict)
    assert "streamlit" in result
