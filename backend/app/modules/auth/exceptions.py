class AuthenticationError(Exception):
    pass

class InvalidSessionError(Exception):
    pass

class DuplicateEmailError(Exception):
    pass

class PasswordPolicyError(Exception):
    pass
