# VHS tape file for quick arxiv-to-ereader demo (no network required)
# Run with: vhs demo-quick.tape
# Outputs: demo.gif

Output demo.gif

# Terminal settings
Set Shell "bash"
Set FontSize 16
Set Width 800
Set Height 450
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 40ms

Sleep 500ms

# Show the tool name
Type "# arxiv-to-ereader"
Enter
Sleep 800ms

Type "# Convert arXiv papers to EPUB/Kindle formats"
Enter
Sleep 1s

# Show help
Type "uv run arxiv-to-ereader --help"
Enter
Sleep 4s

# Show example commands
Type ""
Enter
Type "# Example usage:"
Enter
Sleep 500ms

Type "# uv run arxiv-to-ereader 2402.08954"
Enter
Sleep 800ms

Type "# uv run arxiv-to-ereader 2402.08954 --format azw3"
Enter
Sleep 800ms

Type "# uv run arxiv-to-ereader 2402.08954 2401.12345 -o ~/kindle/"
Enter
Sleep 1.5s
