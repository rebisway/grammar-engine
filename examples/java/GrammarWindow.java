// Grammar window in Java (Swing), the engine in another process.
//
// What it shows:
//   - how to start "python -m grammar_engine --serve" with ProcessBuilder and talk to it in JSON lines;
//   - a small JSON reader (the JDK has none) and the escaping of a JSON string;
//   - how to keep Swing responsive: the request runs in a SwingWorker, the result is shown on the event thread;
//   - how to convert the code point positions of the engine to the UTF-16 positions of a JTextArea
//     (String.offsetByCodePoints).
//
// Build and run (Java 8 or later, no library):
//     javac GrammarWindow.java
//     java GrammarWindow [file.txt]
//
// SPDX-License-Identifier: MIT

import java.awt.BorderLayout;
import java.awt.FlowLayout;
import java.awt.Font;
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import javax.swing.JButton;
import javax.swing.JComboBox;
import javax.swing.JFileChooser;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JSplitPane;
import javax.swing.JTable;
import javax.swing.JTextArea;
import javax.swing.ListSelectionModel;
import javax.swing.SwingUtilities;
import javax.swing.SwingWorker;
import javax.swing.table.DefaultTableModel;

public class GrammarWindow extends JFrame
{
    private static final long serialVersionUID = 1L;

    // [SECTION] A minimal JSON reader: objects become Map, arrays List, strings String, numbers Double, true/false Boolean, null null.

    static final class Json
    {
        private final String s;
        private int i = 0;

        private Json(String s) { this.s = s; }

        // Parses a whole text. Throws IllegalArgumentException on a syntax error: never trust the other side blindly.
        static Object parse(String text)
        {
            Json p = new Json(text);
            Object value = p.value();
            p.skip();
            if (p.i != p.s.length())
                throw new IllegalArgumentException("Extra text after the JSON value");
            return value;
        }

        private void skip() { while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++; }

        private Object value()
        {
            skip();
            if (i >= s.length())
                throw new IllegalArgumentException("Unexpected end");
            char c = s.charAt(i);
            if (c == '{')
            {
                Map<String, Object> map = new LinkedHashMap<String, Object>();
                i++;
                skip();
                if (s.charAt(i) == '}') { i++; return map; }
                for (;;)
                {
                    skip();
                    String key = string();
                    skip();
                    expect(':');
                    map.put(key, value());
                    skip();
                    if (s.charAt(i) == ',') { i++; continue; }
                    expect('}');
                    return map;
                }
            }
            if (c == '[')
            {
                List<Object> list = new ArrayList<Object>();
                i++;
                skip();
                if (s.charAt(i) == ']') { i++; return list; }
                for (;;)
                {
                    list.add(value());
                    skip();
                    if (s.charAt(i) == ',') { i++; continue; }
                    expect(']');
                    return list;
                }
            }
            if (c == '"') return string();
            if (s.startsWith("true", i)) { i += 4; return Boolean.TRUE; }
            if (s.startsWith("false", i)) { i += 5; return Boolean.FALSE; }
            if (s.startsWith("null", i)) { i += 4; return null; }
            int start = i;
            while (i < s.length() && "+-0123456789.eE".indexOf(s.charAt(i)) >= 0) i++;
            if (start == i)
                throw new IllegalArgumentException("Unexpected character at " + i);
            return Double.valueOf(s.substring(start, i));
        }

        private void expect(char c)
        {
            if (i >= s.length() || s.charAt(i) != c)
                throw new IllegalArgumentException("Expected '" + c + "' at " + i);
            i++;
        }

        private String string()
        {
            expect('"');
            StringBuilder out = new StringBuilder();
            while (i < s.length() && s.charAt(i) != '"')
            {
                char c = s.charAt(i++);
                if (c != '\\') { out.append(c); continue; }
                char e = s.charAt(i++);
                switch (e)
                {
                    case 'n': out.append('\n'); break;
                    case 't': out.append('\t'); break;
                    case 'r': out.append('\r'); break;
                    case 'b': out.append('\b'); break;
                    case 'f': out.append('\f'); break;
                    // A unicode escape (backslash, u, four hex digits) gives one UTF-16 unit: a character outside the BMP comes as two, which append() keeps.
                    case 'u': out.append((char) Integer.parseInt(s.substring(i, i + 4), 16)); i += 4; break;
                    default: out.append(e);                      // \" \\ \/
                }
            }
            expect('"');
            return out.toString();
        }
    }

    // A JSON string literal. The line breaks of the text become \n, so a request is always ONE line.
    static String quote(String text)
    {
        StringBuilder out = new StringBuilder("\"");
        for (int k = 0; k < text.length(); k++)
        {
            char c = text.charAt(k);
            switch (c)
            {
                case '"': out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (c < 0x20) out.append(String.format("\\u%04x", (int) c)); else out.append(c);
            }
        }
        return out.append('"').toString();
    }

    // [SECTION] The engine process

    // One problem, as the window needs it.
    static final class Problem
    {
        int paragraph, start, end;          // start and end: code points in the whole text
        String text, suggestion, message, rule;
    }

    static final class Engine
    {
        private final File dir;
        private Process process;
        private BufferedWriter toEngine;
        private BufferedReader fromEngine;
        private int nextId = 1;

        Engine(File dir) { this.dir = dir; }

        private void start() throws IOException
        {
            ProcessBuilder builder = new ProcessBuilder(System.getProperty("os.name").startsWith("Windows") ? "python" : "python3", "-m", "grammar_engine", "--serve");
            builder.directory(dir);                                  // the folder which contains the package grammar_engine
            builder.redirectErrorStream(false);
            process = builder.start();                               // IOException if Python is not installed
            // The protocol is UTF-8 on both pipes, whatever the default charset of the JVM is.
            toEngine = new BufferedWriter(new OutputStreamWriter(process.getOutputStream(), StandardCharsets.UTF_8));
            fromEngine = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));
        }

        // Sends {"id", "lang", "ui", "text"}, waits for the answer line and returns the problems. Called from a worker thread.
        synchronized List<Problem> check(String lang, String ui, String text) throws IOException
        {
            if (process == null)
                start();
            int id = nextId++;
            toEngine.write("{\"id\": " + id + ", \"lang\": " + quote(lang) + ", \"ui\": " + quote(ui) + ", \"text\": " + quote(text) + "}\n");
            toEngine.flush();
            String line = fromEngine.readLine();
            if (line == null)                                        // the process ended
            {
                stop();
                throw new IOException("The engine stopped.");
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> answer = (Map<String, Object>) Json.parse(line);
            if (answer.containsKey("error"))
                throw new IOException(String.valueOf(answer.get("error")));
            List<Problem> problems = new ArrayList<Problem>();
            @SuppressWarnings("unchecked")
            List<Object> issues = (List<Object>) answer.get("issues");
            for (Object o : issues)
            {
                @SuppressWarnings("unchecked")
                Map<String, Object> issue = (Map<String, Object>) o;
                Problem p = new Problem();
                p.paragraph = ((Double) issue.get("paragraph")).intValue();
                p.start = ((Double) issue.get("start")).intValue();
                p.end = ((Double) issue.get("end")).intValue();
                p.text = (String) issue.get("text");
                List<?> suggestions = (List<?>) issue.get("suggestions");
                p.suggestion = suggestions.isEmpty() ? "" : (String) suggestions.get(0);     // empty = delete the text
                p.message = (String) issue.get("message");
                p.rule = (String) issue.get("rule");
                problems.add(p);
            }
            return problems;
        }

        synchronized void stop()
        {
            if (process == null)
                return;
            try { toEngine.close(); } catch (IOException ignored) { }     // the end of the input ends the loop of the engine
            process.destroy();
            process = null;
        }
    }

    // [SECTION] The window

    private final File engineDir;
    private final File samples;
    private final Engine engine;
    private final JTextArea editor = new JTextArea();
    private final DefaultTableModel model = new DefaultTableModel(new Object[] { "Line", "Text", "Suggestion", "Message", "Rule" }, 0)
    {
        @Override public boolean isCellEditable(int row, int column) { return false; }
    };
    private final JTable table = new JTable(model);
    private final JComboBox<String> language = new JComboBox<String>(new String[] { "fr", "en", "es", "es-AR" });
    private final JComboBox<String> ui = new JComboBox<String>(new String[] { "en", "fr", "es" });
    private final JButton checkButton = new JButton("Check");
    private final JLabel status = new JLabel("Open a file or paste a text, then press Check.");
    private List<Problem> problems = new ArrayList<Problem>();

    GrammarWindow(String path)
    {
        super("Grammar window (Java)");
        // The engine is the folder two levels up from this one (grammar-engine/examples/java), or GRAMMAR_ENGINE_DIR.
        String env = System.getenv("GRAMMAR_ENGINE_DIR");
        engineDir = env != null && !env.isEmpty() ? new File(env) : new File(System.getProperty("user.dir")).getAbsoluteFile().getParentFile().getParentFile();
        samples = new File(engineDir, "examples" + File.separator + "sample_texts");
        engine = new Engine(engineDir);

        editor.setLineWrap(true);
        editor.setWrapStyleWord(true);
        editor.setFont(new Font("SansSerif", Font.PLAIN, 14));
        editor.getCaret().setSelectionVisible(true);                 // keep the selection visible when the focus is in the table

        JButton open = new JButton("Open...");
        open.addActionListener(e -> openFile());
        checkButton.addActionListener(e -> check());
        JPanel bar = new JPanel(new FlowLayout(FlowLayout.LEFT));
        bar.add(open);
        bar.add(new JLabel("Text language:"));
        bar.add(language);
        bar.add(new JLabel("Messages:"));
        bar.add(ui);
        bar.add(checkButton);
        bar.add(status);

        table.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        table.getSelectionModel().addListSelectionListener(e -> { if (!e.getValueIsAdjusting()) showSelected(); });   // a click selects the passage
        int[] widths = { 50, 160, 160, 480, 130 };
        for (int k = 0; k < widths.length; k++)
            table.getColumnModel().getColumn(k).setPreferredWidth(widths[k]);

        getContentPane().setLayout(new BorderLayout());
        getContentPane().add(bar, BorderLayout.NORTH);
        getContentPane().add(new JSplitPane(JSplitPane.VERTICAL_SPLIT, new JScrollPane(editor), new JScrollPane(table)), BorderLayout.CENTER);
        setSize(1000, 660);
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        addWindowListener(new java.awt.event.WindowAdapter()
        {
            @Override public void windowClosing(java.awt.event.WindowEvent e) { engine.stop(); }       // stop the child process with the window
        });

        load(path != null ? new File(path) : new File(samples, "fr.txt"));
    }

    private void openFile()
    {
        JFileChooser chooser = new JFileChooser(samples);
        if (chooser.showOpenDialog(this) == JFileChooser.APPROVE_OPTION)
            load(chooser.getSelectedFile());
    }

    private void load(File file)
    {
        try
        {
            String text = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);     // the engine works on UTF-8 text
            editor.setText(text.replace("\r\n", "\n").replaceAll("\\n+$", ""));
            String stem = file.getName().replaceFirst("\\.[^.]*$", "");     // fr.txt, en.txt, es.txt: the name tells the language
            for (int k = 0; k < language.getItemCount(); k++)
                if (language.getItemAt(k).equals(stem))
                    language.setSelectedIndex(k);
            check();
        }
        catch (IOException e)
        {
            JOptionPane.showMessageDialog(this, "Cannot read " + file + "\n" + e.getMessage());
        }
    }

    private void check()
    {
        checkButton.setEnabled(false);
        status.setText("Checking...");
        final String text = editor.getText();                         // JTextArea uses \n for line breaks, as the engine expects
        final String lang = (String) language.getSelectedItem(), messages = (String) ui.getSelectedItem();
        // SwingWorker: doInBackground runs in another thread, done() runs back on the event thread.
        new SwingWorker<List<Problem>, Void>()
        {
            @Override protected List<Problem> doInBackground() throws Exception { return engine.check(lang, messages, text); }

            @Override protected void done()
            {
                checkButton.setEnabled(true);
                try
                {
                    problems = get();
                    model.setRowCount(0);
                    for (Problem p : problems)
                        model.addRow(new Object[] { p.paragraph + 1, p.text, p.suggestion.isEmpty() ? "(delete)" : p.suggestion, p.message, p.rule });
                    status.setText(problems.isEmpty() ? "No problem found." : problems.size() + " problem(s).");
                }
                catch (Exception e)
                {
                    engine.stop();                                    // the next check starts a new process
                    status.setText("Error: " + (e.getCause() != null ? e.getCause().getMessage() : e.getMessage()));
                }
            }
        }.execute();
    }

    private void showSelected()
    {
        int row = table.getSelectedRow();
        if (row < 0 || row >= problems.size())
            return;
        Problem p = problems.get(row);
        String text = editor.getText();
        // The engine counts code points, a Java String counts UTF-16 units: offsetByCodePoints converts.
        int start = text.offsetByCodePoints(0, Math.min(p.start, text.codePointCount(0, text.length())));
        int end = text.offsetByCodePoints(0, Math.min(p.end, text.codePointCount(0, text.length())));
        editor.select(start, end);
        editor.getCaret().setSelectionVisible(true);
    }

    public static void main(final String[] args)
    {
        SwingUtilities.invokeLater(() -> new GrammarWindow(args.length > 0 ? args[0] : null).setVisible(true));
    }
}
