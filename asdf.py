from Crypto.Cipher import AES
import binascii

def decrypt_aes(encrypted_data, key_string):
    key = binascii.unhexlify(key_string)
    ciphertext = binascii.unhexlify(encrypted_data)

    iv = ciphertext[:AES.block_size]
    ciphertext = ciphertext[AES.block_size:]

    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(ciphertext)

    padding = decrypted[-1]
    if padding < 1 or padding > AES.block_size:
        raise ValueError("Incorrect padding")

    decrypted = decrypted[:-padding]
    return decrypted.decode('utf-8')

def main():
    encrypted_data = "6f7e9007dd0882f3f320a08690a230b84fcfa66b483dc4f4352123276622af4cc5c656bf0171c36271700f8f4f0f41d14d7c20baec601c70f670acc8b6037a"
    key_string = "6eba99bf3fac4c92a857b05cff433a39"

    try:
        decrypted_message = decrypt_aes(encrypted_data, key_string)
        print("Decrypted message:", decrypted_message)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
