class ErrorAccessTokenNotProvided(Exception):
    def __str__(self):
        return "Access token not found."


class ErrorPageIdNotProvided(Exception):
    def __str__(self):
        return "Page ID not found."


class ErrorUserIdNotProvided(Exception):
    def __str__(self):
        return "User ID not found."


class ErrorAccessTokenOrUserIdNotFound(Exception):
    def __str__(self):
        return "Access token or User ID not found."


class ErrorThisTypeOfPostIsNotSupported(Exception):
    def __str__(self):
        return "This type of posts is not supported."
