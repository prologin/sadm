working_directory "/var/prologin/redmine"
pid "/tmp/redmine.pid"

preload_app true
timeout 60
worker_processes 4
listen 20120

GC.respond_to?(:copy_on_write_friendly=) and GC.copy_on_write_friendly = true

after_fork do |server, worker|
    if defined?(ActiveRecord::Base)
        env = ENV['RACK_ENV'] || "production"
        config = YAML::load(ERB.new(File.read('config/database.yml')).result)[env]
        ActiveRecord::Base.establish_connection(config)
    end
    addr = "0.0.0.0:#{20120 + worker.nr}"
    server.listen(addr, :tries => -1, :delay => -1, :backlog => 128)
    worker.user('redmine', 'redmine') if Process.euid == 0
end
