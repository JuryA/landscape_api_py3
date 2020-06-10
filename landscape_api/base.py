"""Base module for Landscape API (Python 3)."""
# Copyright 2005-2013 Canonical Limited.  All rights reserved.
# Rewrited to support Python 3.8 by Jiří Altman <jiri.altman@konicaminolta.cz> (c) 2020

__all__ = ["run_query", "API", "errors"]

import argparse
import copy
import ctypes
import ctypes.util
import hmac
import inspect
import json
import os
import re
import sys
import textwrap
import time
import types
from base64 import b64encode
from collections import namedtuple
from datetime import date, datetime
from functools import partial
from hashlib import sha256
from io import BytesIO, StringIO
from pprint import pprint
from urllib.parse import quote, urlparse, urlunparse

import requests

from . import __version__

LATEST_VERSION = "2011-08-01"
FUTURE_VERSION = "2013-11-04"


# The list of API actions that require a raw output (they will use vanilla
# "print" instead of pprint). This is useful for actions that return files, so
# that you can pipe the output to a file.
RAW_ACTIONS_LIST = ("get-script-code",)


def curl_strerr(errno):
    """Look up cURL error message by their errno."""

    libcurl_so_name = ctypes.util.find_library("curl-gnutls")
    curl_strerr = ctypes.CDLL(libcurl_so_name).curl_easy_strerror
    curl_strerr.restype = ctypes.c_char_p
    return curl_strerr(errno)


class _ErrorsContainer(object):
    """
    A container for Exception subclasses which is used as a fake module object.
    """

    def add_error(self, error_name, error):
        """
        Add an exception to this errors container.
        """

        error.__module__ = __name__ + ".errors"
        setattr(self, error_name, error)

    def lookup_error(self, error_name):
        """
        Find an exception by name. If it's not found, C{None} will be returned.
        """

        return getattr(self, error_name, None)


class HTTPError(Exception):
    """Exception raised when a non-200 status is received.

    @ivar code: The HTTP status code.
    @ivar message: The HTTP response body.
    @ivar message_data: A data structure extracted by parsing the response body
        as JSON, if possible. Otherwise None. Can be overridden by passing the
        C{message_data} parameter.
    @ivar error_code: The value of the "error" key from the message data.
    @ivar error_message: The value of the "message" key from the message data.
    """

    def __init__(self, code, message=None, message_data=None):
        self.code = code
        self.message = message
        self.message_data = None
        self.error_code = None
        self.error_message = None
        if message is not None and message.startswith("{"):
            self.message_data = json.loads(message)
        if message_data:
            self.message_data = message_data
        if self.message_data:
            self.error_code = self.message_data["error"]
            self.error_message = self.message_data["message"]

    def __str__(self):
        s = "<%s code=%s" % (type(self).__name__, self.code)
        if self.error_code is not None:
            s += " error_code=%s error_message=%s" % (
                self.error_code,
                self.error_message,
            )
        else:
            s += " message=%s" % (self.message)
        return s + ">"


class APIError(HTTPError):
    """Exception for a known API error"""


_Action = namedtuple(
    "action", ("name", "method_name", "doc", "required_args", "optional_args")
)


def fetch(url, post_body, headers, connect_timeout=30, total_timeout=600, cainfo=True):
    """
    Wrapper around C{requests.session}, setting up the proper options and timeout.

    @return: The body of the response.
    """

    session = requests.session()

    if headers:
        session.headers.update(headers)

    response = session.post(
        url,
        params=post_body,
        allow_redirects=True,
        timeout=(connect_timeout, total_timeout),
        verify=cainfo,
    )

    if not response.ok:
        raise HTTPError(response.status_code, response.text)

    return response.text


def parse(url):
    """
    Split the given URL into the host, port, and path.

    @type url: C{str}
    @param url: An URL to parse.
    """

    lowurl = url.lower()
    if not lowurl.startswith(("http://", "https://")):
        raise SyntaxError("URL must start with 'http://' or 'https://': %s" % (url,))
    url = url.strip()
    parsed = urlparse(url)
    path = urlunparse(("", "") + parsed[2:])
    host = parsed[1]

    if ":" in host:
        host, port = host.split(":")
        try:
            port = int(port)
        except ValueError:
            port = None
    else:
        port = None

    return str(host), port, str(path)


def run_query(
    access_key,
    secret_key,
    action,
    params,
    uri,
    ssl_ca_file=True,
    version=LATEST_VERSION,
):
    """Make a low-level query against the Landscape API.

    @param access_key: The user access key.
    @param secret_key: The user secret key.
    @param action: The type of methods to call. For example, "GetComputers".
    @param params: A dictionary of the parameters to pass to the action.
    @param uri: The root URI of the API service. For example,
        "https://landscape.canonical.com/".
    @param ssl_ca_file: Path to the server's SSL Certificate Authority
        certificate. For example, "~/landscape_server_ca.crt".
    """

    for key, value in list(params.items()):
        if isinstance(key, str):
            params.pop(key)
            key = str(key)
        if isinstance(value, str):
            value = str(value)
        params[key] = value

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    params.update(
        {
            "access_key_id": access_key,
            "action": action,
            "signature_version": "2",
            "signature_method": "HmacSHA256",
            "timestamp": timestamp,
            "version": version,
        }
    )
    method = "POST"
    host, port, path = parse(uri)
    signed_host = "%s:%d" % (host, port) if port is not None else host
    if not path:
        path = "/"
        uri = "%s/" % uri
    signed_params = "&".join(
        "%s=%s" % (quote(key, safe="~"), quote(value, safe="~"))
        for key, value in sorted(params.items())
    )
    to_sign = "%s\n%s\n%s\n%s" % (method, signed_host, path, signed_params)
    digest = hmac.new(
        secret_key.encode("ascii"), to_sign.encode("ascii"), sha256
    ).digest()
    signature = b64encode(digest)
    signed_params += "&signature=%s" % quote(signature)
    try:
        return fetch(uri, signed_params, {"Host": signed_host}, cainfo=ssl_ca_file)
    except HTTPError as e:
        if e.error_code is not None:
            error_class = errors.lookup_error(_get_error_code_name(e.error_code))
            if error_class:
                raise error_class(e.code, e.message)
        raise e


def _get_error_code_name(error_code):
    """
    Get the Python exception name given an error code. If the error code
    doesn't end in "Error", the word "Error" will be appended.
    """

    if error_code.endswith("Error"):
        return error_code
    else:
        return error_code + "Error"


def _lowercase_api_name(name):
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def load_schema():
    """
    Load the schema from the C{schemas.json} file.

    Invoking this method will populate the module-level C{errors} object with
    exception classes based on the schema.
    """

    this_directory = os.path.dirname(os.path.abspath(__file__))
    schema_filename = os.path.join(this_directory, "schemas.json")
    with open(schema_filename) as _file:
        return json.loads(_file.read())


def _build_exception(name):
    # TODO: Put __doc__ on the generated errors (must be included in the
    # schema)
    class _APIError(APIError):
        pass

    _APIError.__name__ = name
    return _APIError


def _build_exceptions(schema):
    """
    Given a schema, construct a L{_ErrorsContainer} and populate it with error
    classes based on all the error codes specified in the schema.
    """

    errors = _ErrorsContainer()
    for action, version_handlers in list(schema.items()):
        for version, handler in list(version_handlers.items()):
            for error in handler["errors"]:
                exception_name = _get_error_code_name(error["code"])
                exception_type = _build_exception(exception_name)
                if not errors.lookup_error(exception_name):
                    errors.add_error(exception_name, exception_type)
    return errors


_schema = load_schema()
errors = _build_exceptions(_schema)
# A hack to make "from landscape_api.base.errors import UnknownComputer" to
# work:
sys.modules[__name__ + ".errors"] = errors


class MultiError(APIError):
    """
    An exception that represents multiple sub-exceptions.

    @ivar errors: A list of instances of L{APIError} or its subclasses.
    """

    def __init__(self, http_code, message):
        # Subclass from APIError just for convenience in catching; we're not
        # using its functionality
        APIError.__init__(self, http_code, message)
        self.errors = []
        for sub_error in self.message_data["errors"]:
            if sub_error.get("error") is not None:
                error_class = errors.lookup_error(
                    _get_error_code_name(sub_error["error"])
                )
                if error_class:
                    exception = error_class(self.code, message_data=sub_error)
                else:
                    exception = APIError(self.code, message_data=sub_error)
            else:
                exception = APIError(self.code, message_data=sub_error)
            self.errors.append(exception)

    def __str__(self):
        return "<%s errors=%s>" % (type(self).__name__, self.errors)


class UnauthorisedError(APIError):
    pass


class SignatureDoesNotMatchError(APIError):
    pass


class AuthFailureError(APIError):
    pass


class InvalidCredentialsError(APIError):
    pass


errors.add_error("MultiError", MultiError)
errors.add_error("Unauthorised", UnauthorisedError)
errors.add_error("SignatureDoesNotMatchError", SignatureDoesNotMatchError)
errors.add_error("AuthFailureError", AuthFailureError)
errors.add_error("InvalidCredentialsError", InvalidCredentialsError)


class _API(object):
    """Provide an object-oriented interface to the Landscape API.

    @param uri: The URI endpoint of the API.
    @param access_key: The 20 characters access key.
    @param secret_key: The 40 characters secret key.
    @param ssl_ca_file: Path to an alterneative CA certificate file.
    @param json: Return plain JSON response instead of a python object.
    @param schema: The schema data to use. If none is specified, it will be
        read from 'schemas.json' in the same directory as this module.

    Usage::

        api = API("https://landscape.canonical.com/api", "access_key",
                  "secret_key")
        computers = api.get_computers()
    """

    # TODO: accept an api_version parameter, use it instead of LATEST_VERSION

    _run_query = staticmethod(run_query)

    #     'overridden_apis' contains information about command-line API actions
    # that we want to override to (locally) take different arguments and invoke
    # a hand-coded method. This is used for situations where we want to provide
    # some extra layer of convenience to the user of this module or the command
    # line, like accepting a filename containing large data instead of
    # requiring it to be passed as a string.
    #     Any documentation that isn't specified in overridden_apis will be
    # looked up in the original schema.
    #     Right now it only supports replacing arguments one-for-one, but it
    # could be extended if we need to.
    overridden_apis = {}

    def __init__(
        self, uri, access_key, secret_key, ssl_ca_file=None, json=False, schema=None
    ):
        self._uri = uri
        self._access_key = access_key
        self._secret_key = secret_key
        self._ssl_ca_file = ssl_ca_file
        self._json = json
        self._schema = schema if schema is not None else _schema

    def run_query(self, action_name, arguments):
        """
        Make a low-level query against the Landscape API, using details
        provided in the L{API} constructor.
        """

        result = self._run_query(
            self._access_key,
            self._secret_key,
            action_name,
            arguments,
            self._uri,
            self._ssl_ca_file,
        )
        if not self._json:
            result = json.loads(result)
        return result

    def call(self, method, **kwargs):
        """
        Invoke an API method, automatically encoding the arguments as defined
        in the schema.
        """

        action = self._schema[method][self.version]
        parameters = action["parameters"]
        fields = [(x["name"], x) for x in parameters]
        arguments = self._encode_struct_fields(fields, kwargs)
        return self.run_query(method, arguments)

    def _encode_struct_fields(self, fields, arguments, prefix=""):
        """
        Encode multiple named fields. This is used for both base argument
        processing and struct fields.

        @param fields: An associative list of field names to field parameter
            descriptions.
        @param arguments: A mapping of field names to actual values to encode.
        @param prefix: The prefix to put on all named parameters encoded.
        """

        result = {}
        for parameter_name, parameter_description in fields:
            # Figure out the type of the parameter and how to encode it.
            if parameter_name not in arguments:
                if not parameter_description.get("optional"):
                    raise TypeError("Missing parameter %s" % (parameter_name,))
            else:
                value = arguments.pop(parameter_name)
                encoded_item = self._encode_argument(
                    parameter_description, prefix + parameter_name, value
                )
                result.update(encoded_item)
        if arguments:
            raise TypeError("Extra arguments: %r" % (arguments,))
        return result

    def _encode_argument(self, parameter, name, value):
        """
        Encode a piece of data based on a parameter description.

        Returns a dictionary of parameters that should be included in the
        request.
        """

        if parameter.get("optional") and value == parameter.get("default"):
            return {}
        kind = parameter["type"].replace(" ", "_")
        handler = getattr(self, "_encode_%s" % (kind,))
        return handler(parameter, name, value)

    def _encode_integer(self, parameter, name, arg):
        return {name: str(arg)}

    def _encode_float(self, parameter, name, arg):
        return {name: str(arg)}

    def _encode_raw_string(self, parameter, name, value):
        return {name: str(value)}

    def _encode_enum(self, parameter, name, value):
        return {name: str(value)}

    def _encode_unicode(self, parameter, name, value):
        """
        Encode a python unicode object OR, for historical reasons, a datetime
        object, into an HTTP argument.
        """

        if isinstance(value, (datetime, date)):
            # This is really dumb compatibility stuff for APIs that aren't
            # properly specifying their type.
            return self._encode_date(parameter, name, value)
        return {name: str(value, "utf-8")}

    # These are Unicode types with specific validation.
    _encode_unicode_line = _encode_unicode
    _encode_unicode_title = _encode_unicode

    def _encode_file(self, parameter, name, value):
        contents = None
        with open(value, "rb") as the_file:
            contents = the_file.read()
        encoded_contents = b64encode(contents).decode()
        # We send the filename along with the contents of the file.close
        filename = os.path.basename(value)
        payload = filename + "$$" + encoded_contents
        return {name: payload.encode("utf-8")}

    def _encode_boolean(self, parameter, name, value):
        return {name: "true" if value else "false"}

    def _encode_date(self, parameter, name, value):
        if isinstance(value, str):
            # allow people to pass strings, since the server has really good
            # date parsing and can handle lots of different formats.
            return {name: value}
        return {name: value.strftime("%Y-%m-%dT%H:%M:%SZ")}

    def _encode_list(self, parameter, name, sequence):
        """
        Encode a python list OR a comma-separated string into individual
        "foo.N" arguments.
        """

        result = {}
        if isinstance(sequence, str):
            sequence = [item.strip() for item in sequence.split(",")]
        for i, item in enumerate(sequence):
            encoded_item = self._encode_argument(
                parameter["item"], "%s.%s" % (name, i + 1), item
            )
            result.update(encoded_item)
        return result

    def _encode_mapping(self, parameter, name, items):
        """Encode a mapping into individual "foo.KEY=VALUE" arguments.

        Mappings andcomma-separated strings of KEY=VALUE pairs are
        supported.
        """

        if isinstance(items, str):
            items = {k.strip(): v.strip() for k, v in _parse_csv_mapping_safely(items)}
        elif hasattr(items, "items"):
            items = list(items.items())

        keyparam = parameter["key"]
        valueparam = parameter["value"]
        result = {}
        for key, value in items:
            key = self._encode_argument(keyparam, "<key>", key)["<key>"]
            subname = "{}.{}".format(name, key)
            result.update(self._encode_argument(valueparam, subname, value))
        return result

    def _encode_data(self, parameter, name, value):
        contents = None
        with open(value, "rb") as the_file:
            contents = the_file.read()
        encoded_contents = b64encode(contents)
        return {name: encoded_contents.encode("utf-8")}

    def _encode_structure(self, parameter, name, dictionary):
        return self._encode_struct_fields(
            iter(list(parameter["fields"].items())),
            dictionary.copy(),
            prefix=name + ".",
        )

    def call_arbitrary(self, method, arguments):
        """
        Invoke an API method in a raw form, without encoding any parameters.

        @returns: The result as returned by the API method. If the C{json}
            parameter to L{API} was passed as C{True}, then the raw result will
            be returned. Otherwise it will be decoded as json and returned as a
            Python object.
        """

        return self.run_query(method, arguments)


def api_factory(schema, version=LATEST_VERSION):
    """
    A creator of L{API} classes. It will read a schema and create the methods
    on an L{API} to be available statically.
    """

    def _get_action_callers():
        """
        Build callable methods for all actions published through the schema
        that will invoke L{API.call}.
        """

        actions = {}
        for action_name in schema:
            action = schema[action_name].get(version)
            if action is None:
                # This API version doesn't support this action
                continue
            python_action_name = _lowercase_api_name(action_name)
            caller = _make_api_caller(action_name, action)
            actions[python_action_name] = caller
        return actions

    def _make_api_caller(action_name, action):
        method_name = _lowercase_api_name(action_name)
        positional_parameters = []
        optional_parameters = []
        defaults = []
        for parameter in action["parameters"]:
            if parameter.get("optional"):
                optional_parameters.append(parameter["name"])
                defaults.append(parameter["default"])
            else:
                positional_parameters.append(parameter["name"])

        positional_parameters.extend(optional_parameters)

        caller = _change_function(
            _caller, method_name, positional_parameters, defaults, action_name,
        )
        caller.__doc__ = _generate_doc(action)
        return caller

    def _generate_doc(action):
        """
        Generate a python docstring vaguely using pydoc syntax.
        """

        doc = inspect.cleandoc(action["doc"]) + "\n"
        for parameter in action["parameters"]:
            pdoc = parameter.get("doc", "Undocumented")
            param_doc = "@param %s: %s" % (parameter["name"], pdoc)
            doc += "\n" + textwrap.fill(param_doc, subsequent_indent="    ")
            doc += "\n@type %s: %s" % (parameter["name"], _describe_type(parameter))
        return doc

    def _describe_type(parameter):
        type_doc = parameter["type"]
        if type_doc == "list":
            type_doc += " (of %s)" % (_describe_type(parameter["item"]),)
        return type_doc

    def _change_function(func, newname, positional_parameters, defaults, action_name):
        """
        Return a new function with the provided name C{newname}, and changing
        the signature corresponding to C{positional_parameters} and
        C{defaults}.
        """

        argcount = len(positional_parameters) + 1
        code = func.__code__
        params = positional_parameters[:]
        params.insert(0, "self")
        varnames = [str(param) for param in params]
        # See _caller for the defined variable _args
        varnames.append("_args")
        varnames = tuple(varnames)
        co_nlocals = len(varnames)
        func_defaults = tuple(defaults) if defaults else None
        newcode = code.replace(
            co_argcount=argcount,
            co_nlocals=co_nlocals,
            co_name=newname,
            co_varnames=varnames,
        )
        # newcode = types.CodeType(
        #     argcount, co_nlocals, code.co_stacksize, code.co_flags,
        #     code.co_code, code.co_consts, code.co_names, varnames,
        #     code.co_filename, newname, code.co_firstlineno, code.co_lnotab,
        #     code.co_freevars, code.co_cellvars)
        # Make locals and action_name available to the method
        func_globals = func.__globals__.copy()
        func_globals["action_name"] = action_name
        return types.FunctionType(
            newcode, func_globals, newname, func_defaults, func.__closure__
        )

    def _caller(self):
        """Wrapper calling C{API.call} with the proper action name."""

        self.action_name = None
        # The locals of this function aren't obvious, because _change_function
        # modifies the parameters, and we have to access them with locals().
        _args = locals().copy()
        _args.pop("self")
        return self.call(action_name, **_args)  # noqa

    api_class = type("API", (_API,), {})
    api_class.version = version
    actions = _get_action_callers()
    for k, v in list(actions.items()):
        if not getattr(api_class, k, None):
            setattr(api_class, k, v)
        else:
            raise RuntimeError(
                "Tried setting '%s' from schema but that "
                "method already exists" % (k,)
            )

    return api_class


class API(api_factory(_schema)):

    overridden_apis = {
        "ImportGPGKey": {
            "method": "import_gpg_key_from_file",
            "doc": None,
            "replace_args": {
                "material": {
                    "name": "filename",
                    "type": "unicode",
                    "doc": "The filename of the GPG file.",
                }
            },
        }
    }

    extra_actions = [
        _Action(
            "ssh",
            "ssh",
            "Try to ssh to a landscape computer",
            [
                {
                    "name": "query",
                    "type": "unicode",
                    "doc": "A query string which should return " "one computer",
                }
            ],
            [
                {
                    "name": "user",
                    "type": "unicode",
                    "default": None,
                    "doc": "If specified, the user to pass to " "the ssh command",
                }
            ],
        )
    ]

    def import_gpg_key_from_file(self, name, filename):
        """
        Import a GPG key with contents from the given filename.
        """

        with open(filename) as _file:
            material = _file.read()

        return self.call("ImportGPGKey", name=name, material=material)

    def ssh(self, query, user=None):
        """
        Calls C{get_computers}, and then the ssh command with the given result.
        """

        data = self.get_computers(query, with_network=True)
        if len(data) != 1:
            raise ValueError("Expected one computer as result, got %d" % len(data))
        computer = data[0]
        if not computer.get("network_devices", []):
            raise ValueError("Couldn't find a network device")
        address = computer["network_devices"][0]["ip_address"]
        args = ["ssh"]
        if user is not None:
            args.extend(["-l", user])
        args.append(address)
        os.execvp("ssh", args)


class APIv2(api_factory(_schema, version=FUTURE_VERSION)):
    """Development version of the API."""

    _run_query = staticmethod(partial(run_query, version=FUTURE_VERSION))


class ParseActionsError(Exception):
    """Raises for errors parsing the API class"""


class UsageError(Exception):
    """Raises when help should be printed."""

    def __init__(self, stdout=None, stderr=None, error_code=None):
        Exception.__init__(self, "", stdout, stderr)
        self.stdout = stdout
        self.stderr = stderr
        self.error_code = error_code


class SchemaParameterAction(argparse.Action):
    """
    An L{argparse.Action} that knows how to parse command-line schema
    parameters and convert them to Python objects.
    """

    def __init__(self, *args, **kwargs):
        self.schema_parameter = kwargs.pop("schema_parameter")
        argparse.Action.__init__(self, *args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        value = self.parse_argument(self.schema_parameter, values)
        setattr(namespace, self.dest, value)

    def parse_argument(self, parameter, value):
        suffix = parameter["type"].replace(" ", "_")
        parser = getattr(self, "parse_%s" % (suffix,))
        try:
            return parser(parameter, value)
        except UsageError:
            raise
        except:  # noqa
            raise UsageError(
                stderr="Couldn't parse value %r as %s\n" % (value, parameter["type"]),
                error_code=1,
            )

    def parse_integer(self, parameter, value):
        return int(value)

    def parse_float(self, parameter, value):
        return float(value)

    def parse_raw_string(self, parameter, value):
        return value

    def parse_enum(self, parameter, value):
        return value

    def parse_unicode(self, parameter, value):
        return value

    # These are Unicode types with specific validation.
    parse_unicode_line = parse_unicode
    parse_unicode_title = parse_unicode

    def parse_file(self, parameter, value):
        return value

    def parse_date(self, parameter, value):
        # the server already has a good date parser, and to parse it well
        # ourselves we'd have to depend on the "dateutil" package...
        return value

    def parse_boolean(self, parameter, value):
        # This is only used for required arguments
        return True if value == "true" else False

    def parse_list(self, parameter, value):
        """Parse a comma-separated list of values converting it to a C{list}.

        Items can contain escaped commas as "\\," and they will be unescaped
        by this method.
        """

        items = _parse_csv_list_safely(value)
        return [
            self.parse_argument(parameter["item"], list_item)
            for list_item in items
            if list_item != ""
        ]

    def parse_mapping(self, parameter, value):
        """Parse a comma-separated list of key/value pairs into a dict.

        Keys and values are separated by "=".
        """

        keyparam = parameter["key"]
        valueparam = parameter["value"]
        result = {}
        for key, value in _parse_csv_mapping_safely(value):
            key = self.parse_argument(keyparam, key)
            value = self.parse_argument(valueparam, value)
            result[key] = value
        return result

    def parse_data(self, parameter, value):
        return value


def _parse_csv_list_safely(value):
    """Yield each substring separated by commas.

    Substrings can contain escaped commas as "\\," and they will be
    unescaped by this function.
    """

    item = ""
    escaped = False
    for c in value:
        if c == ",":
            if escaped:
                item += c
                escaped = False
            else:
                yield item
                item = ""
        elif c == "\\":
            escaped = True
        else:
            if escaped:
                item += "\\"
            item += c
    if escaped:
        item += "\\"
    if item:
        yield item


def _parse_csv_mapping_safely(value):
    """Yield each key/value pair separated by commas.

    Substrings can contain escaped commas as "\\," and they will be
    unescaped by this function.
    """

    for item in _parse_csv_list_safely(value):
        key, sep, value = item.partition("=")
        if not sep:
            raise ValueError("invalid key/value pair {}".format(item))
        yield (key, value)


class CommandLine(object):
    """
    Implementation of the command-line logic.
    """

    # TODO: Accept an --api-version parameter.

    def __init__(self, stdout, stderr, exit, environ):
        self.stdout = stdout
        self.stderr = stderr
        self.exit = exit
        self.environ = environ

    def main(self, argv, schema):  # noqa
        """
        @param argv: The list of command line arguments, usually from
            C{sys.argv}.
        """

        version = self.environ.get("LANDSCAPE_API_VERSION", LATEST_VERSION)
        actions = self.get_actions(schema, version)

        try:
            # Build main parser
            parser = self.get_main_parser()

            # Special case for empty command line
            if len(argv) == 0:
                raise UsageError(
                    stdout=self.format_main_usage(parser, actions), error_code=0
                )

            action_map = dict([(action.name, action) for action in actions])

            (args, argv) = self.wrap_parse_args(parser.parse_known_args, argv)

            print_help_only = False
            if (args.action == "help" and len(argv) == 0) or (
                args.help and not args.action
            ):
                raise UsageError(
                    stdout=self.format_main_usage(parser, actions), error_code=0
                )
            if args.action == "help":
                print_help_only = True
                args.action = argv[0]
            if args.help:
                print_help_only = True

            if args.action != "call" and args.action not in action_map:
                if args.action is None:
                    raise UsageError(stderr="Please specify an action.\n")
                raise UsageError(stderr="Unknown action: %s\n" % args.action)

            if args.action == "call":
                action_parser = self.get_call_parser(parser)
            else:
                action = action_map[args.action]
                action_parser = self.get_action_parser(parser, action)

            if print_help_only:
                raise UsageError(stdout=action_parser.format_help(), error_code=0)

            api = self.get_api(args, schema, version)
            action_args = self.wrap_parse_args(action_parser.parse_args, argv)
            try:
                if args.action != "call":
                    result = self.call_known_action(
                        api, action, action_parser, action_args
                    )
                else:
                    result = self.call_arbitrary_action(api, action_args)
            except HTTPError as e:
                if e.error_code is not None:
                    self.stderr.write("\nGot server error:\nStatus: %s\n" % (e.code,))
                    self._format_api_error(e)
                else:
                    self.stderr.write(
                        "\nGot unexpected server error:\nStatus: %d\n" % e.code
                    )
                    self.stderr.write("Error message: %s\n" % e.message)
                return self.exit(2)

        except UsageError as e:
            if e.stdout is not None:
                self.stdout.write(e.stdout)
            if e.stderr is not None:
                self.stderr.write(e.stderr)
            if e.error_code is not None:
                return self.exit(e.error_code)
            else:
                return self.exit(1)
        except Exception as e:
            self.stderr.write(str(e) + "\n")
            return self.exit(1)

        if args.json_output or action.name in RAW_ACTIONS_LIST:
            # Some of the methods require raw output, for instance the code
            # part of scripts.
            self.stdout.write(str(result) + "\n")
        else:
            pprint(result, stream=self.stdout)

    def _format_api_error(self, error):
        """
        Format and print an HTTP error in a nice way.
        """

        message = error.error_message
        error_code = error.error_code
        if isinstance(message, str):
            message = message.encode("utf-8")
        if isinstance(error_code, str):
            error_code = error_code.encode("utf-8")
        self.stderr.write("Error code: %s\nError message: %s\n" % (error_code, message))

        if isinstance(error, MultiError):
            for error in error.errors:
                self._format_api_error(error)

    def call_known_action(self, api, action, action_parser, args):
        """
        Call a known, supported API action, using methods on L{API}.
        """

        positional_args = []
        keyword_args = {}
        for req_arg in action.required_args:
            # Special case to allow query to be multiple
            # space-separated tokens without having to be quoted on the
            # command line.
            argname = req_arg["name"].replace("_", "-")
            value = (
                " ".join(args.query) if argname == "query" else getattr(args, argname)
            )
            positional_args.append(value)
        for opt_arg in action.optional_args:
            opt_arg_name = opt_arg["name"].replace("_", "-")
            opt_arg_parameter_name = opt_arg["name"]
            arg = getattr(args, opt_arg_name, None)
            if arg is not None and arg != action_parser.get_default(opt_arg_name):
                keyword_args[opt_arg_parameter_name] = arg
        handler = getattr(api, action.method_name)
        return handler(*positional_args, **keyword_args)

    def call_arbitrary_action(self, api, args):
        """
        Call an arbitrary action specified as raw HTTP arguments, using
        L{API.call_arbitrary}.
        """

        action_name = args.action_name
        arguments = {}
        for arg in args.argument:
            key, value = arg.split("=", 1)
            arguments[key] = value
        return api.call_arbitrary(action_name, arguments)

    def get_api(self, args, schema, version):
        """
        Get an L{API} instance with parameters based on command line arguments
        or environment variables.
        """

        if args.key is not None:
            access_key = args.key
        elif "LANDSCAPE_API_KEY" in self.environ:
            access_key = self.environ["LANDSCAPE_API_KEY"]
        else:
            raise UsageError(stderr="Access key not specified.\n")

        if args.secret is not None:
            secret_key = args.secret
        elif "LANDSCAPE_API_SECRET" in self.environ:
            secret_key = self.environ["LANDSCAPE_API_SECRET"]
        else:
            raise UsageError(stderr="Secret key not specified.\n")

        if args.uri is not None:
            uri = args.uri
        elif "LANDSCAPE_API_URI" in self.environ:
            uri = self.environ["LANDSCAPE_API_URI"]
        else:
            raise UsageError(stderr="URI not specified.\n")

        if args.ssl_ca_file is not None:
            ssl_ca_file = args.ssl_ca_file
        else:
            ssl_ca_file = self.environ.get("LANDSCAPE_API_SSL_CA_FILE")

        api_class = APIv2 if version == FUTURE_VERSION else API
        if schema is not _schema:
            api_class = api_factory(schema, version=version)

        return api_class(
            uri, access_key, secret_key, ssl_ca_file, args.json_output, schema=schema
        )

    def get_action_parser(self, parser, action):
        """
        Build an L{argparse.ArgumentParser} for a particular action.
        """

        action_parser = argparse.ArgumentParser(
            add_help=False,
            description=action.doc,
            prog="%s %s" % (parser.prog, action.name),
        )
        for req_arg in action.required_args:
            argname = req_arg["name"].replace("_", "-")
            argdoc = self.get_parameter_doc(req_arg)
            if argname == "query":
                # Special case to allow query to be multiple space-separated
                # tokens without having to be quoted on the command line.
                action_parser.add_argument(argname, help=argdoc, nargs="+")
            else:
                action_parser.add_argument(
                    argname,
                    help=argdoc,
                    action=SchemaParameterAction,
                    schema_parameter=req_arg,
                )
        for opt_arg in action.optional_args:
            argname = opt_arg["name"].replace("_", "-")
            argdoc = self.get_parameter_doc(opt_arg)
            if opt_arg["default"] is False:
                action_parser.add_argument(
                    "--%s" % argname, dest=argname, action="store_true", help=argdoc
                )
            elif opt_arg["default"] is True:
                action_parser.add_argument(
                    "--no-%s" % argname, dest=argname, action="store_false", help=argdoc
                )
            else:
                action_parser.add_argument(
                    "--%s" % argname,
                    dest=argname,
                    help=argdoc,
                    action=SchemaParameterAction,
                    schema_parameter=opt_arg,
                )
        return action_parser

    def get_call_parser(self, parser):
        """
        Build the L{argparse.ArgumentParser} that knows how to handle the
        "call" action.
        """

        call_parser = argparse.ArgumentParser(
            add_help=False,
            description="Call an arbitrary Landscape API action.",
            prog="%s call" % (parser.prog,),
        )
        call_parser.add_argument(
            "action_name", help="The name of the Landscape API action."
        )
        call_parser.add_argument(
            "argument", help="An argument in key=value format", nargs="*"
        )
        return call_parser

    def get_main_parser(self):
        """
        Build the L{argparse.ArgumentParser} for the toplevel command line
        options.
        """

        # Not using argparse subgroups here because the help output gets very
        # messy when you have many subgroups.
        prog = sys.argv[0]
        parser = argparse.ArgumentParser(prog=prog, add_help=False)
        group = parser.add_argument_group("Global Arguments")
        group.add_argument(
            "-h",
            "--help",
            help="show this help message and exit",
            action="store_true",
            default=None,
        )
        group.add_argument(
            "--key",
            help="The Landscape access key to use when making "
            "the API request.  It defaults to the "
            "environment variable LANDSCAPE_API_KEY if "
            "not provided.",
        )
        group.add_argument(
            "--secret",
            help="The Landscape secret key to use when making "
            "the API request.  It defaults to the "
            "environment variable LANDSCAPE_API_SECRET if "
            "not provided.",
        )
        group.add_argument(
            "--uri",
            help="The URI of your Landscape endpoint. It "
            "defaults to the environment variable "
            "LANDSCAPE_API_URI if not provided.",
        )
        group.add_argument(
            "--json",
            dest="json_output",
            action="store_true",
            default=False,
            help="Output directly the JSON structure instead "
            "of the Python representation.",
        )
        group.add_argument(
            "--ssl-ca-file",
            help="SSL CA certificate to validate server.  If "
            "not provided, the SSL certificate provided "
            "by the server will be verified with the "
            "system CAs. It defaults to the environment "
            "variable LANDSCAPE_API_SSL_CA_FILE if not "
            "provided",
        )
        group = parser.add_argument_group("Actions")
        group.add_argument("action", default=None, nargs="?")
        return parser

    def wrap_parse_args(self, parse_args, *args, **kwargs):
        """
        Wraps a call to argparse's parse_args and captures all stdout, stderr,
        and sys.exits() and converts them into a UsageError.

        @param parse_args: The C{parse_args} method of an C{ArgumentParser} to
            execute.
        @param args: Positional args for the C{parse_args} call.
        @param kwargs: Keyword args for the C{parse_args} call.
        """

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        try:
            try:
                return parse_args(*args, **kwargs)
            except SystemExit as e:
                code = e.code
                stdout = sys.stdout.getvalue()
                stderr = sys.stderr.getvalue()
                raise UsageError(stdout, stderr, code)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def format_main_usage(self, parser, actions):
        """
        Format a help display for the command line

        @param parser: The main argparse object for the program.
        @param actions: The actions available.
        @returns: A formatted help string.
        """

        prog = parser.prog
        # Use argparse's help except the last line
        parser_help = parser.format_help()
        parser_help = "\n".join(parser_help.splitlines()[:-1])
        # Build help text
        help_lines = [
            f"Landscape API client (Python 3) - version {__version__}",
            parser_help,
        ]
        # Add action docs
        for action in actions:
            help_lines.append("  %s" % action.name)
        help_lines.append(
            "\nType '%(prog)s help ACTION' for help on a specific action.\n"
            % {"prog": prog}
        )
        return "\n".join(help_lines)

    def get_parameter_doc(self, parameter):
        doc = parameter["doc"]
        suffixes = {
            "list": "(comma-delimited list)",
            "mapping": "(comma-delimited KEY=VALUE pairs)",
            "boolean": "(true or false)",
            "date": "(time in YYYY-MM-DDTHH:MM:SS format)",
            "file": "filename",
        }
        suffix = suffixes.get(parameter["type"])
        if suffix:
            doc += " %s" % (suffix,)
        return doc

    def get_actions(self, schema, version):
        """
        Return a list of data structures representing callable actions provided
        by the API, based on the schema.

        @param schema: The schema, as returned from L{load_schema}.
        @param version: The API version to use.
        """

        overridden_apis = API.overridden_apis
        actions = []
        for name, version_handlers in list(schema.items()):
            if name in overridden_apis:
                # Don't add the base schema if it's been overridden; we don't
                # want duplicate actions.
                continue
            schema_action = version_handlers.get(version)
            if schema_action is None:
                # This action is not supported by this API version
                continue
            actions.append(self._get_action_from_schema(name, schema_action))

        for action_name, override_data in list(overridden_apis.items()):
            if action_name not in schema:
                # We ignore overridden APIs that aren't in the schema because
                # tests override the schema without necessarily providing all
                # the APIs that we override by default.
                continue
            overridden_schema = copy.deepcopy(schema[action_name][version])
            for parameter in overridden_schema["parameters"]:
                if parameter["name"] in override_data["replace_args"]:
                    replacement = override_data["replace_args"][parameter["name"]]
                    parameter.clear()
                    parameter.update(replacement)
            overridden_doc = override_data.get("doc")
            if overridden_doc:
                overridden_schema["doc"] = overridden_doc

            actions.append(
                self._get_action_from_schema(
                    action_name,
                    overridden_schema,
                    overridden_method_name=override_data["method"],
                )
            )

        actions.extend(API.extra_actions)

        return sorted(actions)

    def _get_action_from_schema(self, name, schema_action, overridden_method_name=None):
        """
        Get an L{_Action} instance representing the API action from the schema.
        """

        method_name = _lowercase_api_name(name)
        cli_name = schema_action.get("cli_name")
        cmdline_name = method_name.replace("_", "-") if cli_name is None else cli_name
        action_doc = schema_action["doc"]
        req_args = [
            parameter
            for parameter in schema_action["parameters"]
            if not parameter.get("optional")
        ]
        opt_args = [
            parameter
            for parameter in schema_action["parameters"]
            if parameter.get("optional")
        ]
        if overridden_method_name:
            method_name = overridden_method_name
        return _Action(cmdline_name, method_name, action_doc, req_args, opt_args)


def main(argv, stdout, stderr, exit, environ, schema=_schema):
    return CommandLine(stdout, stderr, exit, environ).main(argv, schema)


if __name__ == "__main__":
    main(sys.argv[1:], sys.stdout, sys.stderr, sys.exit, os.environ)
