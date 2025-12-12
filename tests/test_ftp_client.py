import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import ftplib

from src.loxone_ftp.ftp_client import LoxoneFTPClient, FTPConnectionError


class TestLoxoneFTPClient:
    """Test cases for LoxoneFTPClient"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def client(self, temp_dir):
        """Create FTP client instance"""
        return LoxoneFTPClient(
            host='192.168.1.1',
            username='admin',
            password='password',
            local_storage_path=temp_dir,
            retry_attempts=1,
            retry_delay=0,
        )

    def test_initialization(self, client, temp_dir):
        """Test client initialization"""
        assert client.host == '192.168.1.1'
        assert client.username == 'admin'
        assert client.password == 'password'
        assert client.port == 21
        assert Path(temp_dir).exists()

    def test_local_storage_creation(self, temp_dir):
        """Test that local storage directory is created"""
        storage = Path(temp_dir) / 'new_storage'
        client = LoxoneFTPClient(
            host='192.168.1.1',
            username='admin',
            password='password',
            local_storage_path=str(storage),
            retry_attempts=1,
        )
        assert storage.exists()

    @patch('src.loxone_ftp.ftp_client.ftplib.FTP')
    def test_connect_success(self, mock_ftp_class, client):
        """Test successful FTP connection"""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp

        result = client.connect()

        assert result is True
        assert client.ftp_connection is not None
        mock_ftp.connect.assert_called_once_with('192.168.1.1', 21, timeout=30)
        mock_ftp.login.assert_called_once_with('admin', 'password')

    @patch('src.loxone_ftp.ftp_client.ftplib.FTP')
    def test_connect_failure_raises_exception(self, mock_ftp_class, client):
        """Test connection failure raises exception"""
        mock_ftp_class.side_effect = ftplib.Error("Connection refused")

        with pytest.raises(FTPConnectionError):
            client.connect()

    @patch('src.loxone_ftp.ftp_client.ftplib.FTP')
    def test_connect_with_retry(self, mock_ftp_class, client):
        """Test connection retry logic"""
        mock_ftp = MagicMock()
        # First two attempts fail, third succeeds
        mock_ftp_class.side_effect = [
            ftplib.Error("Connection refused"),
            ftplib.Error("Connection refused"),
            mock_ftp,
        ]

        client.retry_attempts = 3
        client.retry_delay = 0

        result = client.connect()

        assert result is True
        assert mock_ftp_class.call_count >= 3

    @patch('src.loxone_ftp.ftp_client.ftplib.FTP')
    def test_disconnect(self, mock_ftp_class, client):
        """Test FTP disconnection"""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp
        client.connect()

        client.disconnect()

        mock_ftp.quit.assert_called_once()
        assert client.ftp_connection is None

    @patch('src.loxone_ftp.ftp_client.ftplib.FTP')
    def test_disconnect_error_handling(self, mock_ftp_class, client):
        """Test disconnect handles errors gracefully"""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp
        mock_ftp.quit.side_effect = ftplib.Error("Error")
        mock_ftp.close.return_value = None

        client.connect()
        client.disconnect()

        mock_ftp.close.assert_called_once()
        assert client.ftp_connection is None

    @patch('src.loxone_ftp.ftp_client.ftplib.FTP')
    def test_list_files(self, mock_ftp_class, client):
        """Test listing files from FTP directory"""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp
        mock_ftp.nlst.return_value = ['temp_log_1.txt', 'temp_log_2.txt', 'other.txt']

        client.ftp_connection = mock_ftp
        files = client.list_files('/logs')

        assert len(files) == 3
        mock_ftp.nlst.assert_called_once_with('/logs')

    def test_list_files_not_connected(self, client):
        """Test list_files raises error when not connected"""
        with pytest.raises(FTPConnectionError):
            client.list_files()

    @patch('src.loxone_ftp.ftp_client.ftplib.FTP')
    def test_get_temperature_logs(self, mock_ftp_class, client):
        """Test retrieving temperature log files"""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp
        mock_ftp.nlst.return_value = [
            'Temperature_01.txt',
            'Temp_02.csv',
            'Humidity_01.txt',
            'temp_sensor_03.log',
        ]

        client.ftp_connection = mock_ftp
        temp_logs = client.get_temperature_logs()

        assert len(temp_logs) == 3
        assert 'Temperature_01.txt' in temp_logs
        assert 'Humidity_01.txt' not in temp_logs

    def test_is_temperature_log(self, client):
        """Test temperature log pattern matching"""
        assert client._is_temperature_log('Temperature_01.txt') is True
        assert client._is_temperature_log('Temp_02.csv') is True
        assert client._is_temperature_log('temp_sensor.log') is True
        assert client._is_temperature_log('Humidity_01.txt') is False
        assert client._is_temperature_log('Data.csv') is False

    @patch('src.loxone_ftp.ftp_client.ftplib.FTP')
    def test_download_file(self, mock_ftp_class, client, temp_dir):
        """Test downloading single file"""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp

        def write_test_data(cmd, callback):
            callback(b'test data')

        mock_ftp.retrbinary = write_test_data

        client.ftp_connection = mock_ftp
        local_path = client.download_file('/logs/temp_01.txt')

        assert local_path.endswith('temp_01.txt')
        assert Path(local_path).exists()

    def test_download_file_not_connected(self, client):
        """Test download_file raises error when not connected"""
        with pytest.raises(FTPConnectionError):
            client.download_file('/logs/temp_01.txt')

    @patch('src.loxone_ftp.ftp_client.ftplib.FTP')
    def test_context_manager(self, mock_ftp_class, client):
        """Test context manager functionality"""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp

        with client:
            assert client.ftp_connection is not None

        mock_ftp.quit.assert_called_once()
        assert client.ftp_connection is None

    def test_custom_port(self):
        """Test FTP client with custom port"""
        client = LoxoneFTPClient(
            host='192.168.1.1',
            username='admin',
            password='password',
            port=2121,
        )
        assert client.port == 2121

    def test_custom_timeout(self):
        """Test FTP client with custom timeout"""
        client = LoxoneFTPClient(
            host='192.168.1.1',
            username='admin',
            password='password',
            timeout=60,
        )
        assert client.timeout == 60
