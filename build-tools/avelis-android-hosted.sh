#!/usr/bin/env bash
set -euo pipefail

: "${RUNNER_TEMP:?Missing GitHub runner temp directory}"
export KDECI_ANDROID_SDK_ROOT="${ANDROID_HOME:?Missing Android SDK}"
sdkmanager="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
ndk_version=27.3.13750724
"$sdkmanager" --install 'platforms;android-36' 'build-tools;36.0.0' "ndk;$ndk_version"
export KDECI_ANDROID_NDK_ROOT="$ANDROID_HOME/ndk/$ndk_version"

deps="$RUNNER_TEMP/avelis-kde-deps"
checkout_pin() {
    git init -q "$1"
    git -C "$1" fetch --depth=1 "$2" "$3"
    git -C "$1" checkout --detach FETCH_HEAD
}
checkout_pin "$deps" https://invent.kde.org/packaging/krita-deps-management.git 3e9eb8a143c114aa33520421a67c8edfeef649ee
checkout_pin "$deps/ci-utilities" https://invent.kde.org/packaging/krita-ci-utilities.git b591f0ef834d061329707e8841b97ff6a0b3c48b

python3 -m venv "$RUNNER_TEMP/avelis-kde-venv"
export AVELIS_KDE_PYTHON="$RUNNER_TEMP/avelis-kde-venv/bin/python"
"$AVELIS_KDE_PYTHON" -m pip install --require-hashes -r "$deps/requirements.txt"
export AVELIS_KDE_DEPS="$deps"
export AVELIS_KDE_ENV=/dev/null
export PATH="$RUNNER_TEMP/avelis-kde-venv/bin:$PATH"
bash build-tools/avelis-android.sh "$1"

for apk in "_packaging/$1/"*.apk; do
    "$ANDROID_HOME/build-tools/36.0.0/apksigner" verify "$apk"
    "$ANDROID_HOME/build-tools/36.0.0/aapt" dump badging "$apk" > "$apk.info"
    grep -F "native-code:" "$apk.info" | grep -F "'$1'"
    grep -F "package: name='org.avelis.paint.debug'" "$apk.info"
done
