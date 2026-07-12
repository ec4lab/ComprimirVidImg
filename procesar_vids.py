__version__ = "1.0.0"

import subprocess
from pathlib import Path
import shutil
import time
from datetime import datetime
import re
import json

# ================= CONFIGURACIÓN =================
## Carpetas
ORIGEN = Path("Origen")
DESTINO = Path("Destino")

## Coordenadas GPS para agregar a los archivos que no las tengan
COORDS = ("41.980862 S","50.932826 W") # Latitud y Longitud - Atlántico Sur
REFS = ("S","W") # Referencia de COORDS


## Archivos a eliminar o ignorar sin preguntar
ELIMINAR = ["thumbs.db", "desktop.ini", "*.part"]
IGNORAR = ["origen.jpg", "instrucciones.png"]

## Borrar originales después de procesar
BORRAR_ORIGINALES = False

## Logs
ESTADISTICAS = "estadisticas.json"


## Calidades de conversión
Q_VIDEO = "25" # Calidad constante: 0 (sin pérdida) a 51 (muy comprimido), recomendado 24 - 25
P_VIDEO = "slow" # Preset de compresión: ultrafast, superfast, veryfast, faster, fast, medium (default), slow, slower, veryslow
Q_IMAGEN = "3" # Calidad de imagen: 1 (mejor calidad) a 31 (peor calidad), recomendado 3
W_IMAGEN = "0" # Ancho máximo de las imágenes, el alto se ajusta automáticamente para mantener la proporción, "0" para mantener original
# ==========================================



inicio_total = time.time()
total_procesos = 0
archivos_procesados = 0
bytes_entrada = 0
bytes_salida = 0

try:
    with open(ESTADISTICAS, "r") as f:
        estadisticas = json.load(f)
        total_procesos = int(estadisticas['Total de procesos'])
        archivos_procesados = int(estadisticas['archivos'])
        bytes_entrada = float(estadisticas['entrada_MB'])*1024*1024
        bytes_salida = float(estadisticas['salida_MB'])*1024*1024
except FileNotFoundError:
    print("No se encontró el archivo de estadísticas.")
except json.JSONDecodeError:
    print("Error al decodificar el archivo de estadísticas.")

# ==========================================

def ejecutar(cmd):
    # Ejecuta un comando en la terminal y devuelve el resultado.
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def size(path):
    # Devuelve el tamaño de un archivo en bytes, o 0 si el archivo no existe.
    return path.stat().st_size if path.exists() else 0

# ==========================================
# DETECTORES
# ==========================================

def es_video(path):
    # Devuelve True si el archivo es un video, según su extensión.
    return path.suffix.lower() in [".mp4", ".mov", ".mkv", ".avi", ".m4v",".mts", ".m2ts",".wmv",".3gp"]

def es_imagen(path):
    # Devuelve True si el archivo es una imagen, según su extensión.
    return path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp",".heic"]

def destino_libre(destino):
    # La usa para evitar sobrescribir archivos en la carpeta de destino.
    # Si el archivo destino ya existe, agrega un sufijo numérico al 
    # nombre del archivo hasta encontrar uno que no exista.
    if not destino.exists():
        return destino

    base = destino.stem
    ext = destino.suffix
    carpeta = destino.parent

    i = 1

    while True:

        nuevo = carpeta / f"{base}({i}){ext}"

        if not nuevo.exists():
            return nuevo

        i += 1

# ==========================================
# ESTADÍSTICAS
# ==========================================

def guardar_estadisticas():
    datos = {
        "Ultima ejecución": str(datetime.now()),
        "Total de procesos": total_procesos+1,
        "archivos": archivos_procesados,
        "entrada_MB": round(bytes_entrada/1024/1024,2),
        "salida_MB": round(bytes_salida/1024/1024,2),
        "ahorro_MB": round(
            (bytes_entrada-bytes_salida)
            /1024/1024,
            2
        )
    }

    with open(
        ESTADISTICAS,
        "w",
        encoding="utf8"
    ) as f:

        json.dump(
            datos,
            f,
            indent=4,
            ensure_ascii=False
        )

# ==========================================
# METADATA FECHA
# ==========================================

# Analizar el nombre del archivo a ver si indica la fecha de captura
def fecha_nombre(path):
    patrones = [
        r"(\d{8})_(\d{6})", # 20241223_205832  (YYYYMMDD_HHMMSS)
        r"(\d{8})-(\d{6})"  # 20241223-205832 (YYYYMMDD-HHMMSS)
    ]

    nombre = path.stem

    for patron in patrones:
        m = re.search(patron, nombre)
        if m:
            fecha = m.group(1) # si nombre = "20241223_205832", fecha = "20241223"
            hora = m.group(2)  # si nombre = "20241223_205832", hora = "205832"

            return (
                f"{fecha[0:4]}:"
                f"{fecha[4:6]}:"
                f"{fecha[6:8]} "
                f"{hora[0:2]}:"
                f"{hora[2:4]}:"
                f"{hora[4:6]}"
            )
    
    patrones2 = [
        r"(\d{2})-(\d{2})-(\d{2})_(\d{6})",  # 24-08-06_1937 (DD-MM-YY_HHMM)
    ]
    for patron in patrones2:
        m = re.search(patron, nombre)
        if m:
            dia = m.group(1) # si nombre = "24-08-06_1937", dia = "24"
            mes = m.group(2) # si nombre = "24-08-06_1937", mes = "08"
            anio = m.group(3) # si nombre = "24-08-06_1937", anio = "06"
            hora  = m.group(4)  # si nombre = "24-08-06_1937", hora = "1937"

            return (
                f"{anio}:"
                f"{mes}:"
                f"{dia} "
                f"{hora[0:2]}:"
                f"{hora[2:4]}:"
                f"{00}"
            )

    return None

# Obtener la fecha de captura a partir de las metadata del archivo, se buscan varias etiquetas y se elige la más antigua
def obtener_fecha(path):

    tags = [
        "DateTimeOriginal",
        "CreateDate",
        "TrackCreateDate",
        "MediaCreateDate",
        "ModifyDate",
        "TrackModifyDate",
        "MediaModifyDate",
        "CreationDate",
        "FileModifyDate"
    ]

    candidatas = []

    for tag in tags:
        r = ejecutar([
            "exiftool",
            f"-{tag}",
            "-s3",
            str(path)
        ])

        fecha = r.stdout.strip()

        if not fecha:
            continue

        fecha = fecha[:19]
        try:
            dt = datetime.strptime(
                fecha,
                "%Y:%m:%d %H:%M:%S"
            )
            candidatas.append(dt)
        except:
            pass

    fecha_archivo = fecha_nombre(path)
    if fecha_archivo:
        try:
            candidatas.append(
                datetime.strptime(
                    fecha_archivo,
                    "%Y:%m:%d %H:%M:%S"
                )
            )
        except:
            pass

    if not candidatas:
        return None
    return min(candidatas).strftime(
        "%Y:%m:%d %H:%M:%S"
    )

def insertar_fecha(path, fecha):

    if not fecha:
        return

    ejecutar([
        "exiftool",
        "-overwrite_original",
        f"-CreateDate={fecha}",
        f"-ModifyDate={fecha}",
        f"-TrackCreateDate={fecha}",
        f"-TrackModifyDate={fecha}",
        f"-MediaCreateDate={fecha}",
        f"-MediaModifyDate={fecha}",
        f"-DateTimeOriginal={fecha}",
        str(path)
    ])

# ==========================================
# METADATA GPS
# ==========================================
def obtener_gps(path):
    r = ejecutar([
        "exiftool",
        "-GPSLatitude",
        "-GPSLatitudeRef",
        "-GPSLongitude",
        "-GPSLongitudeRef",
        "-GPSAltitude",
        "-GPSAltitudeRef",
        "-s3", # Muestra solo el valor de la etiqueta, sin el nombre de la etiqueta ni el signo de interrogación si no existe.
        str(path)
    ])

    datos = r.stdout.splitlines()

    if len(datos) >= 6:
        return (
            datos[0].strip(),
            datos[1].strip(),
            datos[2].strip(),
            datos[3].strip(),
            datos[4].strip(),
            datos[5].strip()
        )
    return None

def escribir_gps(path, gps):
    lat,refl,lon,reflo,alt,refa = gps
    ejecutar([
        "exiftool",
        "-overwrite_original",
        f"-GPSLatitude={lat}",
        f"-GPSLatitudeRef={refl}",
        f"-GPSLongitude={lon}",
        f"-GPSLongitudeRef={reflo}",
        f"-GPSAltitude={alt}",
        f"-GPSAltitudeRef={refa}",
        str(path)
    ])
    
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
# OTRA METADATA
# ==========================================

def obtener_metadata(path):
    r = ejecutar([
        "exiftool",
        "-Orientation",
        "-s3", # Muestra solo el valor de la etiqueta, sin el nombre de la etiqueta ni el signo de interrogación si no existe.
        str(path)
    ])

    datos = r.stdout.splitlines()

    if len(datos) >= 1:
        return (
            datos[0].strip()            
        )
    return None

def escribir_metadata(path, metadata):
    rot = metadata
    ejecutar([
        "exiftool",
        "-overwrite_original",
        f"-Orientation={rot}"
    ])


# ==========================================
# VIDEO
# ==========================================

def comprimir_video(origen, destino):
    filtros = []

    # Comando a ejecutar
    cmd = [
        "ffmpeg", "-y",
        "-i", str(origen),
        *filtros,
        # Codecs, calidad de video y presets configurados
        "-c:v", "libx264", # Codec de video H.264
        "-preset", P_VIDEO,
        "-crf", Q_VIDEO,
        # Ajuste para compatibilidad con Memories y otros reproductores
        "-profile:v", "main", #""high",
        "-level", "4.0",
        "-pix_fmt", "yuv420p",
        # Codec y calidad de audio
        "-c:a", "aac", # Codec de audio AAC
        "-b:a", "160k", # Bitrate de audio 160 kbps
        # Ajuste para que el video se pueda reproducir antes de descargarse completamente
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

    filtros = []

    if not W_IMAGEN=="0": 
        filtros = ["-vf", f"scale={W_IMAGEN}:-1"]

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

    # Verifica si el video original tiene GPS
    gps = obtener_gps(path)
    if gps:
        # Si lo tiene lo escribe en el video convertido
        escribir_gps(temp, gps)
    else:
        # si no tiene GPS, agrega las coordenadas predeterminadas
        agregar_gps(temp)

    # Busca fecha y copia al nuevo archivo
    fecha = obtener_fecha(path) # Busca en metadatos y nombre del archivo, elije la fecha más antigua
    insertar_fecha(temp, fecha)

    # Copia la metadata de rotación al nuevo archivo
    # En el futuro se puede agregar más metadata, como título, autor, etc.
    metadata = obtener_metadata(path)
    if metadata:
        escribir_metadata(temp, metadata)

    # Mover el archivo temporal a la carpeta de destino
    destino = (DESTINO / rel).with_suffix(".mp4")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino = destino_libre(destino)
    
    shutil.move(str(temp), str(destino))

    bytes_salida += size(destino)
    archivos_procesados += 1

    # Borrado de archivos originales después de procesar
    # si es que ya existen en el destino, y tiene tamaño mayor a 0
    if destino.exists() and destino.stat().st_size > 0:
        if BORRAR_ORIGINALES:
            path.unlink()
    else:
        print(f"❌ ERROR: no se encontró {destino}")

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

    # Verifica si el video original tiene GPS
    gps = obtener_gps(path)
    if gps:
        # Si lo tiene lo escribe en el video convertido
        escribir_gps(temp, gps)
    else:
        # si no tiene GPS, agrega las coordenadas predeterminadas
        agregar_gps(temp)

    fecha = obtener_fecha(path)
    insertar_fecha(temp, fecha)

    # Copia la metadata de rotación al nuevo archivo
    # En el futuro se puede agregar más metadata, como título, autor, etc.
    metadata = obtener_metadata(path)
    if metadata:
        escribir_metadata(temp, metadata)

    # Mover el archivo temporal a la carpeta de destino
    destino = (DESTINO / rel).with_suffix(".jpg")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino = destino_libre(destino)
    shutil.move(str(temp), str(destino))

    bytes_salida += size(destino)
    archivos_procesados += 1

    # Borrado de archivos originales después de procesar
    # si es que ya existen en el destino, y tiene tamaño mayor a 0
    if destino.exists() and destino.stat().st_size > 0:
        if BORRAR_ORIGINALES:
            path.unlink()
    else:
        print(f"❌ ERROR: no se encontró {destino}")

    print(f"OK → {destino}")

# ==========================================
# RECORRER
# ==========================================

def recorrer():
    for path in ORIGEN.rglob("*"): # Recorre recursivamente todos los archivos en la carpeta de origen y sus subcarpetas.

        if not path.is_file():
            continue

        nombre = path.name.lower()

        if nombre in ELIMINAR:
            print(f" {path}, eliminado")
            path.unlink()
            continue

        if nombre in IGNORAR:
            print(f" {path}, ignorado")
            continue

        if es_video(path):
            procesar_video(path)
        elif es_imagen(path):
            procesar_imagen(path)

# ==========================================
# LIMPIEZA
# ==========================================

def limpiar_carpetas_vacias(base):
    # Eliminar carpetas vacías, recursivamente.
    # Se ordenan de mayor a menor profundidad para eliminar primero las subcarpetas y luego las padres.
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

    print("\n Historial")
    print(f"Archivos: {archivos_procesados}")
    print(f"Entrada: {human(bytes_entrada)}")
    print(f"Salida:  {human(bytes_salida)}")
    print(f"Ahorro:  {human(bytes_entrada - bytes_salida)}")
    print(f"Tiempo:  {dur/60:.2f} min")


# ==========================================
# Secuencia principal
# ==========================================

if __name__ == "__main__":

    recorrer()
        # Procesa todos los archivos de video e imagen en la carpeta de origen y los guarda en la carpeta de destino.
    limpiar_carpetas_vacias(ORIGEN)
        # Borra las carpetas vacías que hayan quedado en el origen después de procesar los archivos
    guardar_estadisticas()
        # Guarda un resumen de las estadísticas del proceso en un archivo JSON
    resumen()
        # Imprime en consola un resumen del proceso

#Salir = input("\nPresione Enter para salir...")