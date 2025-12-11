"""
Example usage of the Loxone FTP client for retrieving and processing temperature logs.
"""

import logging
from src.loxone_ftp import LoxoneFTPClient, DataHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Example main function"""

    # FTP connection parameters
    ftp_config = {
        'host': '192.168.1.100',  # Loxone MiniServer IP
        'username': 'admin',
        'password': 'password',
        'port': 21,
    }

    # Create FTP client
    ftp_client = LoxoneFTPClient(
        **ftp_config,
        local_storage_path='./data/logs',
        retry_attempts=3,
        retry_delay=2,
    )

    # Create data handler for processing
    data_handler = DataHandler(
        storage_path='./data/logs',
        processed_path='./data/processed',
    )

    try:
        # Retrieve only new logs
        print("Retrieving temperature logs...")
        log_files = ftp_client.retrieve_logs(only_new=True)

        if log_files:
            print(f"Downloaded {len(log_files)} log files:")
            for log_file in log_files:
                print(f"  - {log_file}")

            # Process the downloaded logs
            print("\nProcessing temperature data...")
            combined_data = data_handler.get_combined_temperature_data(log_files)

            # Save processed data
            output_file = data_handler.save_processed_data(combined_data)
            print(f"\nProcessed data saved to: {output_file}")

            # Display statistics
            if combined_data['all_readings']:
                temp_values = [r['temperature'] for r in combined_data['all_readings']]
                print(f"\nTemperature Statistics:")
                print(f"  Total readings: {len(temp_values)}")
                print(f"  Min: {min(temp_values):.2f}°C")
                print(f"  Max: {max(temp_values):.2f}°C")
                print(f"  Average: {sum(temp_values)/len(temp_values):.2f}°C")
        else:
            print("No new log files found.")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


def example_with_context_manager():
    """Example using context manager"""

    ftp_config = {
        'host': '192.168.1.100',
        'username': 'admin',
        'password': 'password',
    }

    # Using context manager ensures proper connection cleanup
    with LoxoneFTPClient(**ftp_config) as client:
        logs = client.get_temperature_logs()
        print(f"Found {len(logs)} temperature log files")
        # Connection is automatically closed here


def example_manual_connection():
    """Example with manual connection management"""

    client = LoxoneFTPClient(
        host='192.168.1.100',
        username='admin',
        password='password',
    )

    try:
        # Manually connect
        client.connect()

        # List files in specific directory
        files = client.list_files('/logs')
        print(f"Files in /logs: {files}")

        # Download specific file
        local_path = client.download_file('/logs/temperature_01.txt')
        print(f"Downloaded to: {local_path}")

    finally:
        # Always disconnect
        client.disconnect()


if __name__ == '__main__':
    main()
