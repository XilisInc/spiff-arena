import json
import os
import tempfile
from collections.abc import Generator

import pytest
from flask.app import Flask
from spiffworkflow_backend.models.db import db
from spiffworkflow_backend.models.feature_flag import FeatureFlagModel
from spiffworkflow_backend.services.element_units_service import BpmnSpecDict
from spiffworkflow_backend.services.element_units_service import ElementUnitsService
from spiffworkflow_backend.services.feature_flag_service import FeatureFlagService

from tests.spiffworkflow_backend.helpers.base_test import BaseTest

#
# we don't want to fully flex every aspect of the spiff-element-units
# library here, mainly just checking that our interaction with it is
# as expected.
#


@pytest.fixture()
def feature_enabled(app: Flask, with_db_and_bpmn_file_cleanup: None) -> Generator[None, None, None]:
    db.session.query(FeatureFlagModel).delete()
    db.session.commit()
    FeatureFlagService.set_feature_flags({"element_units": True}, {})
    yield


@pytest.fixture()
def feature_disabled(app: Flask, with_db_and_bpmn_file_cleanup: None) -> Generator[None, None, None]:
    db.session.query(FeatureFlagModel).delete()
    db.session.commit()
    FeatureFlagService.set_feature_flags({"element_units": False}, {})
    yield


@pytest.fixture()
def app_no_cache_dir(app: Flask) -> Generator[Flask, None, None]:
    with BaseTest().app_config_mock(app, "SPIFFWORKFLOW_BACKEND_ELEMENT_UNITS_CACHE_DIR", None):
        yield app


@pytest.fixture()
def app_some_cache_dir(app: Flask) -> Generator[Flask, None, None]:
    with BaseTest().app_config_mock(app, "SPIFFWORKFLOW_BACKEND_ELEMENT_UNITS_CACHE_DIR", "some_cache_dir"):
        yield app


@pytest.fixture()
def app_tmp_cache_dir(app: Flask) -> Generator[Flask, None, None]:
    with tempfile.TemporaryDirectory() as tmpdirname:
        with BaseTest().app_config_mock(app, "SPIFFWORKFLOW_BACKEND_ELEMENT_UNITS_CACHE_DIR", tmpdirname):
            yield app


@pytest.fixture()
def example_specs_dict(app: Flask) -> Generator[BpmnSpecDict, None, None]:
    path = os.path.join(app.instance_path, "..", "..", "tests", "data", "specs-json", "no-tasks.json")
    with open(path) as f:
        yield json.loads(f.read())


class TestElementUnitsService(BaseTest):
    """Tests the ElementUnitsService."""

    def test_cache_dir_env_is_respected(
        self,
        app_some_cache_dir: Flask,
    ) -> None:
        assert ElementUnitsService._cache_dir() == "some_cache_dir"

    def test_feature_disabled_if_feature_flag_is_false(
        self,
        feature_disabled: None,
    ) -> None:
        assert not ElementUnitsService._enabled()

    def test_feature_enabled_if_env_is_true(
        self,
        feature_enabled: None,
    ) -> None:
        assert ElementUnitsService._enabled()

    def test_is_disabled_when_no_cache_dir(
        self,
        app_no_cache_dir: Flask,
    ) -> None:
        assert not ElementUnitsService._enabled()

    def test_ok_to_cache_when_disabled(
        self,
        feature_disabled: None,
    ) -> None:
        result = ElementUnitsService.cache_element_units_for_workflow("", {})
        assert result is None

    def test_ok_to_read_workflow_from_cached_element_unit_when_disabled(
        self,
        feature_disabled: None,
    ) -> None:
        result = ElementUnitsService.workflow_from_cached_element_unit("", "", "")
        assert result is None

    def test_can_write_to_cache(
        self,
        app_tmp_cache_dir: Flask,
        feature_enabled: None,
        example_specs_dict: BpmnSpecDict,
    ) -> None:
        result = ElementUnitsService.cache_element_units_for_workflow("testing", example_specs_dict)
        assert result is None

    def test_can_write_to_cache_multiple_times(
        self,
        app_tmp_cache_dir: Flask,
        feature_enabled: None,
        example_specs_dict: BpmnSpecDict,
    ) -> None:
        result = ElementUnitsService.cache_element_units_for_workflow("testing", example_specs_dict)
        assert result is None
        result = ElementUnitsService.cache_element_units_for_workflow("testing", example_specs_dict)
        assert result is None
        result = ElementUnitsService.cache_element_units_for_workflow("testing", example_specs_dict)
        assert result is None

    def test_can_read_element_unit_for_process_from_cache(
        self,
        app_tmp_cache_dir: Flask,
        feature_enabled: None,
        example_specs_dict: BpmnSpecDict,
    ) -> None:
        ElementUnitsService.cache_element_units_for_workflow("testing", example_specs_dict)
        cached_specs_dict = ElementUnitsService.workflow_from_cached_element_unit("testing", "no_tasks", "no_tasks")
        assert cached_specs_dict["spec"]["name"] == example_specs_dict["spec"]["name"]  # type: ignore

    def test_reading_element_unit_for_uncached_process_returns_none(
        self,
        app_tmp_cache_dir: Flask,
        feature_enabled: None,
    ) -> None:
        cached_specs_dict = ElementUnitsService.workflow_from_cached_element_unit("testing", "no_tasks", "")
        assert cached_specs_dict is None
