# vhs tape: animated README hero for bookreader-tui
#
# Render with:
#   sudo pacman -S vhs ffmpeg ttyd     # if not already installed
#   vhs docs/demo.tape                  # produces docs/screenshots/demo.gif
#
# The tape assumes:
#   - bookreader is on PATH (pipx install bookreader-tui)
#   - /home/prjawal/Documents/book.epub exists
#   - You're in a graphics-capable terminal so the recording shows images
#
# Tweak Output, FontSize, and Set commands to match your README aesthetic.

Output docs/screenshots/demo.gif

Set FontSize 14
Set Width 1400
Set Height 800
Set Padding 20
Set Theme "Tokyo Night"

# 1. Open library home
Type "bookreader"
Enter
Sleep 2s

# 2. Tour the sidebar collections
Tab
Sleep 500ms
Down
Sleep 500ms
Down
Sleep 500ms
Up
Sleep 500ms

# 3. Open a book
Tab
Sleep 500ms
Enter
Sleep 3s

# 4. Scroll a bit
Type "jjjjjjj"
Sleep 1s

# 5. Next chapter (likely contains images)
Type "nnn"
Sleep 2s

# 6. Toggle two-page mode
Type "2"
Sleep 3s

# 7. Toggle theme
Type "T"
Sleep 1s
Type "T"
Sleep 1s

# 8. Bookmark and back to library
Type "m"
Sleep 1s
Type "great quote"
Enter
Sleep 1s
Type "q"
Sleep 2s

# 9. Quit
Type "q"
Sleep 500ms
