// Grammar window in C++ with Dear ImGui (GLFW + OpenGL 3), the engine in another process.
//
// What it shows:
//   - how to start "python -m grammar_engine --serve" from C++ and talk to it through two pipes (Windows: CreateProcess,
//     other systems: fork/exec) with one JSON text per line;
//   - a tiny JSON reader and writer, enough for the protocol (no library needed);
//   - how to keep an immediate-mode interface responsive: the request runs in a std::thread, the frame loop only looks
//     at a flag;
//   - how to select a problem in the text: ImGui indexes its text buffer in UTF-8 BYTES, so the byte_start / byte_end
//     fields of the engine are used as they are (no conversion from code points).
//
// Build: see README.md (CMake; Dear ImGui and GLFW come from the folder GRAMMAR_THIRD_DIR).
// Run:   grammar_window_cpp [file.txt]            or      grammar_window_cpp --selftest file.txt lang
//
// SPDX-License-Identifier: MIT

#ifdef _WIN32
#include <windows.h>                                          // before GLFW, which defines APIENTRY itself only if it is not defined yet
#endif
#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"
#include <GLFW/glfw3.h>

#include <atomic>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <vector>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef _WIN32
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

// [SECTION] Minimal JSON

struct Json
{
    enum Type { Null, Bool, Number, String, Array, Object } Kind = Null;
    double Num = 0.0;
    bool Flag = false;
    std::string Str;
    std::vector<Json> Items;                                 // array elements, or the values of an object
    std::vector<std::string> Keys;                           // the keys of an object, in the same order as Items

    const Json* Get(const char* key) const
    {
        for (size_t i = 0; i < Keys.size(); i++)
            if (Keys[i] == key)
                return &Items[i];
        return NULL;
    }
    int Int(const char* key, int fallback = 0) const { const Json* j = Get(key); return j && j->Kind == Number ? (int)j->Num : fallback; }
    std::string Text(const char* key) const { const Json* j = Get(key); return j && j->Kind == String ? j->Str : std::string(); }
};

static void AppendUtf8(std::string& out, unsigned int cp)
{
    if (cp < 0x80) out += (char)cp;
    else if (cp < 0x800) { out += (char)(0xC0 | (cp >> 6)); out += (char)(0x80 | (cp & 0x3F)); }
    else if (cp < 0x10000) { out += (char)(0xE0 | (cp >> 12)); out += (char)(0x80 | ((cp >> 6) & 0x3F)); out += (char)(0x80 | (cp & 0x3F)); }
    else { out += (char)(0xF0 | (cp >> 18)); out += (char)(0x80 | ((cp >> 12) & 0x3F)); out += (char)(0x80 | ((cp >> 6) & 0x3F)); out += (char)(0x80 | (cp & 0x3F)); }
}

// Recursive descent parser. Returns false on any syntax error: a host must not trust the other side blindly.
struct JsonParser
{
    const char* p;
    const char* end;

    void Skip() { while (p < end && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')) p++; }

    bool Hex4(unsigned int& v)
    {
        if (end - p < 4) return false;
        v = 0;
        for (int i = 0; i < 4; i++, p++)
        {
            char c = *p;
            v <<= 4;
            if (c >= '0' && c <= '9') v |= c - '0';
            else if (c >= 'a' && c <= 'f') v |= c - 'a' + 10;
            else if (c >= 'A' && c <= 'F') v |= c - 'A' + 10;
            else return false;
        }
        return true;
    }

    bool ParseString(std::string& out)
    {
        if (p >= end || *p != '"') return false;
        p++;
        while (p < end && *p != '"')
        {
            if (*p != '\\') { out += *p++; continue; }
            p++;
            if (p >= end) return false;
            char c = *p++;
            switch (c)
            {
            case '"': out += '"'; break;
            case '\\': out += '\\'; break;
            case '/': out += '/'; break;
            case 'b': out += '\b'; break;
            case 'f': out += '\f'; break;
            case 'n': out += '\n'; break;
            case 'r': out += '\r'; break;
            case 't': out += '\t'; break;
            case 'u':
            {
                unsigned int cp;
                if (!Hex4(cp)) return false;
                if (cp >= 0xD800 && cp < 0xDC00 && end - p >= 6 && p[0] == '\\' && p[1] == 'u')    // a surrogate pair is one code point
                {
                    p += 2;
                    unsigned int low;
                    if (!Hex4(low)) return false;
                    cp = 0x10000 + ((cp - 0xD800) << 10) + (low - 0xDC00);
                }
                AppendUtf8(out, cp);
                break;
            }
            default: return false;
            }
        }
        if (p >= end) return false;
        p++;
        return true;
    }

    bool ParseValue(Json& v, int depth = 0)
    {
        if (depth > 32) return false;
        Skip();
        if (p >= end) return false;
        if (*p == '"') { v.Kind = Json::String; return ParseString(v.Str); }
        if (*p == '{' || *p == '[')
        {
            bool object = *p == '{';
            char close = object ? '}' : ']';
            v.Kind = object ? Json::Object : Json::Array;
            p++;
            Skip();
            if (p < end && *p == close) { p++; return true; }
            for (;;)
            {
                Skip();
                if (object)
                {
                    std::string key;
                    if (!ParseString(key)) return false;
                    Skip();
                    if (p >= end || *p++ != ':') return false;
                    v.Keys.push_back(key);
                }
                v.Items.emplace_back();
                if (!ParseValue(v.Items.back(), depth + 1)) return false;
                Skip();
                if (p < end && *p == ',') { p++; continue; }
                if (p < end && *p == close) { p++; return true; }
                return false;
            }
        }
        if (!strncmp(p, "true", 4)) { v.Kind = Json::Bool; v.Flag = true; p += 4; return true; }
        if (!strncmp(p, "false", 5)) { v.Kind = Json::Bool; p += 5; return true; }
        if (!strncmp(p, "null", 4)) { p += 4; return true; }
        char* number_end;
        v.Num = strtod(p, &number_end);
        if (number_end == p) return false;
        v.Kind = Json::Number;
        p = number_end;
        return true;
    }
};

static bool ParseJson(const std::string& text, Json& out)
{
    JsonParser parser = { text.c_str(), text.c_str() + text.size() };
    return parser.ParseValue(out);
}

// A JSON string literal. The line breaks of the text are written as \n, so a request is always ONE line.
static std::string JsonString(const std::string& s)
{
    std::string out = "\"";
    for (unsigned char c : s)
    {
        if (c == '"') out += "\\\"";
        else if (c == '\\') out += "\\\\";
        else if (c == '\n') out += "\\n";
        else if (c == '\r') out += "\\r";
        else if (c == '\t') out += "\\t";
        else if (c < 0x20) { char buf[8]; snprintf(buf, sizeof(buf), "\\u%04x", c); out += buf; }
        else out += (char)c;                                  // UTF-8 bytes go through unchanged: JSON text is UTF-8
    }
    return out + "\"";
}

// [SECTION] The engine process

struct EngineProcess
{
#ifdef _WIN32
    HANDLE ToChild = NULL, FromChild = NULL, Process = NULL;
#else
    int ToChild = -1, FromChild = -1;
    pid_t Pid = -1;
#endif
    std::string Pending;                                      // bytes read after the last line break

    // Starts "python -m grammar_engine --serve" in engine_dir. On failure returns false and fills `error`.
    bool Start(const std::string& engine_dir, std::string& error)
    {
#ifdef _WIN32
        SECURITY_ATTRIBUTES sa = { sizeof(sa), NULL, TRUE };  // the child inherits the handles we give it
        HANDLE in_read, in_write, out_read, out_write;
        if (!CreatePipe(&in_read, &in_write, &sa, 0) || !CreatePipe(&out_read, &out_write, &sa, 0))
        {
            error = "Cannot create the pipes.";
            return false;
        }
        SetHandleInformation(in_write, HANDLE_FLAG_INHERIT, 0);   // our ends must not leak into the child
        SetHandleInformation(out_read, HANDLE_FLAG_INHERIT, 0);
        HANDLE nul = CreateFileA("NUL", GENERIC_WRITE, FILE_SHARE_WRITE, &sa, OPEN_EXISTING, 0, NULL);    // the child's error output is not read
        STARTUPINFOA si = {};
        si.cb = sizeof(si);
        si.dwFlags = STARTF_USESTDHANDLES;
        si.hStdInput = in_read;
        si.hStdOutput = out_write;
        si.hStdError = nul;
        PROCESS_INFORMATION pi = {};
        char command[] = "python -m grammar_engine --serve";    // CreateProcess may edit this buffer: it must be writable
        BOOL ok = CreateProcessA(NULL, command, NULL, NULL, TRUE, CREATE_NO_WINDOW, NULL, engine_dir.c_str(), &si, &pi);
        CloseHandle(in_read);                                     // the child holds its ends now
        CloseHandle(out_write);
        CloseHandle(nul);
        if (!ok)
        {
            CloseHandle(in_write);
            CloseHandle(out_read);
            error = "Cannot start Python (is it on the PATH?).";
            return false;
        }
        CloseHandle(pi.hThread);
        ToChild = in_write;
        FromChild = out_read;
        Process = pi.hProcess;
        return true;
#else
        int to[2], from[2];
        if (pipe(to) || pipe(from))
        {
            error = "Cannot create the pipes.";
            return false;
        }
        Pid = fork();
        if (Pid == 0)                                             // child: pipes become stdin and stdout, then python takes over
        {
            dup2(to[0], 0);
            dup2(from[1], 1);
            close(to[0]); close(to[1]); close(from[0]); close(from[1]);
            if (chdir(engine_dir.c_str()) == 0)
                execlp("python3", "python3", "-m", "grammar_engine", "--serve", (char*)NULL);
            _exit(127);                                           // exec failed
        }
        close(to[0]);
        close(from[1]);
        if (Pid < 0)
        {
            error = "Cannot start Python.";
            return false;
        }
        ToChild = to[1];
        FromChild = from[0];
        return true;
#endif
    }

    bool Running() const
    {
#ifdef _WIN32
        return Process != NULL;
#else
        return Pid > 0;
#endif
    }

    // Sends one line and waits for one line. False when the process is gone.
    bool Ask(const std::string& request_line, std::string& answer_line)
    {
        std::string out = request_line + "\n";
#ifdef _WIN32
        DWORD done;
        if (!WriteFile(ToChild, out.data(), (DWORD)out.size(), &done, NULL))
            return false;
#else
        if (write(ToChild, out.data(), out.size()) != (ssize_t)out.size())
            return false;
#endif
        for (;;)
        {
            size_t eol = Pending.find('\n');
            if (eol != std::string::npos)
            {
                answer_line = Pending.substr(0, eol);
                Pending.erase(0, eol + 1);
                return true;
            }
            char buf[4096];
#ifdef _WIN32
            DWORD got = 0;
            if (!ReadFile(FromChild, buf, sizeof(buf), &got, NULL) || got == 0)
                return false;
            Pending.append(buf, got);
#else
            ssize_t got = read(FromChild, buf, sizeof(buf));
            if (got <= 0)
                return false;
            Pending.append(buf, (size_t)got);
#endif
        }
    }

    void Stop()
    {
#ifdef _WIN32
        if (!Process) return;
        CloseHandle(ToChild);                                     // the end of the input ends the loop of the engine
        if (WaitForSingleObject(Process, 3000) != WAIT_OBJECT_0)
            TerminateProcess(Process, 1);
        CloseHandle(Process);
        CloseHandle(FromChild);
        Process = NULL;
#else
        if (Pid <= 0) return;
        close(ToChild);
        waitpid(Pid, NULL, 0);
        close(FromChild);
        Pid = -1;
#endif
    }
};

// [SECTION] The checker: a request, and the list of problems

struct Problem
{
    int Paragraph;
    int ByteStart, ByteEnd;                                       // in UTF-8 bytes, in the whole text
    std::string Text, Suggestion, Message, Rule;
};

// One request {"id", "lang", "ui", "text"}; fills `problems`. Returns an error text, or an empty string.
static std::string RunCheck(EngineProcess& engine, const std::string& engine_dir, int id, const std::string& lang, const std::string& ui, const std::string& text, std::vector<Problem>& problems)
{
    std::string error;
    if (!engine.Running() && !engine.Start(engine_dir, error))
        return error;
    std::string request = "{\"id\": " + std::to_string(id) + ", \"lang\": " + JsonString(lang) + ", \"ui\": " + JsonString(ui) + ", \"text\": " + JsonString(text) + "}";
    std::string line;
    if (!engine.Ask(request, line))
    {
        engine.Stop();                                            // the next check starts a new process
        return "The engine stopped.";
    }
    Json answer;
    if (!ParseJson(line, answer) || answer.Kind != Json::Object)
        return "Invalid answer from the engine.";
    const Json* err = answer.Get("error");
    if (err)
        return err->Str;
    const Json* issues = answer.Get("issues");
    if (!issues || issues->Kind != Json::Array)
        return "The answer has no issues.";
    problems.clear();
    for (const Json& issue : issues->Items)
    {
        Problem p;
        p.Paragraph = issue.Int("paragraph");
        p.ByteStart = issue.Int("byte_start");
        p.ByteEnd = issue.Int("byte_end");
        p.Text = issue.Text("text");
        const Json* suggestions = issue.Get("suggestions");
        p.Suggestion = suggestions && !suggestions->Items.empty() ? suggestions->Items[0].Str : std::string();
        p.Message = issue.Text("message");
        p.Rule = issue.Text("rule");
        problems.push_back(p);
    }
    return std::string();
}

static bool ReadFileUtf8(const char* path, std::string& out)
{
    FILE* f = fopen(path, "rb");
    if (!f)
        return false;
    char buf[4096];
    size_t n;
    out.clear();
    while ((n = fread(buf, 1, sizeof(buf), f)) > 0)
        out.append(buf, n);
    fclose(f);
    if (out.size() >= 3 && !memcmp(out.data(), "\xEF\xBB\xBF", 3))        // a UTF-8 byte order mark is not part of the text
        out.erase(0, 3);
    std::string clean;                                                     // line breaks: the engine splits on \n
    for (char c : out)
        if (c != '\r')
            clean += c;
    while (!clean.empty() && clean.back() == '\n')
        clean.pop_back();
    out = clean;
    return true;
}

// The folder which holds the package grammar_engine: GRAMMAR_ENGINE_DIR, else the one given at build time.
static std::string EngineDir()
{
    const char* env = getenv("GRAMMAR_ENGINE_DIR");
    return env && *env ? env : GRAMMAR_ENGINE_DIR;
}

// [SECTION] The window

struct App
{
    char TextBuf[1 << 18] = "";
    char PathBuf[512] = "";
    int Language = 0, Ui = 0;
    std::vector<Problem> Problems;
    std::string Status = "Type or load a text, then press Check.";
    int SelectedRow = -1;
    int SelectStart = -1, SelectEnd = -1;                     // a selection waiting for the text widget to take it

    EngineProcess Engine;
    std::thread Worker;
    std::atomic<bool> Busy{ false };
    std::mutex Lock;                                          // protects the three members below, written by the worker
    std::vector<Problem> Result;
    std::string ResultError;
    bool ResultReady = false;
    int NextId = 1;
};

static const char* Languages[] = { "fr", "en", "es", "es-AR" };
static const char* UiLanguages[] = { "en", "fr", "es" };

static void StartCheck(App& app)
{
    if (app.Busy)
        return;
    if (app.Worker.joinable())
        app.Worker.join();
    app.Busy = true;
    app.Status = "Checking...";
    std::string text = app.TextBuf, lang = Languages[app.Language], ui = UiLanguages[app.Ui];
    int id = app.NextId++;
    // The worker never touches ImGui: it fills app.Result under the lock and the frame loop picks it up.
    app.Worker = std::thread([&app, text, lang, ui, id]() {
        std::vector<Problem> problems;
        std::string error = RunCheck(app.Engine, EngineDir(), id, lang, ui, text, problems);
        std::lock_guard<std::mutex> guard(app.Lock);
        app.Result = problems;
        app.ResultError = error;
        app.ResultReady = true;
        app.Busy = false;
    });
}

static void LoadFile(App& app, const char* path)
{
    std::string text;
    if (!ReadFileUtf8(path, text))
    {
        app.Status = std::string("Cannot read ") + path;
        return;
    }
    snprintf(app.TextBuf, sizeof(app.TextBuf), "%s", text.c_str());
    for (int i = 0; i < 4; i++)                               // fr.txt, en.txt, es.txt: the name tells the language
    {
        std::string name = std::string(Languages[i]) + ".txt";
        if (strlen(path) >= name.size() && !strcmp(path + strlen(path) - name.size(), name.c_str()))
            app.Language = i;
    }
    StartCheck(app);
}

// Called by the text widget at every frame: this is where a selection can be set.
static int OnTextEdit(ImGuiInputTextCallbackData* data)
{
    App* app = (App*)data->UserData;
    if (app->SelectStart >= 0)
    {
        data->SelectionStart = app->SelectStart;              // ImGui counts in bytes of its UTF-8 buffer
        data->SelectionEnd = app->SelectEnd;
        data->CursorPos = app->SelectEnd;
        app->SelectStart = -1;
    }
    return 0;
}

static void DrawWindow(App& app)
{
    {   // The worker's answer, if it has finished
        std::lock_guard<std::mutex> guard(app.Lock);
        if (app.ResultReady)
        {
            app.ResultReady = false;
            if (app.ResultError.empty())
            {
                app.Problems = app.Result;
                app.SelectedRow = -1;
                app.Status = app.Problems.empty() ? "No problem found." : std::to_string(app.Problems.size()) + " problem(s).";
            }
            else
                app.Status = "Error: " + app.ResultError;
        }
    }

    ImGuiViewport* viewport = ImGui::GetMainViewport();
    ImGui::SetNextWindowPos(viewport->WorkPos);
    ImGui::SetNextWindowSize(viewport->WorkSize);
    ImGui::Begin("Grammar window", NULL, ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoCollapse);

    ImGui::SetNextItemWidth(260);
    ImGui::InputText("##path", app.PathBuf, sizeof(app.PathBuf));
    ImGui::SameLine();
    if (ImGui::Button("Load file"))
        LoadFile(app, app.PathBuf);
    ImGui::SameLine();
    ImGui::SetNextItemWidth(70);
    ImGui::Combo("Text", &app.Language, Languages, IM_ARRAYSIZE(Languages));
    ImGui::SameLine();
    ImGui::SetNextItemWidth(60);
    ImGui::Combo("Messages", &app.Ui, UiLanguages, IM_ARRAYSIZE(UiLanguages));
    ImGui::SameLine();
    ImGui::BeginDisabled(app.Busy);
    if (ImGui::Button("Check"))
        StartCheck(app);
    ImGui::EndDisabled();
    ImGui::SameLine();
    ImGui::TextUnformatted(app.Status.c_str());

    float height = ImGui::GetContentRegionAvail().y;
    if (app.SelectStart >= 0)
        ImGui::SetKeyboardFocusHere();                        // a selection only shows in the widget which has the focus
    ImGui::InputTextMultiline("##text", app.TextBuf, sizeof(app.TextBuf), ImVec2(-1, height * 0.5f), ImGuiInputTextFlags_CallbackAlways, OnTextEdit, &app);

    if (ImGui::BeginTable("problems", 5, ImGuiTableFlags_Borders | ImGuiTableFlags_RowBg | ImGuiTableFlags_ScrollY | ImGuiTableFlags_Resizable))
    {
        ImGui::TableSetupScrollFreeze(0, 1);
        ImGui::TableSetupColumn("Line", ImGuiTableColumnFlags_WidthFixed, 45);
        ImGui::TableSetupColumn("Text", ImGuiTableColumnFlags_WidthFixed, 150);
        ImGui::TableSetupColumn("Suggestion", ImGuiTableColumnFlags_WidthFixed, 150);
        ImGui::TableSetupColumn("Message", ImGuiTableColumnFlags_WidthStretch);
        ImGui::TableSetupColumn("Rule", ImGuiTableColumnFlags_WidthFixed, 130);
        ImGui::TableHeadersRow();
        for (int i = 0; i < (int)app.Problems.size(); i++)
        {
            const Problem& p = app.Problems[i];
            ImGui::TableNextRow();
            ImGui::TableNextColumn();
            ImGui::PushID(i);
            char line[16];
            snprintf(line, sizeof(line), "%d", p.Paragraph + 1);
            if (ImGui::Selectable(line, app.SelectedRow == i, ImGuiSelectableFlags_SpanAllColumns))
            {
                app.SelectedRow = i;
                app.SelectStart = p.ByteStart;                // handed to OnTextEdit at the next frame
                app.SelectEnd = p.ByteEnd;
            }
            ImGui::PopID();
            ImGui::TableNextColumn(); ImGui::TextUnformatted(p.Text.c_str());
            ImGui::TableNextColumn(); ImGui::TextUnformatted(p.Suggestion.empty() ? "(delete)" : p.Suggestion.c_str());
            ImGui::TableNextColumn(); ImGui::TextUnformatted(p.Message.c_str());
            ImGui::TableNextColumn(); ImGui::TextUnformatted(p.Rule.c_str());
        }
        ImGui::EndTable();
    }
    ImGui::End();
}

int main(int argc, char** argv)
{
    // Without a window: check a file and print the problems. Used to test the protocol code alone.
    if (argc >= 4 && !strcmp(argv[1], "--selftest"))
    {
        std::string text;
        if (!ReadFileUtf8(argv[2], text))
            return 2;
        EngineProcess engine;
        std::vector<Problem> problems;
        std::string error = RunCheck(engine, EngineDir(), 1, argv[3], "en", text, problems);
        engine.Stop();
        if (!error.empty())
        {
            printf("error: %s\n", error.c_str());
            return 1;
        }
        for (const Problem& p : problems)
        {
            bool inside = p.ByteEnd <= (int)text.size() && text.substr(p.ByteStart, p.ByteEnd - p.ByteStart) == p.Text;      // the byte range really holds the text
            printf("%d\t%s\t%s\t%s\t%s\n", p.Paragraph + 1, p.Text.c_str(), p.Suggestion.c_str(), p.Rule.c_str(), inside ? "ok" : "BAD RANGE");
        }
        printf("%d problem(s)\n", (int)problems.size());
        return 0;
    }

    if (!glfwInit())
        return 1;
    GLFWwindow* window = glfwCreateWindow(1000, 660, "Grammar window (C++ / ImGui)", NULL, NULL);
    if (!window)
        return 1;
    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.IniFilename = NULL;
    // The default font has the Latin-1 letters (é, ñ, ¿): enough for French and Spanish. A TTF with more glyphs would be loaded here.
    ImGui::StyleColorsLight();
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 130");

    static App app;                                           // static: it is large (the text buffer)
    std::string first = argc >= 2 ? argv[1] : EngineDir() + "/examples/sample_texts/fr.txt";
    snprintf(app.PathBuf, sizeof(app.PathBuf), "%s", first.c_str());
    LoadFile(app, app.PathBuf);

    while (!glfwWindowShouldClose(window))
    {
        glfwPollEvents();
        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplGlfw_NewFrame();
        ImGui::NewFrame();
        DrawWindow(app);
        ImGui::Render();
        int w, h;
        glfwGetFramebufferSize(window, &w, &h);
        glViewport(0, 0, w, h);
        glClearColor(0.94f, 0.94f, 0.94f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
        glfwSwapBuffers(window);
    }

    if (app.Worker.joinable())
        app.Worker.join();
    app.Engine.Stop();                                        // stop the child process with the window
    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplGlfw_Shutdown();
    ImGui::DestroyContext();
    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}
