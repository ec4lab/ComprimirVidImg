# No necesita venv

import subprocess
from pathlib import Path
import shutil
import time
from datetime import datetime

# ================= CONFIGURACIÓN =================
## Carpetas
ORIGEN = Path("Origen")
DESTINO = Path("Destino")

## Coordenadas GPS para agregar a los archivos que no las tengan
COORDS = ("41.980862 S","50.932826 W") # Latitud y Longitud - Atlántico Sur
REFS = ("S","W") # Referencia de COORDS
#"31.252668 S","61.491749 W"  # Rafaela

## Archivos a eliminar o ignorar sin preguntar
ELIMINAR = ["thumbs.db", "desktop.ini", "*.part"]
IGNORAR = ["origen.jpg", "instrucciones.png"]

## Logs
LOG_FILE = "procesamiento.log"

## Calidades de conversión
Q_VIDEO = "25" # Calidad constante: 0 (sin pérdida) a 51 (muy comprimido), recomendado 24 - 25
Q_IMAGEN = "3" # Calidad de imagen: 1 (mejor calidad) a 31 (peor calidad), recomendado 3

# ==========================================

inicio_total = time.time()
archivos_procesados = 0
bytes_entrada = 0
bytes_salida = 0

# ==========================================

def ejecutar(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def size(path):
    return path.stat().st_size if path.exists() else 0

# ==========================================
# DETECTORES
# ==========================================

def es_video(path):
    return path.suffix.lower() in [".mp4", ".mov", ".mkv", ".avi", ".m4v",".mts", ".m2ts"]

def es_imagen(path):
    return path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]

# ==========================================
# METADATA
# ==========================================

def copiar_metadata(origen, destino):
    ejecutar(["exiftool", "-overwrite_original", "-TagsFromFile", str(origen), str(destino)])

def tiene_gps(path):
    r = ejecutar(["exiftool", "-GPSLatitude", str(path)])
    return r.stdout.strip() != ""

def agregar_gps(path):
    ejecutar([
        "exiftool",
        "-overwrite_original",
        f"-GPSLatitude={COORDS[0]}",
        f"-GPSLongitude={COORDS[1]}",
        f"-GPSLatitudeRef={REFS[0]}",
        f"-GPSLongitudeRef={REFS[1]}",
        str(path)
    ])

# ==========================================
# FECHA
# ==========================================

def tiene_fecha(path):
    r = ejecutar(["exiftool", "-DateTimeOriginal", "-creation_time", str(path)])
    return r.stdout.strip() != ""

def obtener_fecha(path):
    r = ejecutar(["exiftool", "-FileModifyDate", "-s3", str(path)])
    return r.stdout.strip()

def insertar_fecha(path, fecha):
    ejecutar([
        "exiftool",
        "-overwrite_original",
        f"-DateTimeOriginal={fecha}",
        f"-CreateDate={fecha}",
        f"-creation_time={fecha}",
        str(path)
    ])

# ==========================================
# ROTACIÓN
# ==========================================

def necesita_rotacion(path):

    r = ejecutar(["exiftool", "-Orientation", "-s3", str(path)])
    orient = r.stdout.strip()

    if orient == "Rotate 270 CW":
        return "270"

    if orient == "Rotate 90 CW":
        return "90"

    return None

# ==========================================
# VIDEO
# ==========================================

def comprimir_video(origen, destino):
    filtros = []

    rot = necesita_rotacion(origen)
    if rot == "90":
        filtros = ["-vf", "transpose=2"]
    elif rot == "270":
        filtros = ["-vf", "transpose=1"]

    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(origen),
        *filtros,

        "-c:v", "libx264", # Codec de video H.264
        "-preset", "slow", # Preset de compresión: ultrafast, superfast, veryfast, faster, fast, medium (default), slow, slower, veryslow
        "-crf", Q_VIDEO,

        "-profile:v", "high",
        "-level", "4.0",
        "-pix_fmt", "yuv420p",

        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",

        "-c:a", "aac", # Codec de audio AAC
        "-b:a", "160k", # Bitrate de audio 160 kbps

        "-movflags", "+faststart",

        str(destino)
    ]


    return ejecutar(cmd).returncode == 0

def validar_video(path):
    r = ejecutar(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"])
    return r.returncode == 0

# ==========================================
# IMAGEN
# ==========================================

def comprimir_imagen(origen, destino):
    filtros = []

    if necesita_rotacion(origen):
        filtros = ["-vf", "transpose=2"]

    cmd = [
        "ffmpeg", "-y",
        "-i", str(origen),
        *filtros,
        "-q:v", Q_IMAGEN,
        str(destino)
    ]
    return ejecutar(cmd).returncode == 0

# ==========================================
# PROCESAMIENTO
# ==========================================

def procesar_video(path):
    global archivos_procesados, bytes_entrada, bytes_salida

    rel = path.relative_to(ORIGEN)
    temp = path.with_suffix(".tmp.mp4")

    print(f"\n {path}")
    bytes_entrada += size(path)

    if not comprimir_video(path, temp):
        print("❌ Error compresión")
        return

    if not validar_video(temp):
        print("❌ Video corrupto")
        temp.unlink(missing_ok=True)
        return

    copiar_metadata(path, temp)

    if not tiene_gps(path):
        agregar_gps(temp)

    if not tiene_fecha(path):
        fecha = obtener_fecha(path)
        insertar_fecha(temp, fecha)

    destino = (DESTINO / rel).with_suffix(".mp4")
    destino.parent.mkdir(parents=True, exist_ok=True)

    shutil.move(str(temp), str(destino))

    bytes_salida += size(destino)
    archivos_procesados += 1

    path.unlink()

    print(f"OK → {destino}")

def procesar_imagen(path):
    global archivos_procesados, bytes_entrada, bytes_salida

    rel = path.relative_to(ORIGEN)
    temp = path.with_suffix(".tmp.jpg")

    print(f"\n {path}")

    bytes_entrada += size(path)

    if not comprimir_imagen(path, temp):
        print("❌ Error compresión")
        return

    copiar_metadata(path, temp)

    if not tiene_gps(path):
        agregar_gps(temp)

    if not tiene_fecha(path):
        fecha = obtener_fecha(path)
        insertar_fecha(temp, fecha)

    destino = (DESTINO / rel).with_suffix(".jpg")
    destino.parent.mkdir(parents=True, exist_ok=True)

    shutil.move(str(temp), str(destino))

    bytes_salida += size(destino)
    archivos_procesados += 1

    path.unlink()

    print(f"OK → {destino}")

# ==========================================
# RECORRER
# ==========================================

def recorrer():
    for path in ORIGEN.rglob("*"):

        if not path.is_file():
            continue

        nombre = path.name.lower()

        if nombre in ELIMINAR:
            print(f" {path}")
            path.unlink()
            continue

        if nombre in IGNORAR:
            print(f" {path}")
            continue

        if es_video(path):
            procesar_video(path)
        elif es_imagen(path):
            procesar_imagen(path)

# ==========================================
# LIMPIEZA
# ==========================================

def limpiar_carpetas_vacias(base):
    for carpeta in sorted(base.rglob("*"), reverse=True):
        if carpeta.is_dir():
            if not any(carpeta.iterdir()):
                carpeta.rmdir()

# ==========================================
# RESUMEN
# ==========================================

def human(n):
    for unit in ['B','KB','MB','GB']:
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"

def resumen():
    dur = time.time() - inicio_total

    print("\n RESUMEN")
    print(f"Archivos: {archivos_procesados}")
    print(f"Entrada: {human(bytes_entrada)}")
    print(f"Salida:  {human(bytes_salida)}")
    print(f"Ahorro:  {human(bytes_entrada - bytes_salida)}")
    print(f"Tiempo:  {dur/60:.2f} min")

    with open(LOG_FILE, "a") as f:
        f.write(f"\n[{datetime.now()}]\n")
        f.write(f"Archivos: {archivos_procesados}\n")
        f.write(f"Entrada: {bytes_entrada}\n")
        f.write(f"Salida: {bytes_salida}\n")
        f.write(f"Tiempo: {dur:.2f}s\n")

# ==========================================

if __name__ == "__main__":
    recorrer()
    limpiar_carpetas_vacias(ORIGEN)
    resumen()