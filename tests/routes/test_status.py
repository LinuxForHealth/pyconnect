"""
test_status.py
Tests the /status API endpoints
"""
import pytest
from asynctest import CoroutineMock
from pyconnect.routes import status


@pytest.mark.asyncio
async def test_status_get(async_test_client):
    """
    Tests /status [GET]
    :param async_test_client: Fast API async test client
    :param settings: Settings test fixture
    :param monkeypatch: MonkeyPatch instance used to mock test cases
    """

    status.is_service_available = CoroutineMock(return_value='AVAILABLE')
    async with async_test_client as ac:
        actual_response = await ac.get('/status')

        assert actual_response.status_code == 200

        actual_json = actual_response.json()
        assert 'application_version' in actual_json
        assert 'elapsed_time' in actual_json
        assert actual_json['elapsed_time'] > 0.0

        expected = {
            'application': 'pyconnect.main:app',
            'application_version': actual_json['application_version'],
            'is_reload_enabled': False,
            'nats_status': 'AVAILABLE',
            'kafka_broker_status': 'AVAILABLE',
            'elapsed_time': actual_json['elapsed_time']
        }
        assert actual_json == expected
