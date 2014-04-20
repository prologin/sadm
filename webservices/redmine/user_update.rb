#!/usr/bin/env ruby

require 'json'

conf = JSON.parse(STDIN.read)

users = conf['users']
commands = conf['commands']

commands.each do |login, cmd|
	user = users[login]

	puts login, cmd
	puts user

	case cmd
	when 'created'
		u = User.new(
			:firstname => user['firstname'],
			:lastname => user['lastname'],
			:mail => login + '@finale.prologin'
		)
		u.login = login
		u.password = user['password']
		u.password_confirmation = user['password']
		u.save

	when 'deleted'
		u = User.find_by_login(login)
		u.destroy

	when 'updated'
		u = User.find_by_login(login)
		u.password = user['password']
		u.password_confirmation = user['password']
		u.save!

	end
end

__END__
