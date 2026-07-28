import subprocess
import logging
import os

def create_immutable_snapshot(subvolume_path="/mnt/core", snapshot_dest="/mnt/snapshots/core_snap"):
    """Ejecuta una orden real al kernel para generar un subvolumen snapshot de solo lectura en btrfs."""
    try:
        if not os.path.exists(subvolume_path):
            logging.warning(f"El subvolumen {subvolume_path} no existe en este host local. Omitiendo ejecución real de btrfs.")
            return False
        
        cmd = ["btrfs", "subvolume", "snapshot", "-r", subvolume_path, f"{snapshot_dest}_frozen"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logging.info(f"Snapshot Btrfs creado exitosamente: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Fallo del kernel al crear snapshot btrfs: {e.stderr.strip()}")
        return False
    except Exception as e:
        logging.error(f"Error inesperado en gestión Btrfs: {str(e)}")
        return False

def enforce_readonly_filesystem(mount_point="/app/data"):
    """Remonta el directorio perimetral en modo read-only mediante llamadas al sistema (mount)."""
    try:
        cmd = ["mount", "-o", "remount,ro", mount_point]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"Punto de montaje {mount_point} asegurado en modo Read-Only estricto.")
        return True
    except Exception as e:
        logging.error(f"No se pudo asegurar el modo read-only en el almacenamiento: {str(e)}")
        return False
