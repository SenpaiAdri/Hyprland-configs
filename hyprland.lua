-- Hyprland 0.57+: edit the Lua modules in conf/.
local root = debug.getinfo(1, "S").source:sub(2):match("(.*/)")
package.path = root .. "?.lua;" .. package.path
require("colors")
require("conf.monitors")
require("conf.environment")
require("conf.autostart")
require("conf.appearance")
require("conf.animations")
require("conf.layout")
require("conf.input")
require("conf.keybinds")
require("conf.window-rules")
