import subprocess
import logging

def create_immutable_snapshot(subvolume_path="/mnt/core", snapshot_dest="/mnt/snapshots/core_snap"):
    try:
        cmd = ["btrfs", "subvolume", "snapshot", "-r", subvolume_path, f"{snapshot_dest}_frozen"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logging.info(f"Snapshot Btrfs creado: {result.stdout.strip()}")
        return True
    except Exception as e:
        logging.error(f"Error en snapshot btrfs: {str(e)}")
        return False

def enforce_readonly_filesystem(mount_point="/app/data"):
    try:
        subprocess.run(["mount", "-o", "remount,ro", mount_point], check=True, capture_output=True)
        logging.info(f"Filesystem en {mount_point} asegurado en Read-Only.")
        return True
    except Exception as e:
        logging.error(f"Error aplicando read-only: {str(e)}")
        return False
