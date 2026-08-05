import bcrypt

password = input("Password: ").encode("utf-8")

hashed = bcrypt.hashpw(
    password,
    bcrypt.gensalt(),
)

print(hashed.decode("utf-8"))