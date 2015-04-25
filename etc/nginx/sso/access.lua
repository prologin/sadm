-- load config
local conf = require "config"
local content_type = "text/plain; charset=utf-8"

-- libs
local ck = require "resty.cookie"
local hlp = require "helpers"
local json = require "cjson"
local presence = require "presence"

-- load cookie reader
local cookie, err = ck:new()
if not cookie then
    ngx.log(ngx.ERR, "SSO: cookie error: " .. err)
    ngx.header["Content-type"] = content_type
    -- continue without SSO
    ngx.header[conf.sso_header] = "failed; cookie error"
    return
end

-- check for sso cookie
function username_from_cookie()
    local field, err = cookie:get(conf.sso_cookie_name)
    if not field then
        -- no cookie (yet)
        return nil
    end
    -- has cookie, validate
    local dotind = string.find(field, ".", 1, true)
    if not dotind then
        ngx.log(ngx.WARN, "SSO: suspicious: no separator in cookie")
        return nil
    end
    local userdata = ngx.decode_base64(string.sub(field, 1, dotind - 1))
    if not userdata then
        ngx.log(ngx.WARN, "SSO: suspicious: malformed b64 userdata")
        return nil
    end
    local signature = ngx.decode_base64(string.sub(field, dotind + 1))
    if not signature then
        ngx.log(ngx.WARN, "SSO: suspicious: malformed b64 cookie signature")
        return nil
    end
    local digest = hlp.hmac256(conf.sso_cookie_secret, userdata)
    if not digest then
        ngx.log(ngx.WARN, "SSO: internal error: could not compute hmac for cookie signature")
        return nil
    end
    local same = digest == signature
    if not same then
        ngx.log(ngx.WARN, "SSO: suspicious: invalid cookie signature")
        return nil
    end
    local username = json.decode(userdata)
    if not username or not type(username) == "string" then
        ngx.log(ngx.WARN, "SSO: internal error: invalid JSON cookie userdata whith right signature (!)")
        return nil
    end
    ngx.log(ngx.DEBUG, "SSO: trusting cookie: " .. ngx.var.remote_addr .. " -> " .. username)
    return username
end

local ssoheader = ""
-- actually try to read the sso cookie
local username = username_from_cookie()

if username then
    -- found
    ssoheader = "; cached"
else
    -- not found/malformed/expired
    -- let's ask presencesync who is remote_addr

    local whoisres = presence.whois(ngx.var.remote_addr)

    if not whoisres.ok then
        ngx.log(ngx.ERR, "SSO: could not query presenced: " .. whoisres.error)
        -- continue without SSO
        ngx.header[conf.sso_header] = "failed; whois error"
        return
    end

    if not whoisres.username then
        -- presence query went fine, but authentication failed
        ngx.log(ngx.WARN, "SSO: presenced returned null username")
        -- continue without SSO
        ngx.header[conf.sso_header] = "unauthorized"
        return
    end
    username = whoisres.username

    -- authentication successful, set cookie
    -- cache the username in an encrypted cookie for subsequent queries
    local jsoned = json.encode(username)
    local signature = ngx.encode_base64(hlp.hmac256(conf.sso_cookie_secret, jsoned))
    cookie:set({
        key = conf.sso_cookie_name,
        value = ngx.encode_base64(jsoned) .. "." .. signature,
        domain = ngx.var.host,
        path = "/",
        secure = true,
        httponly = true,
        expires = ngx.cookie_time(ngx.time() + conf.sso_cookie_expiration)
    })
end

-- authentication successful, set remote user var
ngx.var.sso_remote_user = username

-- add debug headers
ngx.header[conf.sso_header] = "authed" .. ssoheader
ngx.header[conf.sso_header .. "-Username"] = username

-- forward to actual page
return
