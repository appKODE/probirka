# Changelog

## [Unreleased]

### Added
- Ready-made probes, importable from `probirka`: `TcpProbe` (no dependencies), `PostgresAsyncpgProbe`, `RedisProbe`, `HttpHttpxProbe`, `HttpHttpx2Probe`, `HttpAiohttpProbe`, `KafkaAiokafkaProbe`, `RabbitmqAiopikaProbe`, `MongoPymongoProbe`, `MongoMotorProbe`. Each accepts an existing client (or a zero-argument function returning one) or a connection string
- `MissingDependencyError` (an `ImportError`) raised on access to a probe or adapter whose client library is not installed; a library that is installed but too old keeps its original error
- `ProbeFailure` — exception for "the service answered, but not in a healthy way"; its message goes to `ProbeResult.error`
- `CallableProbe` is exported from the `probirka` package; names that need a third-party package (probes, `make_*` adapters) are resolved lazily and listed in `__all__` only when their package is installed, so `from probirka import *` brings what you can use and works with a bare install

### Changed
- Minimum supported Python is 3.11; the test matrix covers 3.11 through 3.15
- `started_at` in `ProbeResult` and `ProbirkaResult` is timezone-aware in the local zone of the host, so `to_dict()` and every HTTP integration now emit an ISO 8601 timestamp with a UTC offset
- `elapsed` and the TTL cache are measured with `time.monotonic()` instead of the wall clock, so clock adjustments no longer distort durations or cache expiry
- `CallableProbe` falls back to the class name for callables without `__name__` (`functools.partial`, objects with `__call__`) instead of raising `AttributeError`
- `groups` and `with_groups` accept any `Sequence[str]`, not just `list`
- Type checking moved from mypy to ty; annotations use PEP 585/604 syntax throughout
- Framework adapter modules are private now (`probirka._ext.*`); `make_fastapi_endpoint`, `make_aiohttp_endpoint` and `make_django_view` are imported from `probirka` as before, resolved lazily; when the framework is missing they raise an `ImportError` naming the package instead of an `AttributeError`
- `probirka` stays dependency-free; client libraries and frameworks are installed separately (no extras)

### Fixed
- `ProbeResult.elapsed` no longer includes the time spent looking up the TTL cache

## [0.6.1] - 2026-09-11

### Fixed
- `CallableProbe` awaits awaitables returned by plain callables (e.g. objects with `async def __call__`), which previously were reported as passed without running
- Replaced deprecated `asyncio.iscoroutinefunction` with `inspect.iscoroutinefunction` (removal scheduled for Python 3.16)
- Per-probe `success_ttl=0` / `failed_ttl=0` now disables caching instead of falling back to the global TTL

## [0.6.0] - 2026-09-11

### Added
- `make_django_view` — Django (>= 4.2) async view integration
- `ProbeResult.to_dict()` and `ProbirkaResult.to_dict()` — JSON-compatible representation shared by all integrations

### Changed
- All integrations return the same JSON format: `started_at` as ISO 8601, `elapsed` in seconds (float)

## [0.5.0] - 2026-09-11

### Added
- `ProbirkaResult.error` with the reason when the overall timeout is hit
- `Probe.name` property
- Python 3.14 support
- `py.typed` marker

### Fixed
- `Probirka.run()` no longer raises `TimeoutError` on the overall timeout: unfinished probes are reported as failed, finished ones keep their results, and the response gets `ok=False`
- Probe errors include the exception type; timeouts are reported explicitly instead of an empty string
- Synchronous probes run in the default executor, so they do not block the event loop and respect `timeout`
- `ProbeBase` is abstract: a subclass without `_check` fails at instantiation instead of silently reporting a failed check
- `ProbeResult.ok` is always a `bool`
- Unknown groups passed to `run()` are ignored instead of being registered as empty groups

## [0.4.1] - 2024-04-02

### Fixed
- Fix incorrect cache status reporting
- Fix empty info dict initialization
- Fix cache expiration behavior
- Rename HealthCheckResult to ProbirkaResult for consistency

## [0.4.0] - 2024-03-21

### Added
- Cache support for probe results with configurable TTL
- Info field support for storing probe metadata
- Comprehensive integration tests for FastAPI and aiohttp

## [0.3.2] - 2024-03-XX

### Added
- Extended health check functionality
- Improved documentation and examples
- Enhanced test coverage

## [0.3.1] - 2024-03-XX

### Added
- Documentation improvements
- Additional usage examples
- Minor bug fixes

## [0.3.0] - 2024-03-XX

### Added
- Initial release
- Basic health check functionality
- Support for async/sync probes
- Group-based probe execution
- FastAPI and aiohttp integration
- Basic documentation 
