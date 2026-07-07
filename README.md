# Comprimir Videos e Imágenes

El propósito de este programa es comprimir recursivamente los archivos de video e imágenes de una carpeta, para almacenaje a largo plazo. Reduciendo todo lo posible el tamaño sin sacrificar demasiada calidad.

Todas las imágenes serán convertidas a JPG y los videos a MP4.

Luego de los chequeos de conversión, se eliminan los archivos originales. (configurable)

## Instalación

```bash
gitclone https://github.com/ec4lab/ComprimirVidImg.git
```

No requiere `venv` ni librerías adicionales, solo tener instalado en el sistema `ffmpeg` y `exiftool`

en **Ubuntu**

```bash
sudo apt install ffmpeg
sudo apt install libimage-exiftool-perl
```

En **windows** ver como instalar [ffmpeg](https://github.com/ec4lab/windows#instalar-ffmpeg-en-windows-11) y [exiftool](https://github.com/ec4lab/windows#instalar-exiftool-en-windows-11).

## Configuración

Antes de ejecutar [procesar_vids.py](procesar_vids.py)

Indicar las carpetas de Origen y Destino:

```python
ORIGEN = Path("Origen")
DESTINO = Path("Destino")
```

Ajustar las calidades de salida con:

```python
## Calidades de conversión
Q_VIDEO = "25" # CRF 0 (sin pérdida) a 51 (muy comprimido), recomendado 24 - 25
P_VIDEO = "slow" # Preset de compresión
Q_IMAGEN = "3" # Calidad de imagen: 1 (mejor calidad) a 31 (peor calidad), recomendado 3
```

Indicar archivos a ignorar o a eliminar directamente

```python
ELIMINAR = ["thumbs.db", "desktop.ini", "*.part"]
IGNORAR = ["origen.jpg", "instrucciones.png"]
```

Permitir el borrado de los archivos originales

```python
BORRAR_ORIGINALES = False
```

>[!WARNING]
>Se recomienda `NO` borrar archivos originales hasta estar absolutamente seguros de que el programa funciona satisfactoriamente

## Flujo de trabajo

1. Analiza directorio de origen.
2. Según sea video o imagen comprime sobre un `.tmp`
3. Añade metadata
4. Mueve a la carpeta de destino (copia estructura de directorios)  
4.1 Si en el destino ya existe el archivo -> renombra
5. Si eliminar originales activado  
5.1. Si el archivo ya esta en destino y es > 0  
5.1.1 Elimina Original
6. Datos acumulados en `estadisticas.json`

## Metadata

Por cuestiones de compatibilidad solo se copia la metadata declarada explícitamente:

Geolocalización: Latitud, Longitud y altura s.n.m. Cuando la imagen no disponga de geolocalización, se grabará un punto arbitrario en el atlántico sur, esto es útil en la función `Mapa` de la aplicación `Memories`de NextCloud.

Fecha: se recuperan los tags: `DateTimeOriginal`,`CreateDate`,`TrackCreateDate`,`MediaCreateDate`,`ModifyDate`,`TrackModifyDate`,`MediaModifyDate`,`CreationDate`,`FileModifyDate` y también se procesan patrones comunes en el nombre de las imágenes, luego se graba la más antigua.

Otra metadata:
Se deben editar las funciones:

```python
obtener_metadata(path)
escribir_metadata(path, metadata)
```

En este caso solo se recupera la Orientación

## Referencias

### Calidades y Formatos en los videos

Se graba un video con el celular y se envía por WhatsApp, de manera normal y en HD, para investigar calidades, formatos y metadata:
Utilizando [analizarVids.py](analizarVids.py) se estudian las salidas.

La lectura de parámetros y metadata la hacemos con `ffprobe`

||Video Original|Video WhatsApp|Video WhatsAppHD|
|---|---|---|---|
|**CONTENEDOR**||||
|Formato|mov,mp4,m4a,3gp,3g2,mj2|mov,mp4,m4a,3gp,3g2,mj2|mov,mp4,m4a,3gp,3g2,mj2|
|Duración|30.363812 segundos|30.363813 segundos|30.363813 segundos|
|Tamaño|74.43 MB|6.63 MB|12.24 MB|
|Bitrate total|20563088 bps|1830461 bps|3380966 bps|

<details>
<summary>continúa...</summary>

|||||
|---|---|---|---|
|**AUDIO**||||
|Codec|aac|aac|aac|
|Canales|2|2|2|
|Bitrate|320023|319931|319931|
|**VIDEO**||||
|Codec|h264|h264|h264|
|Resolución|1920x1080|848x478|1280x720|
|FPS|46052|46052|46052|
|Bitrate|20.034.808|1.508.295|3.059.745|
|Perfil|High|High|High|
|**METADATA**||||
|major_brand|mp42|mp42|mp42|
|minor_version|0|0|0|
|compatible_brands|isommp42|mp42isom|mp42isom|
|creation_time|2026-03-02T02:0:10.000000Z|-|-|
|location|-38.2661-069.4865/|-|-|
|location-eng|-38.2661-069.4865/|-|-|
|com.android.version|15|-|-|
|com.android.manufacturer|Xiaomi|-|-|
|com.android.model|24117RN76G|-|-|
|com.xiaomi.normal_video|30|-|-|

</details>
<br>

Se puede ver que el mayor cambio se da en el Bitrate y en la resolución, haciendo que la compresión sea de mas del 80%, por otro lado tenemos que tener en cuenta que toda la metadata es removida, asi que es necesario reinsertar luego de la compresión.

### Conceptos

#### Bitrate vs CRF

Lo que más comprime el video es el Bitrate, por ejemplo de 20Mbps a 3Mbps. Esto le dice al codec cuanto se quiere que pese cada segundo de video, y la compresión se hace a peso constante,(ajustando la calidad) lo que hace muy predecible el tamaño de archivo final, esto es importante cuando, por ejemplo, se realiza un streaming, pero tiene la desventaja de que en una escena compleja puede que se pierda mucha calidad, en cambio, si la escena es liviana, se podría estar desperdiciando espacio.

Por otro lado existe el sistema de compresión CRF (Constant Rate Factor), que trabaja a calidad constante, por lo que ajusta el Bitrate según lo necesite, dando una calidad uniforme y una compresión más eficiente, aunque no es tan predecible el tamaño de archivo final, para este caso, en donde se busca almacenar a largo plazo consideramos que CRF es mejor que un Bitrate constante.

#### H.264 vs H.265

Es el tipo de codec utilizado para la compresión:

||H.264 (AVC)|H.265 (HEVC)|
|---|---|---|
|Compatibilidad|Alta|Solo en equipos más modernos|
|Eficiencia|Buena|25–40% más eficiente|
|Estándar|Universal|Buena, no universal en hardware viejo|
|Velocidad de codificación|Alta|Baja|
|Consumo CPU para reproducir|Normal|Alto|

Para este proyecto se decidió utilizar `H.264`, previendo a futuro cambiar a H.265. ya que por el momento no todos los navegadores soportan de manera correcta h.265.

#### Perfil (Baseline, Main, High)

Son “niveles de complejidad” del codec.

|Baseline|Main|High|
|---|---|---|
|Muy compatible||Mejor compresión|
|Baja eficiencia|Balance intermedio|Más eficiente|
|Pensado para móviles viejos||Usa herramientas más avanzadas|

Después de varias pruebas el perfil `High` resultó compatible con todos los dispositivos.

#### Presets (ultrafast,medium,slow,veryslow)

Esto NO cambia la calidad objetivo,Cambia cuánto tiempo el encoder “piensa”.

|ultrafast|medium|slow|veryslow|
|---|---|---|---|
|rápido|balance|más tiempo|mucho más lento|
|archivo más grande||mejor compresión|aún más optimizado|

Por ahora se trabaja con `slow`, queda en un futuro ver si vale la pena ultraslow

Respecto a la metadata, hay algunas cosas que no son relevantes para conservar, pero a modo de crear un archivo para almacenaje a largo plazo, y al ser poco significativo sobre el peso final del archivo, se decide conservar el total de la metadata.

|Resumen de compresión de video||
|---|---|
|Audio|mantener|
|Codec|H264|
|Resolución|1920x1080|
|FPS|Mantener|
|Bitrate|No|
|CRF|25 (se prioriza compresión sobre calidad)|
|Perfil|High|
|Preset|slow|

Se pueden editar los parámetros de compresión en:

```python
def comprimir_video(origen, destino):
    filtros = []

    cmd = [
        "ffmpeg", "-y",
        "-i", str(origen),
        *filtros,
        "-c:v", "libx264", # Codec de video H.264
        "-preset", P_VIDEO,
        "-crf", Q_VIDEO,
        "-profile:v", "main", #""high",
        "-level", "4.0",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", # Codec de audio AAC
        "-b:a", "160k", # Bitrate de audio 160 kbps
        "-movflags", "+faststart",
        str(destino)
    ]

    return ejecutar(cmd).returncode == 0
```

>[!NOTE]
> Los parámetros fueron optimizados para la reproducción en `memories` de Nextcloud, algunos reproductores pueden ser un poco quisquillosos con los formato y etiquetados.

### Calidades y Formatos en las imágenes

Se toma una foto con el celular y se envía WhatsApp, de manera normal y en HD, y se analizan formatos y metadata:
Utilizando [analizarVids.py](analizarVids.py) se comparan las salidas.

En cuanto a las imágenes la metadata es mucha más, para esto debemos utilizar `exiftool`

||Imagen Original|Imagen WhatsApp|Imagen WhatsAppHD|
|---|---|---|---|
|**METADATA EXIF**||||
|SourceFile|Original.jpg|ImagenWhatsApp.jpeg|ImagenWhatsAppHD.jpg|
|ExifToolVersion|12.76|12.76|12.76|
|FileName|Original.jpg|ImagenWhatsApp.jpeg|ImagenWhatsAppHD.jpg|
|Directory|-|-|-|
|FileSize|2.1 MB|136 kB|587 kB|
|FileModifyDate|2026:3:01 22:58:51-03:0|2026:3:01 23:5:32-03:0|2026:3:01 23:18:45-03|
|FileAccessDate|2026:3:01 23:54:11-03:0|2026:3:01 23:51:21-03:0|2026:3:01 23:51:23-03|

<details>
<summary>continúa...</summary>

|||||
|---|---|---|---|
|FilePermissions|-rw-rw-r--|-rw-rw-r--|-rw-rw-r--|
|FileType|JPEG|JPEG|JPEG|
|FileTypeExtension|jpg|jpg|jpg|
|MIMEType|image/jpeg|image/jpeg|image/jpeg|
|ExifByteOrder|Little-endian (Intel, II)|-|-|
|Make|Xiaomi|-|-|
|Orientation|Horizontal (normal)|-|-|
|ModifyDate|2026:3:01 22:58:51|-|-|
|GPSLatitudeRef|South|-|-|
|GPSSpeed|0|-|-|
|GPSAltitudeRef|Above Sea Level|-|-|
|GPSProcessingMethod|network|-|-|
|GPSSpeedRef|km/h|-|-|
|GPSVersionID|2.2.0.0|-|-|
|GPSLongitudeRef|West|-|-|
|GPSTimeStamp|0,0823842592592593|-|-|
|GPSDateStamp|84,4187731481482|-|-|
|YResolution|72|1|1|
|XResolution|72|1|1|
|Model|Redmi Note 14|-|-|
|Software|MediaTek Camera Application|-|-|
|ImageDescription||-|-|
|YCbCrPositioning|Co-sited|-|-|
|ExifVersion|220|-|-|
|AIScene|0|-|-|
|Hdr|off|-|-|
|OpMode|36869|-|-|
|FilterId|66048|-|-|
|Mirror|False|-|-|
|SensorType|rear|-|-|
|SmallPicture|False|-|-|
|ZoomMultiple|1|-|-|
|ExposureCompensation|0|-|-|
|ExposureProgram|Not Defined|-|-|
|ColorSpace|sRGB|-|-|
|MaxApertureValue|1.0|-|-|
|ExifImageHeight|1800|-|-|
|BrightnessValue|7.6|-|-|
|DateTimeOriginal|2026:3:01 22:58:51|-|-|
|FlashpixVersion|100|-|-|
|SubSecTimeOriginal|734|-|-|
|WhiteBalance|Auto|-|-|
|InteropIndex|R98 - DCF basic file (sRGB)|-|-|
|InteropVersion|100|-|-|
|RecommendedExposureIndex|0|-|-|
|ExposureMode|Auto|-|-|
|ExposureTime|1/100|-|-|
|OffsetTime|.-3:0|-|-|
|Flash|Auto, Did not fire|-|-|
|SubSecTime|734|-|-|
|FNumber|1.7|-|-|
|ExifImageWidth|4000|-|-|
|ISO|1004|-|-|
|ComponentsConfiguration|Y, Cb, Cr, -|-|-|
|OffsetTimeDigitized|.-3:0|-|-|
|FocalLengthIn35mmFormat|24 mm|-|-|
|SubSecTimeDigitized|734|-|-|
|DigitalZoomRatio|1|Progressive DCT, Huffman coding|Progressive DCT, Huffman coding|
|CreateDate|2026:3:01 22:58:51|-|-|
|ShutterSpeedValue|1/9|-|-|
|MeteringMode|Center-weighted average|-|-|
|FocalLength|5.2 mm|-|-|
|SensitivityType|Unknown|-|-|
|OffsetTimeOriginal|.-3:0|-|-|
|SceneCaptureType|Standard|-|-|
|LightSource|Other|-|-|
|ResolutionUnit|inches|None|None|
|XiaomiModel|Redmi Note 14|-|-|
|Compression|JPEG (old-style)|-|-|
|ThumbnailOffset|1862|-|-|
|ThumbnailLength|36864|-|-|
|ImageWidth|4000|1600|4000|
|ImageHeight|1800|720|1800|
|EncodingProcess|Baseline DCT, Huffman coding|||
|BitsPerSample|8|8|8|
|ColorComponents|3|3|3|
|YCbCrSubSampling|YCbCr4:2:0 (2 2)|YCbCr4:2:0 (2 2)|YCbCr4|
|Aperture|1.7|-|-|
|ImageSize|4000x1800|1600x720|4000x1800|
|Megapixels|7.2|1.2|7.2|
|ScaleFactor35efl|4.6|-|-|
|ShutterSpeed|1/100|-|-|
|SubSecCreateDate|2026:3:01 22:58:51.734-03:0|-|-|
|SubSecDateTimeOriginal|2026:3:01 22:58:51.734-03:0|-|-|
|SubSecModifyDate|2026:3:01 22:58:51.734-03:0|-|-|
|ThumbnailImage|(Binary data 36864 bytes, use -b option to extract)|-|-|
|GPSAltitude|115.1 m Above Sea Level|-|-|
|GPSDateTime|2026:3:02 01:58:38Z|-|-|
|GPSLatitude|38 deg 15' 57.82" S|-|-|
|GPSLongitude|69 deg 29' 11.23" W|-|-|
|CircleOfConfusion|0.007 mm|-|-|
|FOV|73.7 deg|-|-|
|FocalLength35efl|5.2 mm (35 mm equivalent:24.0 mm)|-|-|
|GPSPosition|38 deg 15' 57.82" S, 69 deg 29' 11.23" W|-|-|
|HyperfocalDistance|2.46 m|-|-|
|LightValue|4.8|-|-|
|JFIFVersion||1.01|1.01|

</details>
<br>

Si bien la compresión es muy grande en la imagen de WhatsApp, la perdida de calidad es muy notoria, no es visible en móviles pero en un monitor se nota mucho, por eso se prefieren los parámetros de la calidad HD, que conserva la resolución y la pérdida de calidad no es significativa, sigue permitiendo impresiones y ampliaciones en una calidad aceptable.

Se pueden editar los parámetros de compresión en:

```python
def comprimir_imagen(origen, destino):
    filtros = []

    cmd = [
        "ffmpeg", "-y",
        "-i", str(origen),
        *filtros,
        "-q:v", Q_IMAGEN,
        str(destino)
    ]
    return ejecutar(cmd).returncode == 0
```

>[!NOTE]
> Los parámetros fueron optimizados para la reproducción en `memories` de Nextcloud, algunos reproductores pueden ser un poco quisquillosos con los formato y etiquetados.

## Licencia

Este proyecto está licenciado bajo la Licencia MIT.  
Puedes usar, copiar, modificar y distribuir el software libremente, siempre que incluyas el aviso de derechos de autor original.

Para más información, consulta el archivo [LICENSE](LICENSE).

## Contacto

**EC4lab**  
GitHub: [ec4lab](https://github.com/ec4lab)  
email: [ec4lab@gmail.com](ec4lab@gmail.com)
