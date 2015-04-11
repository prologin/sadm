-- load config
local conf = require "config"

-- libs
local hlp = require "helpers"
local http = require "http"
local json = require "cjson"
local string = require "resty.string"

module('presence', package.seeall)

local this = {}

function this.whois(ipaddr)
    ngx.log(ngx.DEBUG, "SSO: querying presence for IP " .. ipaddr)

    -- build data {"ip": "10.1.2.3"}
    local data = json.encode { ip = ipaddr }
    local timestamp = tostring(ngx.time())
    -- build hmac token
    local digest = hlp.hmac256(conf.presencesync_shared_secret, data .. timestamp)

    if not digest then
        return { ok = false, error = "failed to compute hmac" }
    end

    local signature = timestamp .. ":" .. string.to_hex(digest)

    -- query presencesync
    local httpc = http.new()
    local url = conf.presencesync_url .. "?" .. ngx.encode_args({ data = data, hmac = signature })
    local res, err = httpc:request_uri(url, { method = "GET" })
    if not res then
        return { ok = false, error = "failed to join remote: " .. err }
    end

    -- extract {"username": null} or {"username": "foo"}
    data = json.decode(res.body)
    if not data then
        return { ok = false, error = "malformed response: " .. res.body }
    end
    if data.username == json.null then
        data.username = nil
    end
    ngx.log(ngx.DEBUG, "SSO: " .. ipaddr .. " is " .. tostring(data.username))
    return { ok = true, username = data.username }
end

return this
