import json
import re
from unittest.mock import patch

import pytest
from flask.app import Flask
from spiffworkflow_backend.services.process_instance_processor import ProcessInstanceProcessor
from spiffworkflow_backend.services.secret_service import SecretService
from spiffworkflow_backend.services.service_task_service import ServiceTaskDelegate
from spiffworkflow_backend.services.service_task_service import UncaughtServiceTaskError
from spiffworkflow_connector_command.command_interface import CommandResponseDict
from spiffworkflow_connector_command.command_interface import ConnectorProxyResponseDict

from tests.spiffworkflow_backend.helpers.base_test import BaseTest
from tests.spiffworkflow_backend.helpers.test_data import load_test_spec


class TestServiceTaskDelegate(BaseTest):
    def test_check_prefixes_without_secret(self, app: Flask, with_db_and_bpmn_file_cleanup: None) -> None:
        result = ServiceTaskDelegate.value_with_secrets_replaced("hey")
        assert result == "hey"

    def test_check_prefixes_with_int(self, app: Flask, with_db_and_bpmn_file_cleanup: None) -> None:
        result = ServiceTaskDelegate.value_with_secrets_replaced(1)
        assert result == 1

    def test_check_prefixes_with_secret(self, app: Flask, with_db_and_bpmn_file_cleanup: None) -> None:
        user = self.find_or_create_user("test_user")
        SecretService().add_secret("hot_secret", "my_secret_value", user.id)
        result = ServiceTaskDelegate.value_with_secrets_replaced("secret:hot_secret")
        assert result == "my_secret_value"

    def test_check_prefixes_with_spiff_secret(self, app: Flask, with_db_and_bpmn_file_cleanup: None) -> None:
        user = self.find_or_create_user("test_user")
        SecretService().add_secret("hot_secret", "my_secret_value", user.id)
        result = ServiceTaskDelegate.value_with_secrets_replaced("TOKEN SPIFF_SECRET:hot_secret-haha")
        assert result == "TOKEN my_secret_value-haha"

    def test_check_prefixes_with_spiff_secret_in_dict(self, app: Flask, with_db_and_bpmn_file_cleanup: None) -> None:
        user = self.find_or_create_user("test_user")
        SecretService().add_secret("hot_secret", "my_secret_value", user.id)
        result = ServiceTaskDelegate.value_with_secrets_replaced({"Authorization": "TOKEN SPIFF_SECRET:hot_secret-haha"})
        assert result == {"Authorization": "TOKEN my_secret_value-haha"}

    def test_invalid_call_returns_good_error_message(self, app: Flask, with_db_and_bpmn_file_cleanup: None) -> None:
        process_model = load_test_spec(
            process_model_id="test_group/model_with_lanes",
            bpmn_file_name="lanes.bpmn",
            process_model_source_directory="model_with_lanes",
        )
        process_instance = self.create_process_instance_from_process_model(process_model=process_model)
        processor = ProcessInstanceProcessor(process_instance)
        processor.do_engine_steps(save=True)
        spiff_task = processor.next_task()

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 404
            mock_post.return_value.ok = True
            mock_post.return_value.text = '{"error_stuff": "WE ERRORED"}'
            with pytest.raises(UncaughtServiceTaskError) as connector_proxy_error:
                ServiceTaskDelegate.call_connector("my_invalid_operation", {}, spiff_task)
            message_regex = (
                r"The service did not find the requested resource\..*A critical component \(The connector proxy\) is"
                r" not responding correctly"
            )
            self._assert_error_with_code(
                str(connector_proxy_error.value), "ServiceTaskOperatorReturnedBadStatusError", message_regex, 404
            )

    def test_call_connector_on_request_post_exception(self, app: Flask, with_db_and_bpmn_file_cleanup: None) -> None:
        process_model = load_test_spec(
            process_model_id="test_group/model_with_lanes",
            bpmn_file_name="lanes.bpmn",
            process_model_source_directory="model_with_lanes",
        )
        process_instance = self.create_process_instance_from_process_model(process_model=process_model)
        processor = ProcessInstanceProcessor(process_instance)
        processor.do_engine_steps(save=True)
        spiff_task = processor.next_task()

        with patch("requests.post", side_effect=Exception("mocked error")):
            with pytest.raises(UncaughtServiceTaskError) as connector_proxy_error:
                ServiceTaskDelegate.call_connector("my_operation", {}, spiff_task)
            self._assert_error_with_code(str(connector_proxy_error.value), "Exception", "mocked error", 500)

    def test_call_connector_on_json_loads_exception(self, app: Flask, with_db_and_bpmn_file_cleanup: None) -> None:
        process_model = load_test_spec(
            process_model_id="test_group/model_with_lanes",
            bpmn_file_name="lanes.bpmn",
            process_model_source_directory="model_with_lanes",
        )
        process_instance = self.create_process_instance_from_process_model(process_model=process_model)
        processor = ProcessInstanceProcessor(process_instance)
        processor.do_engine_steps(save=True)
        spiff_task = processor.next_task()
        return_text = "NOT JSON"

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.ok = True
            mock_post.return_value.text = return_text
            with pytest.raises(UncaughtServiceTaskError) as connector_proxy_error:
                ServiceTaskDelegate.call_connector("my_operation", {}, spiff_task)
            self._assert_error_with_code(
                str(connector_proxy_error.value), "ServiceTaskOperatorReturnedInvalidJsonError", return_text, 200
            )

    def test_call_connector_on_error_response(self, app: Flask, with_db_and_bpmn_file_cleanup: None) -> None:
        process_model = load_test_spec(
            process_model_id="test_group/model_with_lanes",
            bpmn_file_name="lanes.bpmn",
            process_model_source_directory="model_with_lanes",
        )
        process_instance = self.create_process_instance_from_process_model(process_model=process_model)
        processor = ProcessInstanceProcessor(process_instance)
        processor.do_engine_steps(save=True)
        spiff_task = processor.next_task()

        command_response: CommandResponseDict = {
            "body": "{}",
            "mimetype": "application/json",
        }
        connector_response: ConnectorProxyResponseDict = {
            "command_response": command_response,
            "error": {
                "error_code": "OurTestError",
                "message": "We errored",
            },
            "command_response_version": 2,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 500
            mock_post.return_value.ok = False
            mock_post.return_value.text = json.dumps(connector_response)
            with pytest.raises(UncaughtServiceTaskError) as connector_proxy_error:
                ServiceTaskDelegate.call_connector("my_operation", {}, spiff_task)
            self._assert_error_with_code(str(connector_proxy_error.value), "OurTestError", "We errored", 500)

    def test_call_connector_can_succeed(self, app: Flask, with_db_and_bpmn_file_cleanup: None) -> None:
        process_model = load_test_spec(
            process_model_id="test_group/model_with_lanes",
            bpmn_file_name="lanes.bpmn",
            process_model_source_directory="model_with_lanes",
        )
        process_instance = self.create_process_instance_from_process_model(process_model=process_model)
        processor = ProcessInstanceProcessor(process_instance)
        processor.do_engine_steps(save=True)
        spiff_task = processor.next_task()

        command_response: CommandResponseDict = {
            "body": json.dumps({"we_did_it": True}),
            "mimetype": "application/json",
        }
        connector_response: ConnectorProxyResponseDict = {
            "command_response": command_response,
            "error": None,
            "command_response_version": 2,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.ok = True
            mock_post.return_value.text = json.dumps(connector_response)
            result = ServiceTaskDelegate.call_connector("my_operation", {}, spiff_task)
            assert result is not None
            assert json.loads(result) == {
                **connector_response["command_response"],
                **{"operator_identifier": "my_operation"},
            }

    def _assert_error_with_code(self, response_text: str, error_code: str, contains_message: str, status_code: int) -> None:
        assert f"'{error_code}'" in response_text
        assert bool(
            re.search(rf"\b{contains_message}\b", response_text)
        ), f"Expected to find '{contains_message}' in: {response_text}"
        assert bool(re.search(rf"\b{status_code}\b", response_text)), f"Expected to find '{status_code}' in: {response_text}"
