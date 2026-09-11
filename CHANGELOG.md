# Changelog

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
