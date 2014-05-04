#!/usr/local/rvm/wrappers/redmine/ruby

require 'json'

conf = JSON.parse(STDIN.read)

users = conf['users']
commands = conf['commands']

commands.each do |login, cmd|
	user = users[login]

	case cmd
	when 'created'
		# FIXME: use firstname/lastname instead
		u = User.new(
			:firstname => login,
			:lastname => user['realname'],
			:mail => login + '@finale.prologin'
		)
		u.login = login
		u.password = user['password']
		u.password_confirmation = user['password']
		if u.valid?
			u.save
		else
			$stderr.puts "invalid created user #{login}"
		end

	when 'deleted'
		u = User.find_by_login(login)
		u.destroy

	when 'updated'
		u = User.find_by_login(login)
		u.password = user['password']
		u.password_confirmation = user['password']
		if u.valid? then
			u.save
		else
			$stderr.puts "invalid updated user #{login}"
		end

	end
end

__END__
