' Chạy trợ lý nền (tray icon) HOÀN TOÀN ẩn — không nháy cửa sổ terminal.
' Double-click file này để bật. Tắt bằng menu chuột phải ở icon khay -> Thoát.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = base
' 0 = cửa sổ ẩn; pythonw cũng không có console -> không nháy gì cả.
sh.Run "pythonw -m tools.ui.tray_assistant", 0, False
