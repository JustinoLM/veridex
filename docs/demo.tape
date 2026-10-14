# Records docs/images/demo.gif. Run from the repository root with:
#   vhs docs/demo.tape
# Requires VHS (https://github.com/charmbracelet/vhs) and `uv` on the PATH.

Output docs/images/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1100
Set Height 800
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms

Type "uv run veridex-play"
Enter
Sleep 3s

# Menu: pick the second puzzle.
Type "2"
Enter
Sleep 3s

# Guess: Ada knave, Bo knave, Cal knight (the correct answer).
Type "knave"
Enter
Sleep 1s
Type "knave"
Enter
Sleep 1s
Type "knight"
Enter
Sleep 4s

# Let the explanation panels sit on screen long enough to read.
Sleep 8s

# Back at the menu: quit.
Type "q"
Enter
Sleep 2s
