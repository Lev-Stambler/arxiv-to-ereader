# VHS tape file for arxiv-to-ereader demo
# Run with: vhs demo.tape
# Outputs: demo.gif

Output demo.gif

# Terminal settings
Set Shell "bash"
Set FontSize 14
Set Width 900
Set Height 500
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 50ms

# Title card pause
Sleep 500ms

# Show the help
Type "# Convert arXiv papers to PDF for your e-reader"
Enter
Sleep 1s

Type "uv run arxiv-ereader --help"
Enter
Sleep 3s

# Clear and show single paper conversion
Type "clear"
Enter
Sleep 500ms

Type "# Convert a single paper to PDF"
Enter
Sleep 500ms

Type "uv run arxiv-ereader 2402.08954 --no-images"
Enter
Sleep 5s

# Show the created file
Type "ls -la *.pdf"
Enter
Sleep 2s

# Clear and show screen preset options
Type "clear"
Enter
Sleep 500ms

Type "# Convert for Kindle Scribe (larger screen)"
Enter
Sleep 500ms

Type "uv run arxiv-ereader 2402.08954 --screen kindle-scribe --no-images"
Enter
Sleep 5s

# Show both files
Type "ls -la *.pdf"
Enter
Sleep 2s

# Final message
Type ""
Enter
Type "# Your paper is ready for your e-reader!"
Enter
Sleep 2s
