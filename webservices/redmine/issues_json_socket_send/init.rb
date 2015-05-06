require 'redmine'
require_dependency 'issues_json_socket_send'

Redmine::Plugin.register :issues_json_socket_send do
  name 'Redmine issues to socket JSON serialized'
  author 'Alexandre `zopieux` Macabies'
  description 'On issue creation, writes the JSON-serialized issue to a socket'
  version '1.0'
  author_url ''
end
