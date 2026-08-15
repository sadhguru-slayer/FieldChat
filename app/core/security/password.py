from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
class PasswordManager:
    @classmethod
    def hash_password(cls,password:str) -> str:
        return password_hash.hash(password)
    @classmethod
    def verify_password(cls,plain_pass:str,hashed_pass:str) -> bool:
        return password_hash.verify(plain_pass,hashed_pass)

password_manager = PasswordManager()