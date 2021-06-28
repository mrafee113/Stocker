def filter_local_names(names: list[str]) -> list[str]:
    return list(filter(lambda x: not x.startswith('__') or not x.endswith('__'), names))
