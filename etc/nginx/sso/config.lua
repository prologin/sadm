module('config')

return {
    -- presencesync_cacheserver url as {host, port, path}.
    presencesync_url = { "127.0.0.1", 20131, "/whois" },
    presencesync_shared_secret = "secret",

    -- Things to exclude from authentication.
    -- No auth will be done; no cookie/header will be added
    -- Do not put a scheme (http/https), comparison is scheme-agnostic.
    -- Port number can be used, default is 80
    url_whitelist = { },
    regex_whitelist = { "^mdb/", "^mdbsync/" },

    -- Page to redirect to if authentication with presencesync failed.
    -- Set to falsy (eg. nil) to display a 403 page instead of redirecting.
    login_failure_redirect_url = nil,

    -- Debug SSO header prefix.
    sso_header = "X-SSO",
    -- Prefix to use on errors.
    sso_error = "Single Sign-On (SSO) error.",

    -- SSO cookie name, stores the username along with a signature.
    sso_cookie_name = "prologin-sso",
    sso_cookie_expiration = 60 * 60 * 24, -- one day
    sso_cookie_secret = "verysecret",
}
