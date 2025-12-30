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
Type "# Convert arXiv papers to EPUB for your Kindle"
Enter
Sleep 1s

Type "uv run arxiv-to-ereader --help"
Enter
Sleep 3s

# Clear and show single paper conversion
Type "clear"
Enter
Sleep 500ms

Type "# Convert a single paper to EPUB"
Enter
Sleep 500ms

Type "uv run arxiv-to-ereader 2402.08954 --no-images"
Enter
Sleep 5s

# Show the created file
Type "ls -la *.epub"
Enter
Sleep 2s

# Clear and show format options
Type "clear"
Enter
Sleep 500ms

Type "# Convert to Kindle-native AZW3 format"
Enter
Sleep 500ms

Type "uv run arxiv-to-ereader 2402.08954 --format azw3 --no-images"
Enter
Sleep 5s

# Show both files
Type "ls -la *.epub *.azw3 2>/dev/null || ls -la *.epub"
Enter
Sleep 2s

# Final message
Type ""
Enter
Type "# Your paper is ready for your e-reader!"
Enter
Sleep 2s
