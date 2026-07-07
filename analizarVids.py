# Herramienta para analizar videos e imágenes usando ffprobe y exiftool
# Permite obtener información detallada sobre el formato, codecs, metadata, etc.

import subprocess
import json
from pathlib import Path


def analizar_video(ruta_video):
    ruta_video = Path(ruta_video)

    if not ruta_video.exists():
        print(f"El archivo '{ruta_video}' no existe.")
        return None

    comando = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(ruta_video)
    ]

    resultado = subprocess.run(comando, capture_output=True, text=True)

    if resultado.returncode != 0:
        print("Error ejecutando ffprobe")
        return None

    data = json.loads(resultado.stdout)

    print("\n==============================")
    print(f"Archivo: {ruta_video.name}")
    print("==============================\n")

    # --- FORMATO GENERAL ---
    formato = data.get("format", {})
    print(">> INFORMACIÓN DEL CONTENEDOR")
    print(f"Formato: {formato.get('format_name')}")
    print(f"Duración: {formato.get('duration')} segundos")
    print(f"Tamaño: {round(int(formato.get('size', 0)) / (1024*1024), 2)} MB")
    print(f"Bitrate total: {formato.get('bit_rate')} bps")

    # --- STREAMS ---
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            print("\n>> STREAM DE VIDEO")
            print(f"Codec: {stream.get('codec_name')}")
            print(f"Resolución: {stream.get('width')}x{stream.get('height')}")
            print(f"FPS: {stream.get('r_frame_rate')}")
            print(f"Bitrate: {stream.get('bit_rate')}")
            print(f"Perfil: {stream.get('profile')}")

        if stream.get("codec_type") == "audio":
            print("\n>> STREAM DE AUDIO")
            print(f"Codec: {stream.get('codec_name')}")
            print(f"Canales: {stream.get('channels')}")
            print(f"Bitrate: {stream.get('bit_rate')}")

    # --- METADATA ---
    print("\n>> METADATA")
    metadata = formato.get("tags", {})
    if metadata:
        for k, v in metadata.items():
            print(f"{k}: {v}")
    else:
        print("No contiene metadata.")

    return data

def analizar_foto(ruta_imagen):
    ruta_imagen = Path(ruta_imagen)

    if not ruta_imagen.exists():
        print(f"El archivo '{ruta_imagen}' no existe.")
        return None

    comando = [
        "exiftool",
        "-j",  # salida en json
        str(ruta_imagen)
    ]

    resultado = subprocess.run(comando, capture_output=True, text=True)

    if resultado.returncode != 0:
        print("Error ejecutando exiftool")
        return None

    data = json.loads(resultado.stdout)[0]

    print("\n==============================")
    print(f"Imagen: {ruta_imagen.name}")
    print("==============================\n")

    print(">> METADATA EXIF COMPLETA\n")

    for k, v in data.items():
        print(f"{k}: {v}")

    return data

#analizar_video("Destino/20240420_185422.mp4")
analizar_foto("Origen/07.jpg")

