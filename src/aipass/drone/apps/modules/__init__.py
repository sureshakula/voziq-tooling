"""Drone modules - command routing services."""

def normalize_branch_arg(arg: str) -> str:
    """Normalize branch argument (strip @, uppercase)."""
    return arg.lstrip("@").upper()
