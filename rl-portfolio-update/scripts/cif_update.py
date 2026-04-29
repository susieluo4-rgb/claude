#!/usr/bin/env python3
"""
CIF 组件 — 轻量包装，直接调用 cif_portfolio_sync.py

支持 --auto（执行更新）和 --dry-run（预览）。

用法：
  python3 cif_update.py            # 预览变更
  python3 cif_update.py --auto     # 执行更新
"""
import subprocess
import sys
from pathlib import Path

CIF_SYNC_SCRIPT = (
    Path.home()
    / ".claude"
    / "skills"
    / "rl-portfolio-monitor"
    / "scripts"
    / "cif_portfolio_sync.py"
)


def main():
    auto_mode = "--auto" in sys.argv

    if not CIF_SYNC_SCRIPT.exists():
        print(f"错误: CIF 同步脚本不存在: {CIF_SYNC_SCRIPT}")
        sys.exit(1)

    cmd = ["python3", str(CIF_SYNC_SCRIPT)]
    cmd.append("--auto" if auto_mode else "--dry-run")

    print(f"运行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
