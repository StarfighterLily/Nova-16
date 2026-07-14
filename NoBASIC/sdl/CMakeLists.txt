cmake_minimum_required(VERSION 3.16)
project(NoBASIC_SDL_Runtime C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find SDL2 package
find_package(SDL2 REQUIRED)

# Create the SDL runtime library
add_library(nobasic_sdl_runtime STATIC
    nobasic_sdl_runtime.c
)

target_include_directories(nobasic_sdl_runtime PUBLIC ${SDL2_INCLUDE_DIRS})
target_link_libraries(nobasic_sdl_runtime ${SDL2_LIBRARIES})

# The main runtime wrapper is compiled separately with LLVM IR
# The workflow is:
# 1. Compile NoBASIC to LLVM IR: python nobasic_compiler.py program.nobasic --target llvm
# 2. Compile with clang: clang program.ll nobasic_sdl_runtime.c llvm_runtime_sdl.c -o program.exe -lSDL2