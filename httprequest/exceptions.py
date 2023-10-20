class NotHttp11RequestMessageError(Exception):
    pass


class NotHttp11ResponseMessageError(Exception):
    pass


class NotURIError(Exception):
    pass


class NotRequestLineError(Exception):
    pass


class NotHttpMethodError(Exception):
    pass


class NotHttpVersionError(Exception):
    pass


class HeaderNotSetError(Exception):
    pass


class NotPortNumberError(Exception):
    pass


class NotHttpSchemeError(Exception):
    pass
