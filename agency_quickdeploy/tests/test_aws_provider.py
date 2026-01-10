"""Tests for AWS provider."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from agency_quickdeploy.providers.base import ProviderType, DeploymentResult
from agency_quickdeploy.config import QuickDeployConfig
from agency_quickdeploy.auth import AuthType


class TestAWSProviderImport:
    """Test AWS provider can be imported."""

    def test_aws_provider_type_exists(self):
        """Test that AWS is in ProviderType enum."""
        assert ProviderType.AWS.value == "aws"

    def test_import_aws_provider(self):
        """Test AWSProvider can be imported."""
        from agency_quickdeploy.providers.aws import AWSProvider
        assert AWSProvider is not None


class TestAWSProviderConfig:
    """Test AWS provider configuration."""

    def test_default_aws_config(self):
        """Test default AWS configuration values."""
        config = QuickDeployConfig(
            provider=ProviderType.AWS,
            auth_type=AuthType.API_KEY,
        )
        assert config.aws_region == "us-east-1"
        assert config.aws_instance_type == "t3.medium"
        assert config.aws_bucket is None

    def test_custom_aws_config(self):
        """Test custom AWS configuration."""
        config = QuickDeployConfig(
            provider=ProviderType.AWS,
            auth_type=AuthType.API_KEY,
            aws_region="eu-west-1",
            aws_bucket="my-bucket",
            aws_instance_type="t3.large",
        )
        assert config.aws_region == "eu-west-1"
        assert config.aws_bucket == "my-bucket"
        assert config.aws_instance_type == "t3.large"


class TestAWSProviderError:
    """Test AWS error classes."""

    def test_aws_error_not_installed(self):
        """Test not installed error message."""
        from agency_quickdeploy.providers.aws import AWSError

        error = AWSError.not_installed()
        assert "not installed" in error.message.lower()
        assert "pip install boto3" in error.message

    def test_aws_error_no_credentials(self):
        """Test no credentials error message."""
        from agency_quickdeploy.providers.aws import AWSError

        error = AWSError.no_credentials()
        assert "credentials" in error.message.lower()
        assert "aws configure" in error.message.lower()

    def test_aws_error_region_not_supported(self):
        """Test region not supported error message."""
        from agency_quickdeploy.providers.aws import AWSError

        error = AWSError.region_not_supported("invalid-region")
        assert "invalid-region" in error.message
        assert "not have" in error.message.lower()

    def test_aws_error_instance_not_found(self):
        """Test instance not found error message."""
        from agency_quickdeploy.providers.aws import AWSError

        error = AWSError.instance_not_found("test-agent")
        assert "test-agent" in error.message
        assert "not found" in error.message.lower()


class TestAWSProviderAMIs:
    """Test AWS AMI configuration."""

    def test_ubuntu_amis_exist(self):
        """Test that Ubuntu AMIs are defined."""
        from agency_quickdeploy.providers.aws import UBUNTU_AMIS

        assert len(UBUNTU_AMIS) > 0
        assert "us-east-1" in UBUNTU_AMIS
        assert "us-west-2" in UBUNTU_AMIS

    def test_ubuntu_ami_format(self):
        """Test that Ubuntu AMIs have correct format."""
        from agency_quickdeploy.providers.aws import UBUNTU_AMIS

        for region, ami_id in UBUNTU_AMIS.items():
            assert ami_id.startswith("ami-"), f"AMI {ami_id} should start with 'ami-'"


class TestAWSProviderInit:
    """Test AWS provider initialization."""

    @patch('agency_quickdeploy.providers.aws.BOTO3_AVAILABLE', True)
    def test_init_with_default_config(self):
        """Test initialization with default config."""
        from agency_quickdeploy.providers.aws import AWSProvider

        config = QuickDeployConfig(
            provider=ProviderType.AWS,
            auth_type=AuthType.API_KEY,
        )

        with patch.object(AWSProvider, '__init__', return_value=None):
            provider = AWSProvider.__new__(AWSProvider)
            provider.config = config
            provider.region = config.aws_region
            provider.bucket = config.aws_bucket
            provider.instance_type = config.aws_instance_type
            provider._ec2 = None
            provider._s3 = None

            assert provider.region == "us-east-1"
            assert provider.instance_type == "t3.medium"


class TestAWSProviderLaunch:
    """Test AWS provider launch functionality."""

    @patch('agency_quickdeploy.providers.aws.BOTO3_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.aws.boto3')
    def test_launch_creates_instance(self, mock_boto3):
        """Test that launch creates an EC2 instance."""
        from agency_quickdeploy.providers.aws import AWSProvider

        # Setup mocks
        mock_ec2 = MagicMock()
        mock_s3 = MagicMock()
        mock_sts = MagicMock()

        mock_boto3.resource.return_value = mock_ec2
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': mock_s3,
            'sts': mock_sts,
        }.get(service)

        mock_sts.get_caller_identity.return_value = {'Account': '123456789'}
        mock_s3.head_bucket.return_value = {}

        mock_instance = Mock()
        mock_instance.id = "i-12345678"
        mock_ec2.create_instances.return_value = [mock_instance]

        # Bypass credentials check
        mock_ec2.instances.limit.return_value = iter([])

        config = QuickDeployConfig(
            provider=ProviderType.AWS,
            auth_type=AuthType.API_KEY,
        )

        provider = AWSProvider(config)
        provider._ec2 = mock_ec2
        provider._s3 = mock_s3
        provider.bucket = "test-bucket"

        result = provider.launch(
            agent_id="test-agent",
            prompt="Build a todo app",
            credentials=None,
        )

        assert result.agent_id == "test-agent"
        assert result.provider == "aws"
        assert result.status == "launching"

    @patch('agency_quickdeploy.providers.aws.BOTO3_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.aws.boto3')
    def test_launch_with_spot_instance(self, mock_boto3):
        """Test that launch can create spot instances."""
        from agency_quickdeploy.providers.aws import AWSProvider

        mock_ec2 = MagicMock()
        mock_s3 = MagicMock()
        mock_sts = MagicMock()

        mock_boto3.resource.return_value = mock_ec2
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': mock_s3,
            'sts': mock_sts,
        }.get(service)

        mock_sts.get_caller_identity.return_value = {'Account': '123456789'}
        mock_s3.head_bucket.return_value = {}

        mock_instance = Mock()
        mock_ec2.create_instances.return_value = [mock_instance]
        mock_ec2.instances.limit.return_value = iter([])

        config = QuickDeployConfig(
            provider=ProviderType.AWS,
            auth_type=AuthType.API_KEY,
        )

        provider = AWSProvider(config)
        provider._ec2 = mock_ec2
        provider._s3 = mock_s3
        provider.bucket = "test-bucket"

        result = provider.launch(
            agent_id="test-agent",
            prompt="Build an app",
            credentials=None,
            spot=True,
        )

        # Verify spot was requested
        call_kwargs = mock_ec2.create_instances.call_args.kwargs
        assert 'InstanceMarketOptions' in call_kwargs


class TestAWSProviderStatus:
    """Test AWS provider status functionality."""

    @patch('agency_quickdeploy.providers.aws.BOTO3_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.aws.boto3')
    def test_status_running_instance(self, mock_boto3):
        """Test status returns info for running instance."""
        from agency_quickdeploy.providers.aws import AWSProvider

        mock_ec2 = MagicMock()
        mock_s3 = MagicMock()

        mock_boto3.resource.return_value = mock_ec2
        mock_boto3.client.return_value = mock_s3

        mock_instance = Mock()
        mock_instance.id = "i-12345678"
        mock_instance.state = {'Name': 'running'}
        mock_instance.public_ip_address = "1.2.3.4"
        mock_instance.tags = [{'Key': 'agent-id', 'Value': 'test-agent'}]

        mock_ec2.instances.filter.return_value = [mock_instance]
        mock_ec2.instances.limit.return_value = iter([])

        # S3 status check
        mock_s3.get_object.side_effect = Exception("No status file")

        config = QuickDeployConfig(
            provider=ProviderType.AWS,
            auth_type=AuthType.API_KEY,
        )

        provider = AWSProvider(config)
        provider._ec2 = mock_ec2
        provider._s3 = mock_s3
        provider.bucket = "test-bucket"

        status = provider.status("test-agent")

        assert status["agent_id"] == "test-agent"
        assert status["status"] == "running"
        assert status["instance_id"] == "i-12345678"
        assert status["external_ip"] == "1.2.3.4"

    @patch('agency_quickdeploy.providers.aws.BOTO3_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.aws.boto3')
    def test_status_not_found(self, mock_boto3):
        """Test status returns not_found for missing instance."""
        from agency_quickdeploy.providers.aws import AWSProvider

        mock_ec2 = MagicMock()
        mock_s3 = MagicMock()

        mock_boto3.resource.return_value = mock_ec2
        mock_boto3.client.return_value = mock_s3

        mock_ec2.instances.filter.return_value = []
        mock_ec2.instances.limit.return_value = iter([])

        config = QuickDeployConfig(
            provider=ProviderType.AWS,
            auth_type=AuthType.API_KEY,
        )

        provider = AWSProvider(config)
        provider._ec2 = mock_ec2
        provider._s3 = mock_s3
        provider.bucket = "test-bucket"

        status = provider.status("missing-agent")

        assert status["agent_id"] == "missing-agent"
        assert status["status"] == "not_found"


class TestAWSProviderStop:
    """Test AWS provider stop functionality."""

    @patch('agency_quickdeploy.providers.aws.BOTO3_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.aws.boto3')
    def test_stop_terminates_instance(self, mock_boto3):
        """Test stop terminates the EC2 instance."""
        from agency_quickdeploy.providers.aws import AWSProvider

        mock_ec2 = MagicMock()

        mock_boto3.resource.return_value = mock_ec2

        mock_instance = Mock()
        mock_ec2.instances.filter.return_value = [mock_instance]
        mock_ec2.instances.limit.return_value = iter([])

        config = QuickDeployConfig(
            provider=ProviderType.AWS,
            auth_type=AuthType.API_KEY,
        )

        provider = AWSProvider(config)
        provider._ec2 = mock_ec2

        result = provider.stop("test-agent")

        assert result is True
        mock_instance.terminate.assert_called_once()

    @patch('agency_quickdeploy.providers.aws.BOTO3_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.aws.boto3')
    def test_stop_returns_false_if_not_found(self, mock_boto3):
        """Test stop returns False if instance not found."""
        from agency_quickdeploy.providers.aws import AWSProvider

        mock_ec2 = MagicMock()

        mock_boto3.resource.return_value = mock_ec2

        mock_ec2.instances.filter.return_value = []
        mock_ec2.instances.limit.return_value = iter([])

        config = QuickDeployConfig(
            provider=ProviderType.AWS,
            auth_type=AuthType.API_KEY,
        )

        provider = AWSProvider(config)
        provider._ec2 = mock_ec2

        result = provider.stop("missing-agent")

        assert result is False


class TestAWSProviderList:
    """Test AWS provider list functionality."""

    @patch('agency_quickdeploy.providers.aws.BOTO3_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.aws.boto3')
    def test_list_agents_returns_instances(self, mock_boto3):
        """Test list_agents returns EC2 instances with agency tags."""
        from agency_quickdeploy.providers.aws import AWSProvider

        mock_ec2 = MagicMock()

        mock_boto3.resource.return_value = mock_ec2

        mock_instance1 = Mock()
        mock_instance1.id = "i-11111111"
        mock_instance1.state = {'Name': 'running'}
        mock_instance1.public_ip_address = "1.2.3.4"
        mock_instance1.tags = [
            {'Key': 'Name', 'Value': 'agent-1'},
            {'Key': 'agent-id', 'Value': 'agent-1'},
        ]

        mock_instance2 = Mock()
        mock_instance2.id = "i-22222222"
        mock_instance2.state = {'Name': 'stopped'}
        mock_instance2.public_ip_address = None
        mock_instance2.tags = [
            {'Key': 'Name', 'Value': 'agent-2'},
            {'Key': 'agent-id', 'Value': 'agent-2'},
        ]

        mock_ec2.instances.filter.return_value = [mock_instance1, mock_instance2]
        mock_ec2.instances.limit.return_value = iter([])

        config = QuickDeployConfig(
            provider=ProviderType.AWS,
            auth_type=AuthType.API_KEY,
        )

        provider = AWSProvider(config)
        provider._ec2 = mock_ec2

        agents = provider.list_agents()

        assert len(agents) == 2
        assert agents[0]["name"] == "agent-1"
        assert agents[0]["status"] == "running"
        assert agents[0]["external_ip"] == "1.2.3.4"
        assert agents[1]["name"] == "agent-2"
        assert agents[1]["status"] == "stopped"


class TestAWSStartupScript:
    """Test AWS startup script generation."""

    @patch('agency_quickdeploy.providers.aws.BOTO3_AVAILABLE', True)
    @patch('agency_quickdeploy.providers.aws.boto3')
    def test_startup_script_contains_required_components(self, mock_boto3):
        """Test startup script contains all required components."""
        from agency_quickdeploy.providers.aws import AWSProvider

        mock_ec2 = MagicMock()
        mock_boto3.resource.return_value = mock_ec2
        mock_ec2.instances.limit.return_value = iter([])

        config = QuickDeployConfig(
            provider=ProviderType.AWS,
            auth_type=AuthType.API_KEY,
        )

        provider = AWSProvider(config)
        provider._ec2 = mock_ec2
        provider.bucket = "test-bucket"

        script = provider._generate_startup_script(
            agent_id="test-agent",
            prompt="Build a todo app",
            credentials=None,
            max_iterations=10,
            no_shutdown=True,
        )

        # Check script contains required components
        assert "AGENT_ID" in script
        assert "test-agent" in script
        assert "BUCKET" in script
        assert "test-bucket" in script
        assert "MAX_ITERATIONS" in script
        assert "NO_SHUTDOWN" in script
        assert "aws s3 cp" in script
        assert "npm install -g @anthropic-ai/claude-code" in script
