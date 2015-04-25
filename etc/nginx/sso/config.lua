module('config')

return {
    -- presencesync_cacheserver url as {host, port, path}
    presencesync_url = { "127.0.0.1", 20131, "/whois" },
    presencesync_shared_secret = "secret",

    -- debug SSO header prefix
    sso_header = "X-SSO",

    -- SSO cookie name, stores the username along with a signature
    sso_cookie_name = "prologin-sso",
    sso_cookie_expiration = 60 * 60 * 24, -- one day
    sso_cookie_secret = "verysecret",
}
