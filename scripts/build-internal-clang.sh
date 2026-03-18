#!/usr/bin/env bash
echoerr() { echo "ERROR: $@" 1>&2; }

set -o errexit
set -o pipefail
set -o nounset

OS="$(uname)"

if [[ "$OS" == "Darwin" ]]; then
    if [[ "$#" != "1" ]] ; then
      echo "$0 <install dir>"
      exit 1
    fi
else
    if [[ "$#" != "2" ]] ; then
      echo "$0 <install dir> <# of cpus>"
      exit 1
    fi
    readonly NCPUS=$2
fi

# user-defined: where to build, and where to install
if [[ "$OS" == "Darwin" ]]; then
    readonly BUILDROOT="$(mktemp -d -t clang-builder)"
else
    readonly BUILDROOT="$(mktemp --directory --suffix "-clang-builder")"
fi

function cleanup() {
  rm -rf "${BUILDROOT}" &> /dev/null || true
}
trap cleanup EXIT

readonly SRC_FOLDER_NAME="llvm-project"
readonly BUILD_FOLDER_NAME="llvm-build-trunk"
readonly BU_SRC_FOLDER_NAME="binutils-src"
readonly BU_BUILD_FOLDER_NAME="binutils-build"
if [[ "$OS" == "Darwin" ]]; then
    readonly INSTALLROOT="$(pwd)/$1"
else
    readonly INSTALLROOT="$(readlink -f $1)"
fi
readonly HOME_USR_BIN="${HOME}/usr/bin"

mkdir -p "${BUILDROOT}"
cd "${BUILDROOT}"
rm -rf * || true # remove everything in the build root folder
git clone --depth 1 https://github.com/llvm/llvm-project.git

##################################################
# Build Gold Linker (Skip on MacOS)
##################################################
if [[ "$OS" != "Darwin" ]]; then
    readonly BINUTIL_TAR_FOLDER_NAME="binutils-2.38"
    readonly BINUTIL_TAR_NAME="${BINUTIL_TAR_FOLDER_NAME}.tar.gz"
    rm -rf "${BU_SRC_FOLDER_NAME}" "${BINUTIL_TAR_FOLDER_NAME}" "${BINUTIL_TAR_NAME}" || true
    wget ftp://sourceware.org/pub/binutils/releases/${BINUTIL_TAR_NAME}
    tar xf ${BINUTIL_TAR_NAME}
    mv ${BINUTIL_TAR_FOLDER_NAME} ${BU_SRC_FOLDER_NAME}

    rm -rf "${BU_BUILD_FOLDER_NAME}"
    mkdir -p "${BU_BUILD_FOLDER_NAME}"
    cd "${BU_BUILD_FOLDER_NAME}"
    ../${BU_SRC_FOLDER_NAME}/configure --enable-gold --enable-plugins --disable-werror > /dev/null
    make all-gold -j${NCPUS} > /dev/null

    cd "${BUILDROOT}"
fi

##################################################
# Build LLVM
##################################################
rm -rf "${BUILD_FOLDER_NAME}"
mkdir -p "${BUILD_FOLDER_NAME}"
cd ${BUILD_FOLDER_NAME}

# Prepare CMake arguments
CMAKE_ARGS=(-DCMAKE_INSTALL_PREFIX=${INSTALLROOT}
           -DCMAKE_C_COMPILER_LAUNCHER=ccache
           -DCMAKE_CXX_COMPILER_LAUNCHER=ccache
           -DCMAKE_BUILD_TYPE=Release
           -DLLVM_ENABLE_ASSERTIONS=ON
           -DLLVM_BUILD_LLVM_DYLIB=ON
           -DLLVM_ENABLE_RTTI=ON
           -DLLVM_ENABLE_EH=ON
           -DLLVM_ENABLE_PROJECTS="clang;llvm;clang-tools-extra;compiler-rt;polly")

# Add OS-specific CMake arguments
if [[ "$OS" != "Darwin" ]]; then
    CMAKE_ARGS+=(-DLLVM_BINUTILS_INCDIR=${BUILDROOT}/${BU_SRC_FOLDER_NAME}/include)
fi

cmake -G Ninja "${CMAKE_ARGS[@]}" ../${SRC_FOLDER_NAME}/llvm

mkdir -p "${INSTALLROOT}"

ninja install

mkdir -p "${HOME_USR_BIN}"
cd "${HOME_USR_BIN}"

readonly CLANG_TRUNK="clang-trunk"
readonly CLANGPP_TRUNK="clang++-trunk"
readonly LLVM_CONFIG="llvm-config-trunk"

rm "${CLANG_TRUNK}" || true
rm "${CLANGPP_TRUNK}" || true
rm "${LLVM_CONFIG}" || true

ln -s "${INSTALLROOT}/bin/clang" "${CLANG_TRUNK}"
ln -s "${INSTALLROOT}/bin/clang++" "${CLANGPP_TRUNK}"
ln -s "${INSTALLROOT}/bin/llvm-config" "${LLVM_CONFIG}"

echo "${CLANG_TRUNK}, ${CLANGPP_TRUNK} and ${LLVM_CONFIG} are created successfully in ${HOME_USR_BIN}"
