#!/usr/bin/env python3
"""Pipeline di build cross-platform per WhisperGUI.

Stessi comandi su Linux, macOS e Windows (usati anche dalla CI):

    python build.py bootstrap      crea il venv e installa le dipendenze
    python build.py build-engine   compila whisper.cpp con il backend dell'OS
                                   e scarica ffmpeg/ffprobe statici (skip con --skip-engine)
    python build.py build          impacchetta l'app con PyInstaller (onedir)
    python build.py package        produce l'artefatto dell'OS (AppImage / dmg / setup.exe)
    python build.py install        installa localmente l'app appena buildata

Flag:
    --skip-engine   non tocca bin/ (usa i binari gia' presenti)
    --no-bootstrap  usa l'interprete corrente invece del venv
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import urllib.request

APP_NAME = "WhisperGUI"
EXEC_NAME = "whisper-gui"
VERSION = "1.0.0"
WHISPERCPP_TAG = "v1.9.1"
WHISPERCPP_URL = "https://github.com/ggml-org/whisper.cpp.git"

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(ROOT, "bin")
DIST_DIR = os.path.join(ROOT, "dist")
CACHE_DIR = os.path.join(ROOT, "build", "cache")

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = not (IS_WINDOWS or IS_MACOS)

WHISPER_CLI = "whisper-cli.exe" if IS_WINDOWS else "whisper-cli"
SEP = ";" if IS_WINDOWS else ":"

# Lib ABI di sistema che PyInstaller copia nel bundle dal runner (ubuntu-22.04,
# GLIBCXX 3.4.30). Se incluse ombreggiano quelle di sistema tramite
# LD_LIBRARY_PATH e rompono il dlopen dello stack driver Vulkan/Mesa su distro
# piu' nuove (es. libSPIRV-Tools richiede GLIBCXX_3.4.32) -> "no GPU found" con
# fallback CPU. Il sistema dell'utente ha sempre una versione >= a quella del
# runner, quindi la rimozione e' sicura anche sul baseline ubuntu-22.04.
_LINUX_BUNDLE_LIBS_TO_STRIP = (
    "libstdc++.so.6",
    "libgcc_s.so.1",
    "libgomp.so.1",
)


def strip_bundle_system_libs(bundle_dir):
    if not IS_LINUX:
        return
    removed = []
    for name in _LINUX_BUNDLE_LIBS_TO_STRIP:
        path = os.path.join(bundle_dir, name)
        if os.path.isfile(path):
            os.remove(path)
            removed.append(name)
    if removed:
        log(f"Rimossi dal bundle (lib ABI di sistema, evitano lo shadowing che "
            f"rompe il driver Vulkan): {', '.join(removed)}")


def log(msg):
    print(f"[build.py] {msg}")


def run(cmd, cwd=None, check=True):
    log("$ " + " ".join(cmd))
    try:
        return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        if e.stderr:
            print("--- stderr ---")
            print(e.stderr.strip()[-2000:])
        if e.stdout:
            print("--- stdout (tail) ---")
            print(e.stdout.strip()[-2000:])
        raise


def venv_python():
    if os.path.exists(os.path.join(ROOT, ".venv")):
        return os.path.join(ROOT, ".venv", "Scripts" if IS_WINDOWS else "bin", "python" + (".exe" if IS_WINDOWS else ""))
    return sys.executable


def download(url, dest):
    if os.path.exists(dest):
        log(f"Gia' presente: {dest}")
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    log(f"Download {url}")
    urllib.request.urlretrieve(url, dest)


def pip_install(python, *packages):
    run([python, "-m", "pip", "install", "--quiet", *packages])


def bootstrap(args):
    python = sys.executable
    venv = os.path.join(ROOT, ".venv")
    if not os.path.exists(venv):
        log("Creazione venv...")
        run([python, "-m", "venv", venv])
    python = venv_python()
    pip_install(python, "-r", os.path.join(ROOT, "requirements.txt"))
    log("Bootstrap completato.")


def ensure_whispercpp_source():
    src = os.path.join(ROOT, "external", "whisper.cpp")
    if not os.path.isdir(src):
        os.makedirs(os.path.join(ROOT, "external"), exist_ok=True)
        log("Clonazione whisper.cpp...")
        run(["git", "clone", "--depth", "1", "--branch", WHISPERCPP_TAG,
             WHISPERCPP_URL, src])
    return src


def build_engine(args):
    if args.skip_engine and os.path.exists(os.path.join(BIN_DIR, WHISPER_CLI)):
        log("--skip-engine: uso i binari gia' presenti in bin/.")
        ensure_ffmpeg()
        return

    os.makedirs(BIN_DIR, exist_ok=True)
    src = ensure_whispercpp_source()

    if IS_WINDOWS:
        backend = ["-DGGML_VULKAN=ON", "-DGGML_AVX512=OFF"]
    elif IS_MACOS:
        backend = ["-DGGML_METAL=ON", "-DWHISPER_COREML=ON"]
    else:
        backend = ["-DGGML_VULKAN=ON", "-DGGML_AVX512=OFF"]

    log("Configurazione CMake...")
    run(["cmake", "-B", "build", *backend], cwd=src)

    log("Compilazione whisper.cpp...")
    jobs = os.environ.get("BUILD_JOBS")
    build_args = ["-j", jobs] if jobs else ["-j"]
    if IS_WINDOWS:
        run(["cmake", "--build", "build", "--config", "Release", *build_args], cwd=src)
        src_cli = os.path.join(src, "build", "bin", "Release", "whisper-cli.exe")
    else:
        run(["cmake", "--build", "build", *build_args], cwd=src)
        src_cli = os.path.join(src, "build", "bin", "whisper-cli")

    shutil.copy2(src_cli, os.path.join(BIN_DIR, WHISPER_CLI))
    log(f"whisper-cli -> {BIN_DIR}")

    ensure_ffmpeg()


def ensure_ffmpeg():
    missing = [n for n in ("ffmpeg" + (".exe" if IS_WINDOWS else ""),
                           "ffprobe" + (".exe" if IS_WINDOWS else ""))
               if not os.path.exists(os.path.join(BIN_DIR, n))]
    if not missing:
        return

    if IS_WINDOWS:
        url = ("https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
               "ffmpeg-n7.1-latest-win64-gpl-7.1.zip")
        zpath = os.path.join(CACHE_DIR, "ffmpeg-win64.zip")
        download(url, zpath)
        import zipfile
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(os.path.join(CACHE_DIR, "ffmpeg-win64"))
        root = os.path.join(CACHE_DIR, "ffmpeg-win64")
        src_bin = None
        for d in os.listdir(root):
            cand = os.path.join(root, d, "bin")
            if os.path.isdir(cand):
                src_bin = cand
                break
        for n in ("ffmpeg.exe", "ffprobe.exe"):
            shutil.copy2(os.path.join(src_bin, n), BIN_DIR)
    elif IS_MACOS:
        download("https://www.osxexperts.net/ffmpeg81arm.zip",
                 os.path.join(CACHE_DIR, "ffmpeg-macos-arm64.zip"))
        download("https://www.osxexperts.net/ffprobe81arm.zip",
                 os.path.join(CACHE_DIR, "ffprobe-macos-arm64.zip"))
        import zipfile
        for name, dest in (("ffmpeg-macos-arm64.zip", "ffmpeg"),
                           ("ffprobe-macos-arm64.zip", "ffprobe")):
            with zipfile.ZipFile(os.path.join(CACHE_DIR, name)) as zf:
                zf.extractall(BIN_DIR)
            for f in os.listdir(BIN_DIR):
                if f.lower().startswith(dest):
                    os.replace(os.path.join(BIN_DIR, f), os.path.join(BIN_DIR, dest))
                    break
        for n in ("ffmpeg", "ffprobe"):
            os.chmod(os.path.join(BIN_DIR, n), 0o755)
        log("Firma ad-hoc e rimozione quarantena (binari macOS)...")
        run(["xattr", "-cr", BIN_DIR], check=False)
        for n in ("ffmpeg", "ffprobe"):
            run(["codesign", "--force", "--sign", "-", os.path.join(BIN_DIR, n)], check=False)
    else:
        download("https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz?accept=yes",
                 os.path.join(CACHE_DIR, "ffmpeg-linux.tar.xz"))
        import tarfile
        with tarfile.open(os.path.join(CACHE_DIR, "ffmpeg-linux.tar.xz")) as tf:
            tf.extractall(os.path.join(CACHE_DIR, "ffmpeg-linux"))
        root = [d for d in os.listdir(os.path.join(CACHE_DIR, "ffmpeg-linux"))
                if d.endswith("-static")][0]
        for n in ("ffmpeg", "ffprobe"):
            shutil.copy2(os.path.join(CACHE_DIR, "ffmpeg-linux", root, n), BIN_DIR)
            os.chmod(os.path.join(BIN_DIR, n), 0o755)

    log("ffmpeg/ffprobe pronti in bin/.")


def build_app(args):
    python = venv_python()
    if not args.no_bootstrap and not os.path.exists(os.path.join(ROOT, ".venv")):
        log("Venv assente: esegui prima 'python build.py bootstrap'.")
        sys.exit(1)

    spec_dir = os.path.join(ROOT, "build", "pyinstaller")
    os.makedirs(spec_dir, exist_ok=True)
    os.makedirs(DIST_DIR, exist_ok=True)

    cmd = [
        python, "-m", "PyInstaller",
        "--onedir", "--noconfirm",
        "--distpath", DIST_DIR,
        "--workpath", os.path.join(spec_dir, "work"),
        "--specpath", spec_dir,
        "--add-data", f"{os.path.join(ROOT, 'bin')}{SEP}bin",
        "--add-data", f"{os.path.join(ROOT, 'media')}{SEP}media",
        "--add-data", f"{os.path.join(ROOT, 'icon')}{SEP}icon",
        "--add-data", f"{os.path.join(ROOT, 'licenses')}{SEP}licenses",
        "--paths", ROOT,
        "--name", APP_NAME,
        os.path.join(ROOT, "main.py"),
    ]
    run(cmd)
    strip_bundle_system_libs(os.path.join(DIST_DIR, APP_NAME, "_internal"))
    log(f"App buildata in {os.path.join(DIST_DIR, APP_NAME)}")


def package_linux():
    out_dir = os.path.join(ROOT, "installer", "linux", "output")
    os.makedirs(out_dir, exist_ok=True)
    appdir = os.path.join(ROOT, "build", "AppDir")
    if os.path.exists(appdir):
        shutil.rmtree(appdir)
    shutil.copytree(os.path.join(DIST_DIR, APP_NAME), appdir)

    python = venv_python()
    run([python, os.path.join(ROOT, "scripts", "icon_gen.py"), "png",
         os.path.join(ROOT, "icon", "ai_studio_code.svg"),
         "/tmp/whisper-gui.png", "256"])
    shutil.copy2("/tmp/whisper-gui.png", os.path.join(appdir, "whisper-gui.png"))

    with open(os.path.join(appdir, "AppRun"), "w") as f:
        f.write('#!/bin/bash\nexec "$APPDIR/%s" "$@"\n' % APP_NAME)
    os.chmod(os.path.join(appdir, "AppRun"), 0o755)

    with open(os.path.join(appdir, "whisper-gui.desktop"), "w") as f:
        f.write(
            "[Desktop Entry]\n"
            "Version=1.0\n"
            "Type=Application\n"
            "Name=WhisperGUI\n"
            "Comment=Trascrizione AI nativa (Vulkan)\n"
            "Exec=WhisperGUI\n"
            "Icon=whisper-gui\n"
            "StartupWMClass=whisper-gui\n"
            "Terminal=false\n"
            "Categories=AudioVideo;Audio;\n"
        )

    tool = os.path.join(CACHE_DIR, "appimagetool-x86_64.AppImage")
    download("https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage", tool)
    os.chmod(tool, 0o755)

    output = os.path.join(out_dir, "WhisperGUI-x86_64.AppImage")
    run([tool, "--appimage-extract-and-run", appdir, output])
    os.chmod(output, 0o755)
    log(f"AppImage creata: {output}")


def package_macos():
    out_dir = os.path.join(ROOT, "installer", "macos", "output")
    os.makedirs(out_dir, exist_ok=True)
    app = os.path.join(ROOT, "build", "WhisperGUI.app")
    if os.path.exists(app):
        shutil.rmtree(app)
    macos_dir = os.path.join(app, "Contents", "MacOS")
    res_dir = os.path.join(app, "Contents", "Resources")
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(res_dir, exist_ok=True)

    for item in os.listdir(os.path.join(DIST_DIR, APP_NAME)):
        item_src = os.path.join(DIST_DIR, APP_NAME, item)
        if os.path.isdir(item_src):
            shutil.copytree(item_src, os.path.join(macos_dir, item), dirs_exist_ok=True)
        else:
            shutil.copy2(item_src, macos_dir)

    python = venv_python()
    iconset = "/tmp/icon.iconset"
    run([python, os.path.join(ROOT, "scripts", "icon_gen.py"), "iconset",
         os.path.join(ROOT, "icon", "ai_studio_code.svg"), iconset])
    run(["iconutil", "-c", "icns", iconset,
         "-o", os.path.join(res_dir, "icon.icns")])

    with open(os.path.join(app, "Contents", "Info.plist"), "w") as f:
        f.write(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n<dict>\n'
            "  <key>CFBundleExecutable</key>\n  <string>WhisperGUI</string>\n"
            "  <key>CFBundleIdentifier</key>\n  <string>com.whisper.gui</string>\n"
            "  <key>CFBundleName</key>\n  <string>WhisperGUI</string>\n"
            "  <key>CFBundleIconFile</key>\n  <string>icon.icns</string>\n"
            "  <key>CFBundlePackageType</key>\n  <string>APPL</string>\n"
            "  <key>CFBundleShortVersionString</key>\n  <string>" + VERSION + "</string>\n"
            "  <key>LSMinimumSystemVersion</key>\n  <string>12.0</string>\n"
            "</dict>\n</plist>\n"
        )

    # Niente codesign del bundle: la firma ad-hoc non abilita alcun vantaggio
    # (l'app non e' notarizzata) e rende il packaging fragile in CI.
    # Gli eseguibili interni (whisper-cli, ffmpeg) sono gia' firmati ad-hoc
    # da build-engine per poter girare su Apple Silicon.

    dmg = os.path.join(out_dir, "WhisperGUI-macOS-arm64.dmg")
    if os.path.exists(dmg):
        os.remove(dmg)
    run(["hdiutil", "create", "-volname", "WhisperGUI",
         "-srcfolder", app, "-ov", "-format", "UDZO", dmg])
    log(f"DMG creata: {dmg}")


def package_windows():
    out_dir = os.path.join(ROOT, "installer", "windows", "output")
    os.makedirs(out_dir, exist_ok=True)

    makensis = shutil.which("makensis")
    if not makensis:
        zpath = os.path.join(CACHE_DIR, "nsis-3.12.zip")
        download("https://sourceforge.net/projects/nsis/files/NSIS%203/3.12/nsis-3.12.zip/download", zpath)
        import zipfile
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(os.path.join(CACHE_DIR, "nsis"))
        found = glob.glob(os.path.join(CACHE_DIR, "nsis", "**", "makensis.exe"), recursive=True)
        if not found:
            raise RuntimeError("makensis.exe non trovato dopo l'estrazione di NSIS")
        makensis = found[0]

    nsi = os.path.join(ROOT, "installer", "windows", "whispergui.nsi")
    output = os.path.join(out_dir, "WhisperGUI-x86_64-setup.exe")
    run([makensis,
         f"-DVERSION={VERSION}",
         f"-DAPP_PATH={os.path.join(DIST_DIR, APP_NAME)}",
         f"-DOUT_FILE={output}",
         nsi])
    log(f"Setup NSIS creato: {output}")


def package(args):
    if IS_LINUX:
        package_linux()
    elif IS_MACOS:
        package_macos()
    else:
        package_windows()


def install(args):
    if IS_LINUX:
        install_linux()
    elif IS_MACOS:
        install_macos()
    else:
        install_windows()


def install_linux():
    app_dir = os.path.join(os.path.expanduser("~"), ".local", "lib", EXEC_NAME)
    bin_dest = os.path.join(os.path.expanduser("~"), ".local", "bin", EXEC_NAME)
    src = os.path.join(DIST_DIR, APP_NAME)

    if not os.path.exists(src):
        log("App non buildata: esegui prima 'python build.py build'.")
        sys.exit(1)

    shutil.rmtree(app_dir, ignore_errors=True)
    os.makedirs(app_dir)
    for item in os.listdir(src):
        item_src = os.path.join(src, item)
        if os.path.isdir(item_src):
            shutil.copytree(item_src, os.path.join(app_dir, item), dirs_exist_ok=True)
        else:
            shutil.copy2(item_src, app_dir)

    os.makedirs(os.path.dirname(bin_dest), exist_ok=True)
    with open(bin_dest, "w") as f:
        f.write('#!/bin/bash\nexec "%s/%s" "$@"\n' % (app_dir, APP_NAME))
    os.chmod(bin_dest, 0o755)

    icons = os.path.join(os.path.expanduser("~"), ".local", "share", "icons",
                         "hicolor", "scalable", "apps")
    os.makedirs(icons, exist_ok=True)
    shutil.copy2(os.path.join(ROOT, "icon", "ai_studio_code.svg"),
                 os.path.join(icons, "whisper-gui.svg"))

    apps = os.path.join(os.path.expanduser("~"), ".local", "share", "applications")
    os.makedirs(apps, exist_ok=True)
    with open(os.path.join(apps, "whisper-gui.desktop"), "w") as f:
        f.write(
            "[Desktop Entry]\n"
            "Version=1.0\n"
            "Type=Application\n"
            "Name=WhisperGUI\n"
            "Comment=Trascrizione AI nativa (Vulkan)\n"
            "Exec=whisper-gui\n"
            "Icon=whisper-gui\n"
            "Terminal=false\n"
            "Categories=AudioVideo;Audio;\n"
        )
    log(f"Installato in {app_dir} (wrapper: {bin_dest})")


def install_macos():
    app = os.path.join(ROOT, "build", "WhisperGUI.app")
    if not os.path.exists(app):
        log("App non buildata: esegui prima 'python build.py build && package'.")
        sys.exit(1)
    dest = os.path.join(os.path.expanduser("~"), "Applications", "WhisperGUI.app")
    os.makedirs(os.path.expanduser("~") + "/Applications", exist_ok=True)
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(app, dest)
    log(f"Installato in {dest}")
    cli = "/usr/local/bin/" + EXEC_NAME
    if os.path.exists(cli):
        os.remove(cli)
    os.symlink(os.path.join(dest, "Contents", "MacOS", APP_NAME), cli)
    log(f"CLI: {cli}")


def install_windows():
    setup = os.path.join(ROOT, "installer", "windows", "output", "WhisperGUI-x86_64-setup.exe")
    if os.path.exists(setup):
        log("Avvio del setup NSIS...")
        subprocess.run([setup], check=False)
        return
    src = os.path.join(DIST_DIR, APP_NAME)
    if not os.path.exists(src):
        log("Nessun setup ne' app buildata: esegui 'python build.py build'.")
        sys.exit(1)
    dest = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "WhisperGUI")
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    log(f"Installato in {dest}")


def main():
    parser = argparse.ArgumentParser(description="WhisperGUI build pipeline")
    parser.add_argument("command", choices=["bootstrap", "build-engine", "build", "package", "install"])
    parser.add_argument("--skip-engine", action="store_true", help="usa i binari bin/ esistenti")
    parser.add_argument("--no-bootstrap", action="store_true", help="non usare il venv")
    args = parser.parse_args()

    if args.command == "bootstrap":
        bootstrap(args)
    elif args.command == "build-engine":
        build_engine(args)
    elif args.command == "build":
        build_app(args)
    elif args.command == "package":
        package(args)
    elif args.command == "install":
        install(args)


if __name__ == "__main__":
    main()
