#!/usr/bin/env bash
set -eo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -d "$root/build-tools" ]]; then
    root="$(dirname "$root")"
fi
cd "$root"
abi="${1:-arm64-v8a}"
case "$abi" in
    arm64-v8a|armeabi-v7a|x86_64) ;;
    *) printf 'Unsupported Android ABI: %s\n' "$abi" >&2; exit 2 ;;
esac

: "${AVELIS_KDE_DEPS:?Set to the pinned KDE krita-deps-management checkout}"
: "${AVELIS_KDE_PYTHON:?Set to the Python interpreter with KDE CI dependencies installed}"
: "${AVELIS_KDE_ENV:?Set to the KDE Android build environment setup script}"

. "$AVELIS_KDE_ENV"
export CI_PROJECT_DIR="$root"
export CI_PROJECT_NAME=krita
export CI_COMMIT_REF_NAME="${GITHUB_REF_NAME:-$(git branch --show-current 2>/dev/null || true)}"
CI_COMMIT_REF_NAME="${CI_COMMIT_REF_NAME:-master}"
export CI_COMMIT_SHORT_SHA
CI_COMMIT_SHORT_SHA="$(git rev-parse --short HEAD 2>/dev/null || cut -c1-12 UPSTREAM-REVISION)"
export KDECI_ANDROID_ABI="$abi"
export KDECI_PACKAGE_PROJECT="teams/ci-artifacts/krita-android-$abi"
export KDECI_CACHE_PATH="${KDECI_CACHE_PATH:-${RUNNER_TEMP:-/tmp}/avelis-kde-android-$abi-cache}"
mkdir -p "$KDECI_CACHE_PATH"
export KDECI_BUILD_TYPE=Release
export KDECI_GITLAB_SERVER=https://invent.kde.org/
export KDECI_REPO_METADATA_PATH="$AVELIS_KDE_DEPS/repo-metadata"
export KDECI_SKIP_ECM_ANDROID_TOOLCHAIN=True
export KDECI_COMPRESS_PACKAGES_ON_DOWNLOAD=False
export KDECI_EXTRA_CMAKE_ARGS="-DHIDE_SAFE_ASSERTS=OFF -DBUILD_TESTING=ON"
export CMAKE_TOOLCHAIN_FILE="$AVELIS_KDE_DEPS/tools/android-toolchain-krita.cmake"
export KRITACI_ANDROID_PACKAGE_TYPE=debug
export KDECI_WORKDIR_PATH
KDECI_WORKDIR_PATH="$(mktemp -d "${RUNNER_TEMP:-/tmp}/avelis-kde.XXXXXXXX")"

config_backup="$KDECI_WORKDIR_PATH/kde-ci.yml"
cp .kde-ci.yml "$config_backup"
trap 'cp "$config_backup" .kde-ci.yml; rm -rf -- "$KDECI_WORKDIR_PATH"' EXIT

"$AVELIS_KDE_PYTHON" "$AVELIS_KDE_DEPS/tools/replace-branch-in-seed-file.py" \
    "$AVELIS_KDE_DEPS/latest/krita-deps.yml" -p \
    -o "$KDECI_WORKDIR_PATH/deps.yml" -d master
"$AVELIS_KDE_PYTHON" "$AVELIS_KDE_DEPS/tools/generate-deps-file.py" \
    -s "$KDECI_WORKDIR_PATH/deps.yml" -o .kde-ci.yml
"$AVELIS_KDE_PYTHON" -u "$AVELIS_KDE_DEPS/ci-utilities/run-ci-build.py" \
    --project "$CI_PROJECT_NAME" --branch "$CI_COMMIT_REF_NAME" \
    --platform "Android/$abi/Qt5/Shared" --only-build --skip-publishing 2>&1 | tee build-krita.log
package_apk() {
    "$AVELIS_KDE_PYTHON" -u build-tools/ci-scripts/build-android-package.py 2>&1 | tee -a build-apk.log
}
# AGP 8.12 butuh JDK 17+, sedangkan image runner default ke Java 11.
for jdk in "${JAVA_HOME_17_X64:-}" "${JAVA_HOME_21_X64:-}"; do
    if [[ -n "$jdk" && -x "$jdk/bin/java" ]]; then
        export JAVA_HOME="$jdk"
        export PATH="$JAVA_HOME/bin:$PATH"
        break
    fi
done
: > build-apk.log
{ echo "## JAVA_HOME=${JAVA_HOME:-unset}"; java -version 2>&1; } | tee -a build-apk.log || true
if package_apk; then
    :
elif [[ "${GITHUB_ACTIONS:-}" == true ]] && grep -Fq 'Invalid json output from qmlimportscanner.' build-apk.log; then
    # qmlimportscanner bawaan paket Qt KDE crash (segfault) di runner GitHub.
    # Ganti dengan qmlimportscanner Qt5 host dari apt, lalu ulangi packaging.
    echo "## qmlimportscanner KDE crash, mencoba scanner host dari apt" | tee -a build-apk.log
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends qtdeclarative5-dev-tools
    # dpkg -L mengembalikan 2 path (asli + symlink multiarch): ambil yang pertama saja.
    host_scanner="$(dpkg -L qtdeclarative5-dev-tools | awk '/\/qt5\/bin\/qmlimportscanner$/ {print; exit}')"
    if [[ -z "$host_scanner" || ! -x "$host_scanner" ]]; then
        echo "qmlimportscanner host (apt) tidak ditemukan" >&2
        exit 1
    fi
    install_root="$KDECI_WORKDIR_PATH/krita/_install"
    mapfile -t scanners < <(find "$install_root" -name qmlimportscanner \( -type f -o -type l \))
    if (( ${#scanners[@]} == 0 )); then
        echo "qmlimportscanner tidak ditemukan di $install_root" >&2
        exit 1
    fi
    for scanner in "${scanners[@]}"; do
        echo "## Mengganti $scanner dengan wrapper ke $host_scanner" | tee -a build-apk.log
        { file "$scanner" || true; ldd "$scanner" || true; } 2>&1 | tee -a build-apk.log
        mv "$scanner" "$scanner.kde"
        {
            printf '#!/usr/bin/env bash\n'
            printf 'unset LD_LIBRARY_PATH QT_PLUGIN_PATH\n'
            printf 'exec %q "$@"\n' "$host_scanner"
        } > "$scanner"
        chmod +x "$scanner"
    done
    package_apk
else
    exit 1
fi
shopt -s nullglob
apks=("$KDECI_WORKDIR_PATH"/krita/_packaging/*.apk)
if (( ${#apks[@]} == 0 )); then
    echo "KDE packaging completed without producing an APK." >&2
    exit 1
fi
output="_packaging/$abi"
mkdir -p "$output"
for apk in "${apks[@]}"; do
    cp "$apk" "$output/"
    (cd "$output" && sha256sum "$(basename "$apk")" > "$(basename "$apk").sha256")
done
