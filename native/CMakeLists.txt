cmake_minimum_required(VERSION 3.18)
project(mendlock_native VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(MSVC)
    add_compile_options(/O2 /arch:AVX2 /W4)
else()
    add_compile_options(-O3 -Wall -Wextra -ffast-math)
    if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
        add_compile_options(-mavx2 -mfma)
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64|arm64")
        add_compile_options(-mcpu=cortex-a76)
    endif()
endif()

include_directories(include)

# 1. Shared library loaded by Python ctypes (mendlock/native_bridge.py)
add_library(mendlock_core SHARED src/mendlock_core.cpp)

# Copy the built shared library into ../mendlock/native/ automatically
set(PY_NATIVE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../mendlock/native")
add_custom_command(TARGET mendlock_core POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "${PY_NATIVE_DIR}"
    COMMAND ${CMAKE_COMMAND} -E copy "$<TARGET_FILE:mendlock_core>" "${PY_NATIVE_DIR}/"
    COMMENT "Copying mendlock_core shared library to mendlock/native/"
)

# 2. Standalone C++ unit test and micro-benchmark binary
add_executable(test_native src/test_native.cpp src/mendlock_core.cpp)

# 3. Optional lightweight Edge Daemon for Raspberry Pi 5 offload benchmarks
if(UNIX)
    add_executable(mendlock_edge_daemon src/edge_daemon.cpp src/mendlock_core.cpp)
endif()