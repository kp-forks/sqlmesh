from __future__ import annotations

import typing as t

from sqlmesh.core import constants as c
from sqlmesh.core.config.base import BaseConfig
from sqlmesh.core.config.model import ModelDefaultsConfig
from sqlmesh.core.config.common import variables_validator
from sqlmesh.core.config.connection import (
    SerializableConnectionConfig,
    connection_config_validator,
)
from sqlmesh.core.config.scheduler import SchedulerConfig, scheduler_config_validator


class GatewayConfig(BaseConfig):
    """Gateway configuration defines how SQLMesh should connect to the data warehouse,
    the state backend and the scheduler.

    Args:
        connection: Connection configuration for the data warehouse.
        state_connection: Connection configuration for the state backend. If not provided,
            the same connection as the data warehouse will be used.
        test_connection: Connection configuration for running unit tests.
        scheduler: The scheduler configuration.
        state_schema: Schema name to use for the state tables. If None or empty string are provided
            then no schema name is used and therefore the default schema defined for the connection will be used
        variables: A dictionary of gateway-specific variables that can be used in models / macros. This overrides
            root-level variables by key.
    """

    connection: t.Optional[SerializableConnectionConfig] = None
    state_connection: t.Optional[SerializableConnectionConfig] = None
    test_connection: t.Optional[SerializableConnectionConfig] = None
    scheduler: t.Optional[SchedulerConfig] = None
    state_schema: t.Optional[str] = c.SQLMESH
    variables: t.Dict[str, t.Any] = {}
    model_defaults: t.Optional[ModelDefaultsConfig] = None

    _connection_config_validator = connection_config_validator
    _scheduler_config_validator = scheduler_config_validator
    _variables_validator = variables_validator
