import os, glob, time

def cleanup_old_zips(downloads_dir: str, keep_last:int=100, days:int=30):
    os.makedirs(downloads_dir, exist_ok=True)
    zips = sorted(glob.glob(os.path.join(downloads_dir, "*.zip")), key=os.path.getmtime, reverse=True)
    cutoff = time.time() - days*24*3600
    # Mantener N más recientes; del resto solo borrar si son viejos
    for p in zips[keep_last:]:
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
        except Exception:
            pass
