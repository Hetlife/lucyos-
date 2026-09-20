"""Little Lucy local management interface. No implicit SSH or device writes."""
import argparse
import json
from pathlib import Path

from devices.little_lucy.emulator.server import serve
from devices.little_lucy.updater.releases import rollback, stage, status


def main(argv=None):
    p = argparse.ArgumentParser(prog="little-lucyctl")
    p.add_argument("--root", type=Path, default=Path.home() / ".local/share/little-lucy")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("status", "doctor", "discover", "restart", "logs", "screenshot", "rollback", "hardware", "camera", "sensors", "emulator"):
        sub.add_parser(name)
    deploy = sub.add_parser("deploy")
    deploy.add_argument("source", type=Path)
    deploy.add_argument("version")
    args = p.parse_args(argv)
    if args.command == "emulator":
        serve()
    elif args.command == "deploy":
        print(json.dumps(stage(args.root, args.source, args.version), indent=2))
    elif args.command == "rollback":
        print(json.dumps(rollback(args.root), indent=2))
    elif args.command == "status":
        print(json.dumps(status(args.root), indent=2))
    elif args.command == "doctor":
        print(json.dumps({"local_root": str(args.root), "state_schema": 1, "device_access": "not configured", "hardware_inventory": "pending"}, indent=2))
    elif args.command == "discover":
        print("Run platforms/nebula/discover.sh manually after authorized SSH access. No network probe performed.")
    elif args.command == "hardware":
        print("Nebula CPU, graphics, input, camera, G-sensor and storage: pending read-only inventory")
    elif args.command in ("camera", "sensors"):
        print(f"{args.command}: unavailable until hardware inventory and adapter implementation")
    elif args.command == "screenshot":
        print("Physical screenshot unavailable until renderer and framebuffer inventory; local emulator is available.")
    elif args.command in ("restart", "logs"):
        print(f"{args.command}: unavailable until remote service adapter is verified")


if __name__ == "__main__":
    main()
