module('config')

return {
    -- presencesync conf
    presencesync_url = "http://127.0.0.1:9191/whois",
    presencesync_shared_secret = "secret",

    -- Things to exclude from authentication:
    -- no auth will be done; no cookie/header will be added
    -- Do not put a scheme (http/https), comparison is scheme-agnostic.
    -- Port number can be used, default is 80
    url_whitelist = { "^private/status$" },
    regex_whitelist = { "^public/" },

    -- Page to redirect to if authentication with presencesync failed
    -- Set to falsy (eg. nil) to display a 403 page instead of redirecting
    login_failure_redirect_url = nil,

    -- SSO cookie name, stores the username along with a signature
    sso_cookie_name = "prologin-sso",
    sso_cookie_expiration = 60 * 60 * 24, -- one day
    sso_cookie_secret = "verysecret",
}
