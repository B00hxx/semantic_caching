import redis

r = redis.Redis(host="localhost", port = 6379, db = 0)

print(r.ping())

my_list = ["emb", "answer"]

r.rpush("question?",*my_list)

print(r.lrange("question?", 0, 0))