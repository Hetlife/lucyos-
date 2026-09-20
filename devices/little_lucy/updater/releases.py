"""Versioned release staging with atomic pointer switch and rollback."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile


def _slot(root, name):
    link = root / name
    return link.resolve(strict=True) if link.is_symlink() else None


def _point(root, name, target):
    temp = root / ("." + name + ".next")
    temp.unlink(missing_ok=True)
    temp.symlink_to(target.relative_to(root))
    os.replace(temp, root / name)


def status(root):
    root = Path(root).resolve()
    return {name: str(_slot(root, name)) if _slot(root, name) else None for name in ("current", "previous")}


def stage(root, source, version):
    root, source = Path(root).resolve(), Path(source).resolve()
    if not version or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for c in version):
        raise ValueError("unsafe version")
    if not source.is_dir() or source == root or root in source.parents:
        raise ValueError("invalid source")
    releases = root / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    target = releases / version
    if target.exists():
        raise FileExistsError(target)
    temp = Path(tempfile.mkdtemp(prefix=".staging-", dir=releases))
    try:
        shutil.copytree(source, temp, dirs_exist_ok=True, symlinks=False)
        health = Path("release/health.py")
        if not (temp / health).is_file():
            raise ValueError("release requires release/health.py")
        subprocess.run(["python3", str(temp / health)], cwd=temp, check=True, timeout=15, env={"PATH": os.environ.get("PATH", "")})
        os.replace(temp, target)
        old = _slot(root, "current")
        if old:
            _point(root, "previous", old)
        _point(root, "current", target)
        try:
            subprocess.run(["python3", str(target / health)], cwd=target, check=True, timeout=15, env={"PATH": os.environ.get("PATH", "")})
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if old:
                _point(root, "current", old)
            else:
                (root / "current").unlink(missing_ok=True)
            raise RuntimeError("health check failed; rolled back")
        return status(root)
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def rollback(root):
    root = Path(root).resolve()
    previous = _slot(root, "previous")
    if previous is None or root / "releases" not in previous.parents:
        raise ValueError("no previous release")
    current = _slot(root, "current")
    _point(root, "current", previous)
    if current:
        _point(root, "previous", current)
    return status(root)
