from cryptography.fernet import Fernet
import os

print("Зашиф")
# Получаем ключ из переменной окружения или генерируем новый
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", Fernet.generate_key())
fernet = Fernet(ENCRYPTION_KEY)

# Шифрование
message = b"Hello, secret world!"
encrypted = fernet.encrypt(message)
print("Зашифровано:", encrypted)

# Дешифрование
decrypted = fernet.decrypt(encrypted)
print("Расшифровано:", decrypted.decode())

print(Fernet.generate_key())
