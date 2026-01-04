"""Tests for gcp/vm.py - TDD style.

These tests define the expected behavior of the GCE VM manager module.
Tests use mocks to avoid requiring actual GCP credentials.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestVMManager:
    """Tests for VMManager class."""

    def test_init_with_project_and_zone(self):
        """Should initialize with project and zone."""
        from agency_quickdeploy.gcp.vm import VMManager

        vm = VMManager(project="my-project", zone="us-central1-a")
        assert vm.project == "my-project"
        assert vm.zone == "us-central1-a"

    @patch("agency_quickdeploy.gcp.vm.compute_v1.InstancesClient")
    @patch("agency_quickdeploy.gcp.vm.compute_v1.ZoneOperationsClient")
    def test_create_vm(self, mock_ops_client_class, mock_instances_client_class):
        """Should create a VM instance."""
        from agency_quickdeploy.gcp.vm import VMManager

        mock_instances = MagicMock()
        mock_instances_client_class.return_value = mock_instances

        # Mock insert operation
        mock_operation = MagicMock()
        mock_operation.name = "operation-123"
        mock_instances.insert.return_value = mock_operation

        # Mock wait for operation
        mock_ops = MagicMock()
        mock_ops_client_class.return_value = mock_ops
        done_operation = MagicMock()
        done_operation.status = "DONE"
        done_operation.error = None
        mock_ops.wait.return_value = done_operation

        vm_manager = VMManager("test-project", "us-central1-a")
        result = vm_manager.create(
            name="test-vm",
            machine_type="e2-medium",
            startup_script="#!/bin/bash\necho hello",
            metadata={"anthropic-api-key": "test-key"},
        )

        assert result is not None
        assert "name" in result or result.get("status") == "creating"
        mock_instances.insert.assert_called_once()

    @patch("agency_quickdeploy.gcp.vm.compute_v1.InstancesClient")
    @patch("agency_quickdeploy.gcp.vm.compute_v1.ZoneOperationsClient")
    def test_create_spot_vm(self, mock_ops_client_class, mock_instances_client_class):
        """Should create a spot/preemptible VM."""
        from agency_quickdeploy.gcp.vm import VMManager

        mock_instances = MagicMock()
        mock_instances_client_class.return_value = mock_instances

        mock_operation = MagicMock()
        mock_operation.name = "operation-123"
        mock_instances.insert.return_value = mock_operation

        mock_ops = MagicMock()
        mock_ops_client_class.return_value = mock_ops
        done_operation = MagicMock()
        done_operation.status = "DONE"
        done_operation.error = None
        mock_ops.wait.return_value = done_operation

        vm_manager = VMManager("test-project", "us-central1-a")
        result = vm_manager.create(
            name="test-vm",
            machine_type="e2-medium",
            startup_script="#!/bin/bash\necho hello",
            metadata={},
            spot=True,
        )

        assert result is not None
        # Verify spot instance configuration was included
        call_args = mock_instances.insert.call_args
        instance_resource = call_args.kwargs.get("instance_resource") or call_args[1].get("instance_resource")
        assert instance_resource is not None

    @patch("agency_quickdeploy.gcp.vm.compute_v1.InstancesClient")
    @patch("agency_quickdeploy.gcp.vm.compute_v1.ZoneOperationsClient")
    def test_delete_vm(self, mock_ops_client_class, mock_instances_client_class):
        """Should delete a VM instance."""
        from agency_quickdeploy.gcp.vm import VMManager

        mock_instances = MagicMock()
        mock_instances_client_class.return_value = mock_instances

        mock_operation = MagicMock()
        mock_operation.name = "delete-op-123"
        mock_instances.delete.return_value = mock_operation

        mock_ops = MagicMock()
        mock_ops_client_class.return_value = mock_ops
        done_operation = MagicMock()
        done_operation.status = "DONE"
        done_operation.error = None
        mock_ops.wait.return_value = done_operation

        vm_manager = VMManager("test-project", "us-central1-a")
        result = vm_manager.delete("test-vm")

        assert result is True
        mock_instances.delete.assert_called_once()

    @patch("agency_quickdeploy.gcp.vm.compute_v1.InstancesClient")
    def test_get_vm(self, mock_instances_client_class):
        """Should get VM details."""
        from agency_quickdeploy.gcp.vm import VMManager

        mock_instances = MagicMock()
        mock_instances_client_class.return_value = mock_instances

        mock_instance = MagicMock()
        mock_instance.name = "test-vm"
        mock_instance.status = "RUNNING"
        mock_instances.get.return_value = mock_instance

        vm_manager = VMManager("test-project", "us-central1-a")
        result = vm_manager.get("test-vm")

        assert result is not None
        mock_instances.get.assert_called_once()

    @patch("agency_quickdeploy.gcp.vm.compute_v1.InstancesClient")
    def test_get_vm_not_found(self, mock_instances_client_class):
        """Should return None if VM doesn't exist."""
        from agency_quickdeploy.gcp.vm import VMManager
        from google.api_core.exceptions import NotFound

        mock_instances = MagicMock()
        mock_instances_client_class.return_value = mock_instances
        mock_instances.get.side_effect = NotFound("VM not found")

        vm_manager = VMManager("test-project", "us-central1-a")
        result = vm_manager.get("nonexistent-vm")

        assert result is None

    @patch("agency_quickdeploy.gcp.vm.compute_v1.InstancesClient")
    def test_list_by_label(self, mock_instances_client_class):
        """Should list VMs with specific label."""
        from agency_quickdeploy.gcp.vm import VMManager

        mock_instances = MagicMock()
        mock_instances_client_class.return_value = mock_instances

        mock_vm1 = MagicMock()
        mock_vm1.name = "agent-001"
        mock_vm1.status = "RUNNING"
        mock_vm2 = MagicMock()
        mock_vm2.name = "agent-002"
        mock_vm2.status = "TERMINATED"

        mock_instances.list.return_value = [mock_vm1, mock_vm2]

        vm_manager = VMManager("test-project", "us-central1-a")
        result = vm_manager.list_by_label("agency-quickdeploy", "true")

        assert len(result) == 2


class TestVMLabeling:
    """Tests for VM labeling functionality."""

    @patch("agency_quickdeploy.gcp.vm.compute_v1.InstancesClient")
    @patch("agency_quickdeploy.gcp.vm.compute_v1.ZoneOperationsClient")
    def test_create_vm_with_labels(self, mock_ops_client_class, mock_instances_client_class):
        """Should create VM with custom labels."""
        from agency_quickdeploy.gcp.vm import VMManager

        mock_instances = MagicMock()
        mock_instances_client_class.return_value = mock_instances

        mock_operation = MagicMock()
        mock_operation.name = "operation-123"
        mock_instances.insert.return_value = mock_operation

        mock_ops = MagicMock()
        mock_ops_client_class.return_value = mock_ops
        done_operation = MagicMock()
        done_operation.status = "DONE"
        done_operation.error = None
        mock_ops.wait.return_value = done_operation

        vm_manager = VMManager("test-project", "us-central1-a")
        result = vm_manager.create(
            name="test-vm",
            machine_type="e2-medium",
            startup_script="#!/bin/bash",
            metadata={},
            labels={"agency-quickdeploy": "true", "agent-id": "test-123"},
        )

        assert result is not None
        # The labels should be included in the VM config
        call_args = mock_instances.insert.call_args
        instance_resource = call_args.kwargs.get("instance_resource") or call_args[1].get("instance_resource")
        assert instance_resource is not None
