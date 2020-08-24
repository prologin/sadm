from django.contrib.auth.hashers import BasePasswordHasher


class PlainTextPasswordHasher(BasePasswordHasher):
    algorithm = "plain"

    def salt(self):
        return ''

    def encode(self, password, salt):
        assert salt == ''
        return f'plain$42$prologin${password}'

    def verify(self, password, encoded):
        return f'plain$42$prologin${password}' == encoded

    def safe_summary(self, encoded):
        return {
            'algorithm': self.algorithm,
            'hash': encoded,
        }
