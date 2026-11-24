// Grammar window in C# (Windows Forms, .NET 8 or later).
//
// What it shows:
//   - how to start "python -m grammar_engine --serve" as a child process and talk to it in JSON lines;
//   - how to keep the window responsive: every request runs with Task.Run and the window only awaits the result;
//   - how to turn the positions of the engine into positions in a RichTextBox. The engine counts in Unicode code points
//     (and in UTF-8 bytes), .NET strings are UTF-16: a character outside the Basic Multilingual Plane (an emoji) is two
//     chars, so a position must be converted. The helper Utf16Index does it.
//
// Build and run:   dotnet run          (from this folder; needs Python 3.9+ on the PATH)
//
// SPDX-License-Identifier: MIT

using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace GrammarWindow;

// One problem found by the engine, as the window needs it.
record Problem(int Start, int End, int Paragraph, string Text, string Suggestion, string Message, string Rule);

// A client of the engine. It owns the child process and exchanges one JSON line per request and per answer.
sealed class EngineClient : IDisposable
{
    private readonly Process process;
    private readonly SemaphoreSlim gate = new(1, 1);    // one request at a time: answers come back in the order of the questions
    private int nextId = 1;

    public EngineClient(string engineDir)
    {
        var info = new ProcessStartInfo
        {
            FileName = OperatingSystem.IsWindows() ? "python" : "python3",
            WorkingDirectory = engineDir,               // the folder which contains the package grammar_engine
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,                    // needed to redirect the streams
            CreateNoWindow = true,                      // no console window flashing on the screen
            // The protocol is UTF-8 on both pipes, whatever the code page of the machine is.
            StandardInputEncoding = new UTF8Encoding(false),    // false: no byte order mark in front of the first request
            StandardOutputEncoding = new UTF8Encoding(false),
            StandardErrorEncoding = new UTF8Encoding(false),
        };
        info.ArgumentList.Add("-m");
        info.ArgumentList.Add("grammar_engine");
        info.ArgumentList.Add("--serve");
        try
        {
            process = Process.Start(info) ?? throw new InvalidOperationException("The process did not start.");
        }
        catch (System.ComponentModel.Win32Exception e)  // "python" is not on the PATH
        {
            throw new InvalidOperationException("Cannot start Python: " + e.Message);
        }
    }

    // Sends {"id", "lang", "ui", "text"} and returns the issues of the answer.
    public async Task<List<Problem>> CheckAsync(string language, string ui, string text)
    {
        await gate.WaitAsync();
        try
        {
            int id = nextId++;
            // Utf8JsonWriter / JsonSerializer escape the line breaks of the text, so the request stays on ONE line.
            string request = JsonSerializer.Serialize(new Dictionary<string, object> { ["id"] = id, ["lang"] = language, ["ui"] = ui, ["text"] = text });
            await process.StandardInput.WriteLineAsync(request);
            await process.StandardInput.FlushAsync();
            string? line = await process.StandardOutput.ReadLineAsync();
            if (line == null)                           // the process ended: its error output tells why
            {
                string reason = process.HasExited ? await process.StandardError.ReadToEndAsync() : "";
                throw new InvalidOperationException("The engine stopped. " + reason.Trim());
            }
            using JsonDocument answer = JsonDocument.Parse(line);   // throws JsonException if the line is not JSON
            JsonElement root = answer.RootElement;
            if (root.TryGetProperty("error", out JsonElement error))
                throw new InvalidOperationException(error.GetString());
            var problems = new List<Problem>();
            foreach (JsonElement issue in root.GetProperty("issues").EnumerateArray())
            {
                JsonElement suggestions = issue.GetProperty("suggestions");
                problems.Add(new Problem(
                    issue.GetProperty("start").GetInt32(), issue.GetProperty("end").GetInt32(),   // code points in the whole text
                    issue.GetProperty("paragraph").GetInt32(), issue.GetProperty("text").GetString() ?? "",
                    suggestions.GetArrayLength() > 0 ? suggestions[0].GetString() ?? "" : "",      // empty = delete the text
                    issue.GetProperty("message").GetString() ?? "", issue.GetProperty("rule").GetString() ?? ""));
            }
            return problems;
        }
        finally
        {
            gate.Release();
        }
    }

    public void Dispose()
    {
        try
        {
            process.StandardInput.Close();              // the end of the input ends the loop of the engine
            if (!process.WaitForExit(3000))
                process.Kill();
        }
        catch (InvalidOperationException) { }           // already gone
        process.Dispose();
    }
}

sealed class MainForm : Form
{
    private readonly string samples;
    private readonly string engineDir;
    private EngineClient? client;
    private List<Problem> problems = new();

    private readonly RichTextBox editor = new() { Dock = DockStyle.Fill, Font = new Font("Segoe UI", 11), HideSelection = false };
    private readonly ListView list = new() { Dock = DockStyle.Fill, View = View.Details, FullRowSelect = true, HideSelection = false, MultiSelect = false };
    private readonly ComboBox language = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 70 };
    private readonly ComboBox ui = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 60 };
    private readonly Button checkButton = new() { Text = "Check", AutoSize = true };
    private readonly Label status = new() { AutoSize = true, Padding = new Padding(8, 6, 0, 0), Text = "Open a file or paste a text, then press Check." };

    public MainForm()
    {
        Text = "Grammar window (C#)";
        Size = new Size(1000, 660);

        // The engine is the folder three levels up from the build output (grammar-engine/examples/csharp/bin/...), or two from the sources.
        // The environment variable GRAMMAR_ENGINE_DIR wins when it is set (useful when the program is copied elsewhere).
        string root = Environment.GetEnvironmentVariable("GRAMMAR_ENGINE_DIR") ?? AppContext.BaseDirectory;
        while (!string.IsNullOrEmpty(root) && !Directory.Exists(Path.Combine(root, "grammar_engine")))
            root = Path.GetDirectoryName(root.TrimEnd(Path.DirectorySeparatorChar)) ?? "";
        engineDir = root;
        samples = Path.Combine(engineDir, "examples", "sample_texts");

        // Tool bar
        var open = new Button { Text = "Open...", AutoSize = true };
        open.Click += (_, _) => OpenFile();
        language.Items.AddRange(new object[] { "fr", "en", "es", "es-AR" });
        language.SelectedIndex = 0;
        ui.Items.AddRange(new object[] { "en", "fr", "es" });
        ui.SelectedIndex = 0;
        checkButton.Click += async (_, _) => await RunCheck();
        var bar = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, Padding = new Padding(4) };
        bar.Controls.AddRange(new Control[] { open, new Label { Text = "Text language:", AutoSize = true, Padding = new Padding(8, 6, 0, 0) }, language,
                                              new Label { Text = "Messages:", AutoSize = true, Padding = new Padding(8, 6, 0, 0) }, ui, checkButton, status });

        // The list of problems: one row per problem
        foreach ((string name, int width) in new[] { ("Line", 50), ("Text", 160), ("Suggestion", 160), ("Message", 480), ("Rule", 130) })
            list.Columns.Add(name, width);
        list.SelectedIndexChanged += (_, _) => ShowSelected();      // a click on a problem selects the passage

        var split = new SplitContainer { Dock = DockStyle.Fill, Orientation = Orientation.Horizontal, SplitterDistance = 300 };
        split.Panel1.Controls.Add(editor);
        split.Panel2.Controls.Add(list);
        Controls.Add(split);
        Controls.Add(bar);                                          // added last, it docks above the split container

        Load += async (_, _) => { LoadFile(Path.Combine(samples, "fr.txt")); await RunCheck(); };
        FormClosed += (_, _) => client?.Dispose();                  // stop the child process with the window
    }

    private void OpenFile()
    {
        using var dialog = new OpenFileDialog { InitialDirectory = samples, Filter = "Text|*.txt;*.md|All files|*.*" };
        if (dialog.ShowDialog() == DialogResult.OK)
        {
            LoadFile(dialog.FileName);
            _ = RunCheck();
        }
    }

    private void LoadFile(string path)
    {
        try
        {
            editor.Text = File.ReadAllText(path, Encoding.UTF8).TrimEnd('\r', '\n').Replace("\r\n", "\n");
            string stem = Path.GetFileNameWithoutExtension(path);   // fr.txt, en.txt, es.txt: the name tells the language
            if (language.Items.Contains(stem))
                language.SelectedItem = stem;
        }
        catch (IOException e)
        {
            MessageBox.Show(this, "Cannot read " + path + "\n" + e.Message, Text);
        }
    }

    private async Task RunCheck()
    {
        checkButton.Enabled = false;
        status.Text = "Checking...";
        try
        {
            client ??= new EngineClient(engineDir);                 // started at the first check, kept for the next ones
            // The RichTextBox gives "\n" for a line break: the same character the engine splits the text on.
            string text = editor.Text;
            // Task.Run keeps the user interface free during the request; "await" comes back to the interface thread.
            problems = await Task.Run(() => client.CheckAsync((string)language.SelectedItem!, (string)ui.SelectedItem!, text));
            list.Items.Clear();
            foreach (Problem p in problems)
                list.Items.Add(new ListViewItem(new[] { (p.Paragraph + 1).ToString(), p.Text, p.Suggestion.Length > 0 ? p.Suggestion : "(delete)", p.Message, p.Rule }));
            status.Text = problems.Count > 0 ? problems.Count + " problem(s)." : "No problem found.";
        }
        catch (Exception e) when (e is InvalidOperationException or JsonException or IOException)
        {
            client?.Dispose();
            client = null;                                          // the next check starts a new process
            status.Text = "Error: " + e.Message;
        }
        finally
        {
            checkButton.Enabled = true;
        }
    }

    // Converts a position counted in code points to a position in the UTF-16 string.
    private static int Utf16Index(string s, int codePoints)
    {
        int index = 0;
        for (int n = 0; n < codePoints && index < s.Length; n++)
            index += char.IsHighSurrogate(s[index]) && index + 1 < s.Length ? 2 : 1;
        return index;
    }

    private void ShowSelected()
    {
        if (list.SelectedIndices.Count == 0)
            return;
        Problem p = problems[list.SelectedIndices[0]];
        string text = editor.Text;
        int start = Utf16Index(text, p.Start);
        int end = Utf16Index(text, p.End);
        editor.Select(start, end - start);                          // selects the passage in the text
        editor.ScrollToCaret();
    }
}

static class Program
{
    [STAThread]
    static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
    }
}
