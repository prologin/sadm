#!/usr/local/rvm/wrappers/redmine/ruby

require 'json'

conf = JSON.parse(STDIN.read)

users = conf['users']
commands = conf['commands']

commands.each do |login, cmd|
	user = users[login]

	case cmd
	when 'created', 'updated'
		u = User.find_by_login(login)
		if not u then
			u = User.new(
				:firstname => user['firstname'],
				:lastname => user['lastname'],
				:mail => login + '@finale.prologin')
		end
		u.login = login
		u.mail = login + '@finale.prologin'
		u.password = user['password']
		u.password_confirmation = user['password']
		u.firstname = user['firstname']
		u.lastname = user['lastname']
		u.admin = user['group'] == 'root'

		if u.valid?
			u.save
		else
			$stderr.puts "invalid created user: #{login}"
			$stderr.puts "#{u.errors.full_messages}"
		end

		['user', 'orga', 'root'].each do |gname|
			g = Group.where(lastname: gname).first_or_create
			g.save
			g.users.delete(u)
		end

		g = Group.where(lastname: user['group']).first
		g.users << u

	when 'deleted'
		u = User.find_by_login(login)
		if u then
			u.destroy
		end
	end
end

__END__
