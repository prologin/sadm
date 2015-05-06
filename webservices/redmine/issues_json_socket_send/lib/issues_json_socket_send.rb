#!/usr/local/rvm/wrappers/redmine/ruby

require 'json'
require 'socket'

# HOST & PORT must reflect /etc/prologin/irc-redmine-issues.yml hook-listener
HOST = '127.0.0.1'
PORT = 20129
# We really don't want the user to wait
TIMEOUT = 1


# Shamelessly stolen from teh internets
def connect(host, port, timeout = 5)
  # Convert the passed host into structures the non-blocking calls
  # can deal with
  addr = Socket.getaddrinfo(host, nil)
  sockaddr = Socket.pack_sockaddr_in(port, addr[0][3])

  Socket.new(Socket.const_get(addr[0][0]), Socket::SOCK_STREAM, 0).tap do |socket|
    socket.setsockopt(Socket::IPPROTO_TCP, Socket::TCP_NODELAY, 1)

    begin
      # Initiate the socket connection in the background. If it doesn't fail
      # immediatelyit will raise an IO::WaitWritable (Errno::EINPROGRESS)
      # indicating the connection is in progress.
      socket.connect_nonblock(sockaddr)

    rescue IO::WaitWritable
      # IO.select will block until the socket is writable or the timeout
      # is exceeded - whichever comes first.
      if IO.select(nil, [socket], nil, timeout)
        begin
          # Verify there is now a good connection
          socket.connect_nonblock(sockaddr)
        rescue Errno::EISCONN
          return socket
          # Good news everybody, the socket is connected!
        rescue
          # An unexpected exception was raised - the connection is no good.
          socket.close
          raise
        end
      else
        # IO.select returns nil when the socket is not ready before timeout
        # seconds have elapsed
        socket.close
        raise "Connection timeout"
      end
    end
  end
end


class IssuesJsonSocketSend < Redmine::Hook::ViewListener

  def controller_issues_new_after_save(context={})
    issue = context[:issue]
    json = nil
    begin
      json = JSON.dump({
        :attrs => issue.attributes,
        :hattrs => {
          :category => issue.category,
          :tracker => issue.tracker,
          :priority => issue.priority,
          :status => issue.status
        },
        :author => {
          :id => issue.author.id,
          :username => issue.author.login,
          :name => issue.author
        },
        :url => issue_path(issue)
      })
    rescue
      $stderr.puts "issue_to_irc_hook: unable to JSON serialize #{issue.id}"
      return
    end
    begin
      socket = connect(HOST, PORT, TIMEOUT)
      socket.write(json)
      socket.write("\n")
      socket.flush
      socket.close
      $stderr.puts "issue_to_irc_hook: successfully sent issue #{issue.id}"
    rescue
      $stderr.puts "issue_to_irc_hook: unable to connect to bot at #{HOST}:#{PORT} (#{TIMEOUT} sec timeout)"
    end
  end

end
