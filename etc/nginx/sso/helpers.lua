local string = require "string"
local hmac = require "hmac"

module('helpers')

local this = {}

function this.string_starts(str, start)
    return start == '' or string.sub(str, 1, string.len(start)) == start
end

function this.string_ends(str, ending)
    return ending == '' or string.sub(str, -string.len(ending)) == ending
end

function this.hmac256(key, data)
    local hmacg = hmac:new(key, hmac.ALGOS.SHA256)
    if not hmacg then
        return nil
    end
    return hmacg:final(data)
end

return this
