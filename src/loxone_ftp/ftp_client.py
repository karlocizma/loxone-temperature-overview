import ftplib
import os
import logging
from pathlib import Path
from typing import List, Optional
from time import sleep

logger = logging.getLogger(__name__)


class FTPConnectionError(Exception):
    """Raised when FTP connection fails"""
    pass


class LoxoneFTPClient:
    """FTP client for connecting to Loxone MiniServer and retrieving logs"""

    DEFAULT_PORT = 21
    DEFAULT_TIMEOUT = 30
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 2
    LOG_DIRECTORY = "/logs"
    TEMP_LOG_PATTERNS = ["Temp", "Temperature", "temp"]

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = DEFAULT_PORT,
        timeout: int = DEFAULT_TIMEOUT,
        local_storage_path: str = "./data/logs",
        retry_attempts: int = RETRY_ATTEMPTS,
        retry_delay: int = RETRY_DELAY,
    ):
        """
        Initialize Loxone FTP client.

        Args:
            host: Loxone server IP address or hostname
            username: FTP username
            password: FTP password
            port: FTP port (default: 21)
            timeout: Connection timeout in seconds (default: 30)
            local_storage_path: Local directory for storing downloaded logs
            retry_attempts: Number of retry attempts on connection failure
            retry_delay: Delay in seconds between retries
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.local_storage_path = Path(local_storage_path)
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.ftp_connection = None
        self._ensure_local_storage()

    def _ensure_local_storage(self) -> None:
        """Create local storage directory if it doesn't exist"""
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage path: {self.local_storage_path}")

    def connect(self) -> bool:
        """
        Establish FTP connection with retry logic.

        Returns:
            bool: True if connection successful, False otherwise

        Raises:
            FTPConnectionError: If all retry attempts fail
        """
        for attempt in range(1, self.retry_attempts + 1):
            try:
                logger.info(f"Attempting FTP connection to {self.host}:{self.port} (attempt {attempt}/{self.retry_attempts})")
                self.ftp_connection = ftplib.FTP()
                self.ftp_connection.connect(
                    self.host,
                    self.port,
                    timeout=self.timeout
                )
                self.ftp_connection.login(self.username, self.password)
                logger.info(f"Successfully connected to {self.host}")
                return True
            except (ftplib.Error, OSError) as e:
                logger.warning(f"Connection attempt {attempt} failed: {e}")
                if attempt < self.retry_attempts:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    sleep(self.retry_delay)
                else:
                    raise FTPConnectionError(
                        f"Failed to connect to {self.host}:{self.port} after {self.retry_attempts} attempts: {e}"
                    )

    def disconnect(self) -> None:
        """Safely disconnect from FTP server"""
        if self.ftp_connection:
            try:
                self.ftp_connection.quit()
                logger.info("Disconnected from FTP server")
            except ftplib.Error as e:
                logger.warning(f"Error during disconnect: {e}")
                try:
                    self.ftp_connection.close()
                except Exception:
                    pass
            finally:
                self.ftp_connection = None

    def list_files(self, directory: str = None) -> List[str]:
        """
        List files in FTP directory.

        Args:
            directory: Remote directory path (default: LOG_DIRECTORY)

        Returns:
            List of filenames in the directory
        """
        if not self.ftp_connection:
            raise FTPConnectionError("Not connected to FTP server")

        directory = directory or self.LOG_DIRECTORY
        try:
            logger.info(f"Listing files in {directory}")
            files = self.ftp_connection.nlst(directory)
            logger.info(f"Found {len(files)} files")
            return files
        except ftplib.Error as e:
            logger.error(f"Error listing files: {e}")
            return []

    def _is_temperature_log(self, filename: str) -> bool:
        """
        Check if file appears to be a temperature log file.

        Args:
            filename: Name of the file to check

        Returns:
            bool: True if file matches temperature log patterns
        """
        filename_lower = filename.lower()
        return any(pattern.lower() in filename_lower for pattern in self.TEMP_LOG_PATTERNS)

    def get_temperature_logs(self, remote_directory: str = None) -> List[str]:
        """
        Get list of temperature log files from remote server.

        Args:
            remote_directory: Remote directory to search (default: LOG_DIRECTORY)

        Returns:
            List of temperature log filenames
        """
        all_files = self.list_files(remote_directory)
        temp_logs = [f for f in all_files if self._is_temperature_log(f)]
        logger.info(f"Found {len(temp_logs)} temperature log files")
        return temp_logs

    def download_file(self, remote_path: str, local_path: str = None) -> str:
        """
        Download single file from FTP server.

        Args:
            remote_path: Remote file path
            local_path: Local file path (default: uses filename in storage directory)

        Returns:
            Path to downloaded file

        Raises:
            FTPConnectionError: If not connected to FTP server
        """
        if not self.ftp_connection:
            raise FTPConnectionError("Not connected to FTP server")

        filename = os.path.basename(remote_path)
        if not local_path:
            local_path = self.local_storage_path / filename

        try:
            logger.info(f"Downloading {remote_path} to {local_path}")
            with open(local_path, 'wb') as f:
                self.ftp_connection.retrbinary(f'RETR {remote_path}', f.write)
            logger.info(f"Successfully downloaded {filename}")
            return str(local_path)
        except ftplib.Error as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            if local_path.exists():
                local_path.unlink()
            raise

    def download_temperature_logs(self, remote_directory: str = None) -> List[str]:
        """
        Download all temperature log files from remote server.

        Args:
            remote_directory: Remote directory (default: LOG_DIRECTORY)

        Returns:
            List of paths to downloaded files
        """
        if not self.ftp_connection:
            raise FTPConnectionError("Not connected to FTP server")

        temp_logs = self.get_temperature_logs(remote_directory)
        remote_directory = remote_directory or self.LOG_DIRECTORY

        downloaded_files = []
        for log_file in temp_logs:
            try:
                remote_path = f"{remote_directory}/{log_file}" if not remote_directory.endswith('/') else f"{remote_directory}{log_file}"
                local_file = self.download_file(remote_path)
                downloaded_files.append(local_file)
            except Exception as e:
                logger.error(f"Failed to download {log_file}: {e}")
                continue

        logger.info(f"Downloaded {len(downloaded_files)}/{len(temp_logs)} temperature logs")
        return downloaded_files

    def get_new_logs_only(self) -> List[str]:
        """
        Get only new/updated temperature log files.

        This method checks local storage to determine which files have already
        been processed and downloads only new or updated files.

        Returns:
            List of paths to new/updated log files
        """
        if not self.ftp_connection:
            raise FTPConnectionError("Not connected to FTP server")

        try:
            remote_files = self.get_temperature_logs()
            local_files = {f.name for f in self.local_storage_path.glob('*') if f.is_file()}

            new_files = []
            for remote_file in remote_files:
                if remote_file not in local_files:
                    new_files.append(remote_file)

            logger.info(f"Found {len(new_files)} new temperature logs")

            downloaded = []
            remote_directory = self.LOG_DIRECTORY
            for new_file in new_files:
                try:
                    remote_path = f"{remote_directory}/{new_file}" if not remote_directory.endswith('/') else f"{remote_directory}{new_file}"
                    local_file = self.download_file(remote_path)
                    downloaded.append(local_file)
                except Exception as e:
                    logger.error(f"Failed to download new log {new_file}: {e}")
                    continue

            return downloaded
        except Exception as e:
            logger.error(f"Error retrieving new logs: {e}")
            return []

    def retrieve_logs(self, only_new: bool = True) -> List[str]:
        """
        Main method to retrieve temperature logs from Loxone server.

        Args:
            only_new: If True, retrieve only new logs; if False, retrieve all (default: True)

        Returns:
            List of paths to retrieved log files
        """
        try:
            self.connect()
            if only_new:
                files = self.get_new_logs_only()
            else:
                files = self.download_temperature_logs()
            return files
        except FTPConnectionError as e:
            logger.error(f"FTP connection error: {e}")
            return []
        finally:
            self.disconnect()

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
        return False
