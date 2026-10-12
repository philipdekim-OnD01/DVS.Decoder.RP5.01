#!/usr/bin/env python3
"""Install/restore the verified Pi 5 snapshot. No automatic reboot."""
import argparse, hashlib, json, os, pathlib, pwd, shutil, subprocess, sys, tempfile, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
KERNEL = "6.12.47+rpt-rpi-2712"
UNIT = "dvs-raw2-production.service"
VENV = pathlib.Path("/home/philip/dvs_web_app/.venv")
BOOT = pathlib.Path("/boot/firmware/config.txt")

def run(*args, **kw):
    return subprocess.run(args, check=True, **kw)

def verify():
    for line in (ROOT / "SNAPSHOT_SHA256SUMS").read_text().splitlines():
        expected, rel = line.split(None, 1)
        p = ROOT / rel.strip()
        if hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Snapshot checksum mismatch: " + str(p))

def configure_boot(current):
    active = {line.strip() for line in current.splitlines()}
    required = ["dtparam=i2c_csi_dsi0=on", "gpio=35=op,dh", "dtoverlay=s5krc1s-cam0"]
    missing = [line for line in required if line not in active]
    if not missing: return current
    return current + "\n# BEGIN DVS SNAPSHOT\n[all]\n" + "\n".join(missing) + "\n# END DVS SNAPSHOT\n"

def files():
    return sorted(p for p in (ROOT / "payload").rglob("*") if p.is_file())

def preflight():
    if os.geteuid() != 0: raise RuntimeError("Run sudo ./install.sh")
    if os.uname().release != KERNEL or os.uname().machine != "aarch64":
        raise RuntimeError("Requires aarch64 kernel " + KERNEL + "; no files changed")
    if "Raspberry Pi 5" not in pathlib.Path("/proc/device-tree/model").read_text():
        raise RuntimeError("Requires Raspberry Pi 5")
    user = pwd.getpwnam("philip")
    if user.pw_uid != 1000 or user.pw_dir != "/home/philip":
        raise RuntimeError("Requires desktop user philip, UID 1000, /home/philip")
    if not BOOT.is_file(): raise RuntimeError("Missing " + str(BOOT))
    for unit in ("dvs-web.service", "dvs-live-thumbnail.service", "dvs-live-event-viewer.service"):
        if subprocess.run(["systemctl", "is-active", "--quiet", unit]).returncode == 0:
            raise RuntimeError("Conflicting service is active; stop/disable it first: " + unit)

def backup(targets, directory):
    directory.mkdir(parents=True, exist_ok=False)
    entries=[]
    for target in targets:
        if target.is_symlink(): raise RuntimeError("Refusing symlink target: " + str(target))
        exists=target.exists()
        item={"path":str(target), "existed":exists}
        if exists:
            nodes=[target]+(list(target.rglob("*")) if target.is_dir() else [])
            item["owners"]={str(node.relative_to(target)):[node.lstat().st_uid,node.lstat().st_gid] for node in nodes}
        entries.append(item)
        if exists:
            dst=directory/"files"/str(target).lstrip("/")
            dst.parent.mkdir(parents=True, exist_ok=True)
            if target.is_dir(): shutil.copytree(target,dst,symlinks=True)
            else: shutil.copy2(target,dst)
    (directory/"manifest.json").write_text(json.dumps(entries,indent=2))

def restore(directory):
    entries=json.loads((directory/"manifest.json").read_text())
    for item in reversed(entries):
        target=pathlib.Path(item["path"])
        if target.is_dir() and not target.is_symlink(): shutil.rmtree(target)
        elif target.exists() or target.is_symlink(): target.unlink()
        if item["existed"]:
            src=directory/"files"/str(target).lstrip("/")
            target.parent.mkdir(parents=True,exist_ok=True)
            if src.is_dir(): shutil.copytree(src,target,symlinks=True)
            else: shutil.copy2(src,target)
            for rel, owner in item.get("owners",{}).items():
                node=target if rel=="." else target/rel
                if os.geteuid()==0: os.chown(node,*owner,follow_symlinks=False)

def restore_system(directory):
    run("systemctl","stop",UNIT)
    restore(directory)
    run("depmod","-a",KERNEL); run("systemctl","daemon-reload")
    state=json.loads((directory/"service.json").read_text())
    if state["enabled"]: run("systemctl","enable",UNIT)
    else: subprocess.run(["systemctl","disable",UNIT],check=False)
    if state["active"]: run("systemctl","start",UNIT)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true",help="Read-only checks; no installation")
    parser.add_argument("--stage-root",type=pathlib.Path,help="Copy payload into a NEW directory only; no system changes")
    parser.add_argument("--restore",type=pathlib.Path,help="Restore a backup created by this installer")
    args=parser.parse_args()
    if args.restore:
        if os.geteuid()!=0: raise RuntimeError("Restore requires sudo")
        if os.uname().release!=KERNEL: raise RuntimeError("Boot the matching kernel before restore")
        restore_system(args.restore.resolve()); print("Restored. Reboot to reload original drivers."); return
    verify()
    if args.stage_root:
        shutil.copytree(ROOT/"payload",args.stage_root)
        print("Payload staged (no dependencies, boot, or service changes):",args.stage_root); return
    preflight()
    for module in (ROOT/"payload/lib/modules"/KERNEL).rglob("*.ko"):
        vermagic=subprocess.check_output(["modinfo","-F","vermagic",str(module)],text=True)
        if vermagic.split()[0]!=KERNEL: raise RuntimeError("Driver kernel mismatch")
    if args.check: print("Snapshot hashes, platform, user, and kernel modules: OK"); return
    run("apt-get","update")
    run("apt-get","install","-y","python3-venv","python3-pip","python3-numpy","python3-pyqt5","python3-smbus2","ffmpeg","v4l-utils","i2c-tools","kmod","xwayland")
    # Download dependencies before interrupting the running application.
    with tempfile.TemporaryDirectory(prefix="dvs-wheels-") as wheel_dir:
        run("python3","-m","pip","download","--dest",wheel_dir,"-r",str(ROOT/"requirements.txt"))
        targets=[pathlib.Path("/")/p.relative_to(ROOT/"payload") for p in files()]+[BOOT,VENV]
        directory=pathlib.Path("/var/backups/dvs")/(time.strftime("%Y%m%d-%H%M%S")+"-"+str(os.getpid()))
        state={"enabled":subprocess.run(["systemctl","is-enabled","--quiet",UNIT]).returncode==0,
               "active":subprocess.run(["systemctl","is-active","--quiet",UNIT]).returncode==0}
        run("systemctl","stop",UNIT) if state["active"] else None
        try: backup(targets,directory)
        except BaseException:
            if state["active"]: run("systemctl","start",UNIT)
            raise
        (directory/"service.json").write_text(json.dumps(state))
        print("Backup:",directory,flush=True)
        try:
            for p in files():
                target=pathlib.Path("/")/p.relative_to(ROOT/"payload")
                target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,target)
            if VENV.exists(): shutil.rmtree(VENV)
            run("python3","-m","venv","--system-site-packages",str(VENV))
            run(str(VENV/"bin/python"),"-m","pip","install","--no-index","--find-links",wheel_dir,"-r",str(ROOT/"requirements.txt"))
            run(str(VENV/"bin/python"),"-c","import numpy, PyQt5, smbus2, websockets")
            current=BOOT.read_text()
            # Keep all existing platform/display settings intact.
            BOOT.write_text(configure_boot(current))
            run("usermod","-aG","video,render,i2c","philip")
            run("chown","-R","philip:philip","/home/philip/dvs_raw2_production","/home/philip/dvs_web_app")
            run("depmod","-a",KERNEL); run("systemctl","daemon-reload"); run("systemctl","enable",UNIT)
        except BaseException:
            print("Install failed; restoring backed-up files.",file=sys.stderr)
            restore_system(directory)
            raise
    print("Installed. Reboot manually: sudo reboot")
    print("Restore: sudo ./install.sh --restore",directory)
    print("Log in to the philip desktop session after reboot (Wayland + Xwayland required).")

if __name__=="__main__":
    try: main()
    except Exception as exc: print("ERROR:",exc,file=sys.stderr); sys.exit(1)
