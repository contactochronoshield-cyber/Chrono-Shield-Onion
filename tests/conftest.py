import pytest


def _readable(path):
    try:
        open(path).close()
        return True
    except OSError:
        return False


_SKIP = {}
if not _readable("/proc/stat"):
    _SKIP["test_telemetry_authorized"] = "/proc/stat no legible (Android/Termux)"
if not (_readable("/proc/stat") and _readable("/proc/net/tcp")):
    _SKIP["test_metrics_endpoint"] = "/proc no legible completo (Android/Termux)"


def pytest_collection_modifyitems(config, items):
    for it in items:
        if it.name in _SKIP:
            it.add_marker(pytest.mark.skip(reason=_SKIP[it.name]))
