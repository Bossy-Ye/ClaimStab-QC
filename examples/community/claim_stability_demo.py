from __future__ import annotations

import sys

from claimstab.pipelines.claim_stability_app import main


def _ensure_default_out_dir(argv: list[str]) -> list[str]:
    """Keep community demo outputs under output/examples unless caller sets one."""
    if "--out-dir" in argv:
        return argv
    return [*argv, "--out-dir", "output/examples/claim_stability_demo"]


if __name__ == "__main__":
    sys.argv = [sys.argv[0], *_ensure_default_out_dir(sys.argv[1:])]
    main()
