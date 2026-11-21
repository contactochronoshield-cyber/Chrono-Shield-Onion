import pytest

try:
    open("/proc/stat").close()
    _OK = True
except OSError:
    _OK = False


def pytest_collection_modifyitems(config, items):
    if _OK:
        return
    skip = pytest.mark.skip(reason="/proc/stat no legible (Android/Termux)")
    for it in items:
        if it.name in ("test_metrics_endpoint", "test_telemetry_authorized"):
            it.add_marker(skip)
