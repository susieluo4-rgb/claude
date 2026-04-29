#!/usr/bin/env python3
"""
组合持仓 + 净值更新统一入口编排层。

用法：
  python3 portfolio_update.py --cif              # 仅 CIF 持仓
  python3 portfolio_update.py --runming          # 仅润铭持仓
  python3 portfolio_update.py --nav              # 更新两个组合净值
  python3 portfolio_update.py --all              # 全部（持仓+净值）
  python3 portfolio_update.py --backfill-nav runming  # 润铭净值历史回填
  python3 portfolio_update.py --list             # 列出可用组件
"""
import argparse
import subprocess
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).parent.parent
CIF_SYNC_SCRIPT = (
    Path.home()
    / ".claude"
    / "skills"
    / "rl-portfolio-monitor"
    / "scripts"
    / "cif_portfolio_sync.py"
)
RUNMING_SYNC_SCRIPT = SKILL_DIR / "scripts" / "runming_update.py"
FETCH_NAV_SCRIPT = SKILL_DIR / "scripts" / "fetch_nav.py"


COMPONENTS = {
    "cif": {
        "name": "CIF 持仓同步",
        "script": CIF_SYNC_SCRIPT,
        "status": "ready",
    },
    "runming": {
        "name": "润铭持仓同步",
        "script": RUNMING_SYNC_SCRIPT,
        "status": "ready",
    },
    "nav": {
        "name": "净值拉取（润铭 + CIF）",
        "script": FETCH_NAV_SCRIPT,
        "status": "ready",
    },
}


def run_cif(dry_run: bool) -> bool:
    if not CIF_SYNC_SCRIPT.exists():
        print(f"错误: CIF 同步脚本不存在: {CIF_SYNC_SCRIPT}")
        return False
    cmd = ["python3", str(CIF_SYNC_SCRIPT)]
    cmd.append("--dry-run" if dry_run else "--auto")
    print(f"运行: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode == 0


def run_runming(dry_run: bool) -> bool:
    if not RUNMING_SYNC_SCRIPT.exists():
        print(f"错误: 润铭同步脚本不存在: {RUNMING_SYNC_SCRIPT}")
        return False
    cmd = ["python3", str(RUNMING_SYNC_SCRIPT)]
    cmd.append("--dry-run" if dry_run else "--auto")
    print(f"运行: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode == 0


def run_nav(backfill: str = None) -> bool:
    if not FETCH_NAV_SCRIPT.exists():
        print(f"错误: 净值拉取脚本不存在: {FETCH_NAV_SCRIPT}")
        return False
    cmd = ["python3", str(FETCH_NAV_SCRIPT)]
    if backfill:
        cmd.extend(["--backfill", backfill])
    print(f"运行: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode == 0


def list_components():
    print(f"{'组件':25s} {'状态':10s} {'脚本'}")
    print("-" * 70)
    for key, comp in COMPONENTS.items():
        script = str(comp["script"]) if comp["script"] else "—"
        status = "✅" if comp["status"] == "ready" else "⏳"
        print(f"{key:25s} {status:10s} {script}")
    print()
    print("参数说明:")
    print("  --cif              更新 CIF 持仓")
    print("  --runming          更新润铭持仓")
    print("  --nav              更新两个组合净值（增量）")
    print("  --backfill-nav {组合}  净值全量历史回填")
    print("  --all              更新全部（持仓+净值）")
    print("  --dry-run          预览模式（仅持仓同步）")


def main():
    parser = argparse.ArgumentParser(description="组合持仓 + 净值更新统一入口")
    parser.add_argument("--cif", action="store_true", help="更新 CIF 持仓")
    parser.add_argument("--runming", action="store_true", help="更新润铭持仓")
    parser.add_argument("--nav", action="store_true", help="更新两个组合净值")
    parser.add_argument("--all", action="store_true", help="更新全部（持仓+净值）")
    parser.add_argument("--dry-run", action="store_true", help="预览变更，不修改文件")
    parser.add_argument("--backfill-nav", choices=["runming"], help="净值全量历史回填")
    parser.add_argument("--list", action="store_true", help="列出可用组件")
    args = parser.parse_args()

    if args.list:
        list_components()
        return

    if args.backfill_nav:
        print(f"\n{'='*50}")
        print(f"  净值历史回填: {args.backfill_nav}")
        print(f"{'='*50}")
        if not run_nav(backfill=args.backfill_nav):
            print(f"  ✗ 回填失败")
            sys.exit(1)
        print(f"  ✓ 回填完成")
        return

    if not args.cif and not args.runming and not args.nav and not args.all:
        parser.print_help()
        print()
        list_components()
        sys.exit(1)

    success = True

    if args.cif or args.all:
        print(f"\n{'='*50}")
        print("  CIF 持仓同步")
        print(f"{'='*50}")
        if not run_cif(args.dry_run):
            print("  ✗ CIF 更新失败")
            success = False
        else:
            print("  ✓ CIF 更新完成")

    if args.runming or args.all:
        print(f"\n{'='*50}")
        print("  润铭持仓同步")
        print(f"{'='*50}")
        if not run_runming(args.dry_run):
            print("  ✗ 润铭更新失败")
            success = False
        else:
            print("  ✓ 润铭更新完成")

    if args.nav or args.all:
        print(f"\n{'='*50}")
        print("  净值拉取")
        print(f"{'='*50}")
        if not run_nav():
            print("  ✗ 净值更新失败")
            success = False
        else:
            print("  ✓ 净值更新完成")

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
