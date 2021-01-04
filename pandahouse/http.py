import requests
from uuid import uuid4

from requests.exceptions import RequestException
from toolz import valfilter, merge

from .utils import escape


_default = dict(
    host="http://localhost:8123",
    database="default",
    user=None,
    password=None,
    verify_tls=True,
)


class ClickhouseException(Exception):
    pass


def prepare(
    query, connection=None, external=None, query_id_prefix=None, quota_key=None
):
    connection = merge(_default, connection or {})
    database = escape(connection["database"])
    query = query.format(db=database)
    params = {
        "database": connection["database"],
        "query": query,
        "user": connection["user"],
        "password": connection["password"],
    }

    if query_id_prefix:
        params["query_id"] = f"{query_id_prefix}|{uuid4()}"

    if quota_key:
        params["quota_key"] = quota_key

    params = valfilter(lambda x: x, params)

    files = {}
    external = external or {}
    for name, (structure, serialized) in external.items():
        params["{}_format".format(name)] = "CSV"
        params["{}_structure".format(name)] = structure
        files[name] = serialized

    host = connection["host"]

    return host, params, files, connection["verify_tls"]


def execute(
    query,
    connection=None,
    data=None,
    external=None,
    stream=False,
    query_id_prefix=None,
    quota_key=None,
):
    host, params, files, verify_tls = prepare(
        query,
        connection,
        external=external,
        query_id_prefix=query_id_prefix,
        quota_key=quota_key,
    )

    # default limits of HTTP url length, for details see:
    # https://clickhouse.yandex/docs/en/single/index.html#http-interface
    if len(params["query"]) >= 15000 and data is None:
        data = params.pop("query", None)

    # basic auth
    kwargs = dict(params=params, data=data, stream=stream, files=files)
    if "user" in params and "password" in params:
        kwargs["auth"] = (params["user"], params["password"])
        del params["user"]
        del params["password"]

    response = requests.post(host, verify=verify_tls, **kwargs)

    try:
        response.raise_for_status()
    except RequestException as e:
        if response.content:
            raise ClickhouseException(response.content)
        else:
            raise e

    if stream:
        return response.raw
    else:
        return response.content
