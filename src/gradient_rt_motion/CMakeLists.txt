cmake_minimum_required(VERSION 3.16)

project(gradient_rt_motion LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(gradient-rt-motion
  main.cpp
)

target_compile_definitions(gradient-rt-motion PRIVATE _GNU_SOURCE)
target_compile_options(gradient-rt-motion PRIVATE -Wall -Wextra -Wpedantic)

target_link_libraries(gradient-rt-motion PRIVATE pthread)

