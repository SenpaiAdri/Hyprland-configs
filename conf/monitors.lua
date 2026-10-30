-- Laptop left, external display right, top edges aligned.
hl.monitor({ output = "eDP-1", mode = "1920x1200@60.01", position = "0x0", scale = 1 })
hl.monitor({ output = "HDMI-A-1", mode = "1920x1080@144", position = "1920x0", scale = 1 })
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })
hl.workspace_rule({ workspace = "1", monitor = "eDP-1", default = true, persistent = true })
for i = 2, 8 do
    hl.workspace_rule({ workspace = tostring(i), monitor = "HDMI-A-1", default = i == 2, persistent = true })
end
