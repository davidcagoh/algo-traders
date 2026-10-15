def select_device(cuda_available: bool, mps_available: bool) -> str:
    if cuda_available:
        return "cuda"
    if mps_available:
        return "mps"
    return "cpu"


def current_device() -> str:
    import torch

    return select_device(
        cuda_available=torch.cuda.is_available(),
        mps_available=torch.backends.mps.is_available(),
    )
