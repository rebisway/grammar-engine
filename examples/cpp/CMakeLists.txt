cmake_minimum_required(VERSION 3.16)
project(grammar_window_cpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(MSVC)
	add_compile_options(/utf-8)
endif()

# The folder which holds the third party libraries: src/third/IMGUI (Dear ImGui), src/third/GLFW
# (headers) and lib/glfw/glfw3.lib. Set it with -DGRAMMAR_THIRD_DIR=... to use another place.
set(GRAMMAR_THIRD_DIR "" CACHE PATH "Folder of the third party libraries")
set(IMGUI_DIR "${GRAMMAR_THIRD_DIR}/src/third/IMGUI")

# The folder which holds the package grammar_engine; the program starts "python -m grammar_engine --serve" there.
# The environment variable GRAMMAR_ENGINE_DIR overrides it at run time.
get_filename_component(GRAMMAR_ENGINE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)

add_executable(grammar_window_cpp
	main.cpp
	${IMGUI_DIR}/imgui.cpp
	${IMGUI_DIR}/imgui_draw.cpp
	${IMGUI_DIR}/imgui_tables.cpp
	${IMGUI_DIR}/imgui_widgets.cpp
	${IMGUI_DIR}/backends/imgui_impl_glfw.cpp
	${IMGUI_DIR}/backends/imgui_impl_opengl3.cpp)
target_include_directories(grammar_window_cpp PRIVATE ${IMGUI_DIR} ${IMGUI_DIR}/backends ${GRAMMAR_THIRD_DIR}/src/third)
target_compile_definitions(grammar_window_cpp PRIVATE GRAMMAR_ENGINE_DIR="${GRAMMAR_ENGINE_ROOT}")

if(WIN32)
	target_link_libraries(grammar_window_cpp PRIVATE ${GRAMMAR_THIRD_DIR}/lib/glfw/glfw3.lib opengl32 gdi32 shell32 user32)
else()
	find_package(glfw3 REQUIRED)
	find_package(OpenGL REQUIRED)
	target_link_libraries(grammar_window_cpp PRIVATE glfw OpenGL::GL pthread)
endif()
