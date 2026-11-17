"""Build FH2 rendering overrides from the local game assets."""
from pathlib import Path
import math
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile


def smoothstep(start, end, value):
    x = max(0.0, min(1.0, (value - start) / (end - start)))
    return x * x * (3.0 - 2.0 * x)


def byte(value):
    return max(0, min(255, round(value)))


def daytime_grade(stock):
    # The stock swatch is a tiled 16x16x16 RGBA8 volume. Apply a pointwise
    # transform in place so the tile order, alpha, header and padding stay intact.
    if (
        len(stock) != 20307
        or stock[:4] != b"burG"
        or stock[16:20] != b"BCXT"
        or stock[40:44] != b"HCXT"
        or struct.unpack_from("<6H", stock, 64) != (16,) * 6
        or stock[76:83] != bytes.fromhex("05 05 00 ad 01 00 44")
    ):
        raise ValueError("Unexpected DryDay swatch layout")

    result = bytearray(stock)
    for i in range(83, len(stock), 4):
        red, green, blue, alpha = stock[i:i + 4]
        if alpha == 0:
            if blue or green or red:
                raise ValueError("Unexpected DryDay padding")
            continue
        if alpha != 255:
            raise ValueError("Unexpected alpha in the DryDay volume")

        luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
        midtone = 4 * luminance * (1 - luminance)
        cool = smoothstep(5, 60, blue - red)
        warmth = midtone * (1 - 0.86 * cool)
        # Pull saturated yellow grass toward its original luminance, and
        # apply a shared gain so the brightness curve does not shift hue.
        yellow = smoothstep(14, 90, min(red, green) - blue)
        desaturation = 0.24 * yellow
        gray = luminance * 255
        gain = 1 - 0.11 * luminance - 0.17 * midtone
        result[i:i + 3] = bytes((
            byte((red + (gray - red) * desaturation + 6 * warmth) * gain),
            byte((green + (gray - green) * desaturation + 1 * warmth) * gain),
            byte((blue + (gray - blue) * desaturation - 7 * warmth) * gain),
        ))
    return result


def daylight_curves(stock):
    def u32(offset):
        return struct.unpack_from("<I", stock, offset)[0]

    if stock[:12] != b"FxBk\x08R\0\0XOne" or u32(12) != len(stock):
        raise ValueError("Unexpected TimeOfDay FXB layout")

    result = bytearray(stock)
    string_start, string_end = u32(20), u32(24)
    color_start, color_end = u32(44), u32(48)
    root = u32(92)
    track = u32(root + 40)
    bindings = u32(track + 20)
    strength_by_curve = {b"Sun.Colour": 1.0, b"Misc.StaticCubeSunColour": 0.6}
    found = set()
    for index in range(u32(track + 16)):
        definition, curve = struct.unpack_from("<II", stock, bindings + index * 8)
        name_start = u32(definition)
        if not string_start <= name_start < string_end:
            raise ValueError("Invalid TimeOfDay FXB property name")
        name = stock[name_start:stock.index(0, name_start, string_end)]
        if name not in strength_by_curve:
            continue
        if u32(definition + 4) != 3 or not color_start <= curve <= color_end - 4:
            raise ValueError(f"Invalid TimeOfDay color curve {name!r}")
        count = u32(curve)
        if count < 2 or curve + 4 + count * 8 > color_end or name in found:
            raise ValueError(f"Unexpected TimeOfDay color keys for {name!r}")
        found.add(name)
        for key in range(count):
            offset = curve + 4 + key * 8
            time, blue, green, red, alpha = struct.unpack_from("<f4B", stock, offset)
            if not math.isfinite(time) or not 0 <= time <= 1 or alpha != 255:
                raise ValueError(f"Invalid TimeOfDay color key for {name!r}")
            daylight = smoothstep(0.24, 0.35, time) * (1 - smoothstep(0.71, 0.80, time))
            amount = daylight * strength_by_curve[name]
            struct.pack_into("<3B", result, offset + 4,
                             byte(blue * (1 - 0.06 * amount)),
                             byte(green * (1 - 0.008 * amount)),
                             byte(red * (1 + 0.008 * amount)))
    if found != strength_by_curve.keys():
        raise ValueError("TimeOfDay FXB is missing required color curves")
    return result


def vignette(stock):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    root = ET.fromstring(stock, parser)
    if root.tag != "CameraPhysics":
        raise ValueError("Unexpected camera physics XML")

    for name in ("FollowCam", "FollowCam2"):
        layers = root.findall(f"./{name}/Layer[@OutputType='Vignette']")
        if len(layers) != 1 or layers[0].get("InputToParamMapping") != "FivePoint":
            raise ValueError(f"Missing stock vignette layer for {name}")
        layer = layers[0]
        layer.set("Enabled", "1")
        # Keep the normal chase-camera vignette geometry. Use the same
        # amount at each speed so it is visible even when stopped.
        for key in range(5):
            layer.set(f"InputToParamCurveOutput{key}", "0.280000")
        layer.set("InputToParamCurveInput0", "0.000000")

    return ET.tostring(root, encoding="utf-8")


def main(media, output):
    with zipfile.ZipFile(media / "PostEffects.zip") as archive:
        grade = daytime_grade(archive.read("ColourGradingMaps/DryDay.swatchbin"))
    with zipfile.ZipFile(media / "Camera.zip") as archive:
        camera = vignette(archive.read("CameraPhysics.xml"))
    tod = media / "timeofday/xboxone"
    assets = {
        101: ("DryDay.swatchbin", grade),
        102: ("TimeOfDay.fxb", daylight_curves((tod / "TimeOfDay.fxb").read_bytes())),
        103: ("TimeOfDay_island.fxb", daylight_curves((tod / "TimeOfDay_island.fxb").read_bytes())),
        104: ("CameraPhysics.xml", camera),
    }
    output.mkdir(parents=True, exist_ok=True)
    resources = []
    for identifier, (filename, data) in assets.items():
        path = output / filename
        path.write_bytes(data)
        resources.append(f'{identifier} RCDATA "{path.resolve().as_posix()}"\n')
    (output / "assets.rc").write_text("".join(resources), encoding="ascii")


if __name__ == "__main__":
    main(*(Path(arg) for arg in sys.argv[1:]))
