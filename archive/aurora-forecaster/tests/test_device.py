from aurora_forecaster.device import select_device


def test_prefers_cuda_when_available():
    assert select_device(cuda_available=True, mps_available=True) == "cuda"


def test_prefers_mps_over_cpu_when_cuda_unavailable():
    assert select_device(cuda_available=False, mps_available=True) == "mps"


def test_falls_back_to_cpu_when_neither_available():
    assert select_device(cuda_available=False, mps_available=False) == "cpu"
