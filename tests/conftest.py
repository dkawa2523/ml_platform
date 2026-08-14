"""Shared test profiles."""

from hypothesis import HealthCheck, settings

settings.register_profile("nightly", max_examples=500, suppress_health_check=(HealthCheck.too_slow,))
