# Grammar window in PowerShell (Windows Forms, Windows PowerShell 5.1 or PowerShell 7 on Windows).
#
# What it shows:
#   - how to start "python -m grammar_engine --serve" and talk to it in JSON lines, with the .NET Process class;
#   - how to keep the window responsive WITHOUT threads: the read of the answer is a Task (ReadLineAsync) and a Timer
#     looks every 100 ms whether it has finished;
#   - how to convert the code point positions of the engine to the UTF-16 positions of a RichTextBox.
#
# Run it:   powershell -ExecutionPolicy Bypass -File grammar_window.ps1 [file.txt]
# It needs Python 3.9+ on the PATH.
#
# SPDX-License-Identifier: MIT

param([string]$Path)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

# The engine is the folder two levels up from this script (grammar-engine/); GRAMMAR_ENGINE_DIR overrides it.
$EngineDir = if ($env:GRAMMAR_ENGINE_DIR) { $env:GRAMMAR_ENGINE_DIR } else { (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
$Samples = Join-Path $EngineDir 'examples\sample_texts'
$Utf8 = New-Object System.Text.UTF8Encoding($false)      # UTF-8 without a byte order mark

# ---- The engine process ----------------------------------------------------------------------------------------

$script:Engine = $null       # the Process, started at the first check
$script:Reader = $null       # a StreamReader on its output
$script:NextId = 1
$script:Pending = $null      # the Task which reads the answer being waited for
$script:PendingId = 0

function Start-Engine {
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = 'python'
    $info.Arguments = '-m grammar_engine --serve'
    $info.WorkingDirectory = $EngineDir                  # the folder which contains the package grammar_engine
    $info.UseShellExecute = $false                       # needed to redirect the streams
    $info.RedirectStandardInput = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.CreateNoWindow = $true
    $script:Engine = [System.Diagnostics.Process]::Start($info)
    # The protocol is UTF-8 on both pipes. We write and read the raw streams so that the code page of the console does not matter.
    $script:Reader = New-Object System.IO.StreamReader($script:Engine.StandardOutput.BaseStream, $Utf8)
}

function Send-Request([hashtable]$Request) {
    # ConvertTo-Json -Compress writes ONE line; the line breaks of the text are escaped as \n in it.
    $Request['id'] = $script:NextId
    $script:PendingId = $script:NextId
    $script:NextId++
    $line = ($Request | ConvertTo-Json -Compress) + "`n"
    $bytes = $Utf8.GetBytes($line)
    $script:Engine.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
    $script:Engine.StandardInput.BaseStream.Flush()
    $script:Pending = $script:Reader.ReadLineAsync()     # returns at once; the answer is read in the background
}

function Stop-Engine {
    if ($script:Engine -and -not $script:Engine.HasExited) {
        $script:Engine.StandardInput.Close()             # the end of the input ends the loop of the engine
        if (-not $script:Engine.WaitForExit(3000)) { $script:Engine.Kill() }
    }
    $script:Engine = $null
    $script:Pending = $null
}

# Converts a position counted in code points to a position in the UTF-16 string.
function ConvertTo-Utf16Index([string]$Text, [int]$CodePoints) {
    $index = 0
    for ($n = 0; $n -lt $CodePoints -and $index -lt $Text.Length; $n++) {
        if ([char]::IsHighSurrogate($Text[$index]) -and $index + 1 -lt $Text.Length) { $index += 2 } else { $index++ }
    }
    return $index
}

# ---- The window ---------------------------------------------------------------------------------------------------

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Grammar window (PowerShell)'
$form.Size = New-Object System.Drawing.Size(1000, 660)

$editor = New-Object System.Windows.Forms.RichTextBox
$editor.Font = New-Object System.Drawing.Font('Segoe UI', 11)
$editor.HideSelection = $false
$editor.Dock = 'Fill'

$list = New-Object System.Windows.Forms.ListView
$list.View = 'Details'; $list.FullRowSelect = $true; $list.HideSelection = $false; $list.MultiSelect = $false; $list.Dock = 'Fill'
foreach ($c in @(@('Line', 50), @('Text', 160), @('Suggestion', 160), @('Message', 480), @('Rule', 130))) { [void]$list.Columns.Add($c[0], $c[1]) }

$split = New-Object System.Windows.Forms.SplitContainer
$split.Dock = 'Fill'; $split.Orientation = 'Horizontal'; $split.SplitterDistance = 300
$split.Panel1.Controls.Add($editor)
$split.Panel2.Controls.Add($list)

$bar = New-Object System.Windows.Forms.FlowLayoutPanel
$bar.Dock = 'Top'; $bar.AutoSize = $true; $bar.Padding = New-Object System.Windows.Forms.Padding(4)
$open = New-Object System.Windows.Forms.Button; $open.Text = 'Open...'; $open.AutoSize = $true
$language = New-Object System.Windows.Forms.ComboBox; $language.DropDownStyle = 'DropDownList'; $language.Width = 70
[void]$language.Items.AddRange(@('fr', 'en', 'es', 'es-AR')); $language.SelectedIndex = 0
$ui = New-Object System.Windows.Forms.ComboBox; $ui.DropDownStyle = 'DropDownList'; $ui.Width = 60
[void]$ui.Items.AddRange(@('en', 'fr', 'es')); $ui.SelectedIndex = 0
$check = New-Object System.Windows.Forms.Button; $check.Text = 'Check'; $check.AutoSize = $true
$status = New-Object System.Windows.Forms.Label; $status.AutoSize = $true; $status.Padding = New-Object System.Windows.Forms.Padding(8, 6, 0, 0)
$status.Text = 'Open a file or paste a text, then press Check.'
$bar.Controls.AddRange(@($open, $language, $ui, $check, $status))

$form.Controls.Add($split)
$form.Controls.Add($bar)                                 # added last, it docks above the split container

$script:Problems = @()

function Load-File([string]$File) {
    try {
        $editor.Text = ([System.IO.File]::ReadAllText($File, $Utf8)).TrimEnd("`r", "`n").Replace("`r`n", "`n")
        $stem = [System.IO.Path]::GetFileNameWithoutExtension($File)      # fr.txt, en.txt, es.txt: the name tells the language
        if ($language.Items.Contains($stem)) { $language.SelectedItem = $stem }
    } catch {
        [void][System.Windows.Forms.MessageBox]::Show("Cannot read ${File}:`n$($_.Exception.Message)")
    }
}

function Start-Check {
    if ($script:Pending) { return }                      # a request is already running
    try {
        if (-not $script:Engine -or $script:Engine.HasExited) { Start-Engine }
        $check.Enabled = $false
        $status.Text = 'Checking...'
        Send-Request @{ lang = [string]$language.SelectedItem; ui = [string]$ui.SelectedItem; text = $editor.Text }
    } catch {
        $status.Text = 'Error: ' + $_.Exception.Message  # for instance Python is not installed
        $check.Enabled = $true
    }
}

# Every 100 ms: has the answer arrived? The interface thread never blocks.
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 100
$timer.Add_Tick({
    if (-not $script:Pending -or -not $script:Pending.IsCompleted) { return }
    $line = $script:Pending.Result
    $script:Pending = $null
    $check.Enabled = $true
    if ($null -eq $line) {                               # end of the stream: the process died
        $reason = if ($script:Engine.HasExited) { $script:Engine.StandardError.ReadToEnd().Trim() } else { '' }
        $status.Text = "The engine stopped. $reason"
        $script:Engine = $null
        return
    }
    try {
        $answer = $line | ConvertFrom-Json               # throws if the line is not JSON
        if ($answer.PSObject.Properties.Name -contains 'error') { $status.Text = 'Error: ' + $answer.error; return }
        $script:Problems = @($answer.issues)
        $list.Items.Clear()
        foreach ($p in $script:Problems) {
            $suggestion = if ($p.suggestions.Count -gt 0) { [string]$p.suggestions[0] } else { '(delete)' }   # empty = delete the text
            $item = New-Object System.Windows.Forms.ListViewItem(([string]($p.paragraph + 1)))
            [void]$item.SubItems.Add([string]$p.text); [void]$item.SubItems.Add($suggestion)
            [void]$item.SubItems.Add([string]$p.message); [void]$item.SubItems.Add([string]$p.rule)
            [void]$list.Items.Add($item)
        }
        $status.Text = if ($script:Problems.Count -gt 0) { "$($script:Problems.Count) problem(s)." } else { 'No problem found.' }
    } catch {
        $status.Text = 'Invalid answer: ' + $_.Exception.Message
    }
})

$list.Add_SelectedIndexChanged({
    if ($list.SelectedIndices.Count -eq 0) { return }
    $p = $script:Problems[$list.SelectedIndices[0]]
    $text = $editor.Text
    $start = ConvertTo-Utf16Index $text ([int]$p.start)  # start and end are code points in the whole text (a "text" request)
    $end = ConvertTo-Utf16Index $text ([int]$p.end)
    $editor.Select($start, $end - $start)
    $editor.ScrollToCaret()
})

$open.Add_Click({
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.InitialDirectory = $Samples; $dialog.Filter = 'Text|*.txt;*.md|All files|*.*'
    if ($dialog.ShowDialog() -eq 'OK') { Load-File $dialog.FileName; Start-Check }
})
$check.Add_Click({ Start-Check })
$form.Add_Shown({
    Load-File $(if ($Path) { $Path } else { Join-Path $Samples 'fr.txt' })
    $timer.Start()
    Start-Check
})
$form.Add_FormClosed({ $timer.Stop(); Stop-Engine })     # stop the child process with the window

[void]$form.ShowDialog()
