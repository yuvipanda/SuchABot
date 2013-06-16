local keys = redis.call('smembers', KEYS[1])
local count = table.getn(keys)
for index, key in pairs(keys) do
    redis.call('lpush', key, ARGV[1])
end
return count
