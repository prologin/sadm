-- load config
local conf = require "config"

-- libs
local http = require "resty.http.simple"
local ngx = ngx
local string = string
local tostring = tostring

module('presence')

local this = {}

function this.whois(ipaddr)
    ngx.log(ngx.DEBUG, "SSO: querying presence for IP " .. ipaddr)

    -- query presencesync
    local res, err = http.request(conf.presencesync_url[1], conf.presencesync_url[2], {
        path = conf.presencesync_url[3],
        query = { ip = ipaddr }
    })
    if not res then
        return { ok = false, error = "failed to join remote: " .. err }
    end

    res.body = string.gsub(res.body, "\n", "")

    if res.body == "" then
        res.body = nil
    end

    ngx.log(ngx.DEBUG, "SSO: " .. ipaddr .. " is " .. tostring(res.body))
    return { ok = true, username = res.body }
end

return this
