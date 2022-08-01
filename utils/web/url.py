import validators

from urllib import parse


class UrlManipulator:
    @classmethod
    def urlify(cls, scheme=str(), netloc=str(), path=str(), params=str(), query=str(), fragment=str()) -> str:
        return parse.unquote(parse.ParseResult(
            scheme=scheme, netloc=netloc, path=path,
            params=params, fragment=fragment, query=query).geturl())  # noqa

    @classmethod
    def querify(cls, url: str, parameters: list[tuple]) -> str:
        if not validators.url(url):
            raise ValueError(f'invalid url={url}')

        if not parameters or any(map(lambda x: len(x) < 2, parameters)):
            return url

        parts = parse.urlparse(url)
        parameters += parse.parse_qsl(parts.query)

        if any(map(lambda x: len(x) > 2, parameters)):
            doseq = True
        else:
            doseq = False

        return cls.urlify(
            query=parse.urlencode(parameters, doseq=doseq),
            scheme=parts.scheme, netloc=parts.hostname, path=parts.path, params=parts.params,
            fragment=parts.params
        )
