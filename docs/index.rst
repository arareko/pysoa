PySOA - Fast Python (micro)Services
===================================

Release: |version|

.. image:: https://pepy.tech/badge/pysoa
    :target: https://pepy.tech/project/pysoa

.. image:: https://img.shields.io/pypi/l/pysoa.svg
    :target: https://pypi.python.org/pypi/pysoa

.. image:: https://api.travis-ci.org/eventbrite/pysoa.svg
    :target: https://travis-ci.org/eventbrite/pysoa

.. image:: https://img.shields.io/pypi/v/pysoa.svg
    :target: https://pypi.python.org/pypi/pysoa

.. image:: https://img.shields.io/pypi/wheel/pysoa.svg
    :target: https://pypi.python.org/pypi/pysoa

.. image:: https://img.shields.io/pypi/pyversions/pysoa.svg
    :target: https://pypi.python.org/pypi/pysoa

**PySOA** is a general-purpose library for writing fast Python (micro)services and their clients, based on an RPC
(remote procedure call) calling style. It provides both a client and a server, which can be used directly by themselves
or, as we do, extended with extra functionality (our authentication, database routing, and other code is written as
private middleware and runs on top of this library).

PySOA uses the concept of pluggable "transports" to define a layer for sending requests and responses (messages)
between clients and servers. The default, production-ready included transport is a `Redis <https://redis.io/>`_ pub-sub
layer, which we use in combination with Redis Sentinel in clusters. A single Redis cluster is capable of handling tens
of thousands of PySOA messages per second with extremely efficient and desirable load-balancing properties. There is
also a local transport implementation primarily used for testing and demonstration but capable of being used in
production where appropriate.

The following sections summarize the details you will find in the rest of this documentation.


Basic Tenets
------------

- Services and actions both have simple names, and are called from the client by name. You can call actions
  individually, or bundle multiple action calls into a "job" to be run serially (either aborting or continuing on
  error).

- Requests and responses are simply Python dictionaries, and PySOA uses our open source validation framework
  `Conformity <https://github.com/eventbrite/conformity>`_ in order to verify their schema on the way in and out.

- Message bodies are encoded using `MessagePack <http://msgpack.org/>`_ by default (however, you can define your own
  serializer), with a few non-standard types encoded using MessagePack extensions, such as dates, times, date-times,
  and amounts of currency (using our open source `currint <https://github.com/eventbrite/currint>`_ library).

- Requests have a ``context``, which is sourced from the original client context (web request, API request, etc.) and
  automatically chained down into subsequent client calls made inside the service. This is used for contextual request
  information like correlation IDs, authentication tokens, locales, etc.

- We include "SOA Switches" as a first-party implementation of feature flags/toggles. Part of the context, they are
  bundled along with every request and automatically chained, and are packed as integers to ensure they have minimal
  overhead.


Servers
-------

SOA servers run as standalone processes and connect out to their transport to service requests and send responses, with
no listening ports. This means they can easily be scaled by simply launching or killing instances with whatever
orchestration software you want to use.

You can run all of the servers under a single channel layer (Redis instance/Sentinel cluster), have a separate layer
per service, or have separate layers for different quality of service levels for your site based on the access point
and type of accessing user.

Servers declare one or more Actions, which are registered on the class. Actions are callable objects of some type (such
as a function or method, or a class with a ``__call__`` method that will get instantiated before being called) that get
called with a request and return a response. We provide a base ``Action`` class that extends this contract to also
implement validation on requests and responses, but there is no requirement to use this if your needs are more complex.
Actions that are classes will be passed a reference to the server's settings object when instantiated.

.. code-block:: python

    from pysoa import server

    from example_service.actions.call_service import CallServiceAction
    from example_service.actions.square import SquareAction
    from example_service.actions.status import StatusAction


    class Server(server.BaseServer):

        service_name = 'example'

        action_class_map = {
            'call_service': CallServiceAction,
            'square': SquareAction,
            'status': StatusAction,
        }


A fully-functional `Example Service <https://github.com/eventbrite/example_service>`_ is available for your analysis
and experimentation. We encourage you to browse its source code, and even start it up, to see how it works and get a
better idea how to build services using PySOA.


Clients
-------

Clients are instantiated with a dictionary of service names and the transports by which they can be reached. There are
several approaches for calling service actions with a ``Client`` object:

- Calling a single action and getting the action response back directly using ``call_action``:

  .. code-block:: python

      action_response = client.call_action('example', 'square', {'number': 42})

- Creating a single job of multiple action requests, and sending it off to all be processed by the same server
  instance, serially:

  .. code-block:: python

      job_response = client.call_actions('example', [
          {'action': 'square', 'body': {'number': 42}},
          {'action': 'status', 'body': {'verbose': True}},
      ])

- Creating multiple jobs, one for each action belonging to the same service, and send them off to be processed by
  multiple server instances in parallel:

  .. code-block:: python

      action_responses = client.call_actions_parallel('example', [
          {'action': 'square', 'body': {'number': 1035}},
          {'action': 'status', 'body': {'verbose': True}},
      ])

- Creating multiple jobs, each with its own service name and one or more actions, and send them off to be processed by
  multiple server instances in parallel:

  .. code-block:: python

      job_responses = client.call_jobs_parallel([
          {'service_name': 'example', 'actions': [
              {'action': 'square', 'body': {'number': 4}},
              {'action': 'square', 'body': {'number': 8}},
              {'action': 'square', 'body': {'number': 17}},
          ]},
          {'service_name': 'example', 'actions': [{'action': 'status', 'body': {'verbose': True}}]},
          {'service_name': 'flight_booking', 'actions': [
              {'action': 'get_available_flights', 'body': {
                  'departure_airport': 'BNA',
                  'arrival_airport': 'SFO',
                  'departure_date': '2018-07-15',
                  'return_date': '2018-07-20',
              }},
          ]},
      ])


Middleware
----------

Both clients and servers can be extended using middleware, which, in the Django style, is code that wraps around a
request-response call, either on the client or server side, to add or mutate things in the request or response.

For example, some of our internal server middleware:

- Reads authentication tokens from the request and validates them to make sure the request is valid and not too old
- Logs metrics at the start and end of an action being processed so we can track how long our code is taking to run
- Catches errors in server code and logs it into Sentry so we can track and fix problems in production


Settings
--------

Both client and server use a dict-based settings system, with a
`Conformity <https://github.com/eventbrite/conformity>`_-defined schema to ensure that whatever settings are provided
are valid (this schema is extensible by service implementations if they have special settings they need set).

The server also has an integration mode with Django where it will read its settings from
``django.conf.settings.SOA_SERVER_SETTINGS`` for both running and for tests, which allows easy integration of Django
models and application logic into services (we make heavy use of the Django ORM in our services).


Testing
-------

Services can be tested using standard unit tests either by calling the actions directly (after all, they are just
callable objects), or, if a run through the server machinery is desired, using the
:class:`pysoa.test.server.PyTestServerTestCase` or :class:`pysoa.test.server.UnitTestServerTestCase` base classes, which
take care of setting up local transports for you.

For entire-system functional tests, you will need to spin up a copy of each desired service individually and point
them at an functional-test-specific channel layer to ensure isolation from the rest of the system.

There is also a ``StubClient`` available for testing code that calls services, but where you do not actually want to
have the service code in place, and a ``stub_action`` decorator / context manager that makes easy work of using it. This
is a must-have in unit and integration tests, where you do not want to call external dependencies.

For more information about using these test utilities in your services or service-calling applications, see the
`testing documentation <testing.html>`_.

For testing this PySOA library directly on your system, see the `contribution guide <contributing.html>`_.


Table of Contents
-----------------

.. toctree::
   :maxdepth: 2

   api
   testing
   protocol
   reference
   contributing
   roadmap
   history


Indices, Tables, and Searching
------------------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
