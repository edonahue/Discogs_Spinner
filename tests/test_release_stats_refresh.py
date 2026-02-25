"""Tests for release_stats_refresh use case."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from discogs_player.use_cases.release_stats_refresh import run_refresh_release_stats


def test_refresh_release_stats_no_token():
    """Test that missing token returns error."""
    with patch("discogs_player.use_cases.release_stats_refresh.get_discogs_token", return_value=None):
        result = run_refresh_release_stats()
        assert result == {"error": "Discogs token missing"}


def test_refresh_release_stats_no_candidates():
    """Test when no candidates are found."""
    with patch("discogs_player.use_cases.release_stats_refresh.get_discogs_token", return_value="test_token"):
        with patch("discogs_player.use_cases.release_stats_refresh.get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.execute.return_value = mock_cursor
            mock_conn.return_value.close = MagicMock()
            
            result = run_refresh_release_stats()
            
            assert result["status"] == "No candidates found"
            assert result["processed"] == 0


def test_refresh_release_stats_success():
    """Test successful refresh of release stats."""
    with patch("discogs_player.use_cases.release_stats_refresh.get_discogs_token", return_value="test_token"):
        with patch("discogs_player.use_cases.release_stats_refresh.DiscogsClient") as mock_client:
            with patch("discogs_player.use_cases.release_stats_refresh.get_connection") as mock_conn:
                # Setup mock data
                mock_cursor = MagicMock()
                mock_cursor.fetchall.return_value = [(123,), (456,)]
                mock_cursor.execute = MagicMock()
                
                mock_db = MagicMock()
                mock_db.execute.return_value = mock_cursor
                mock_db.close = MagicMock()
                mock_conn.return_value = mock_db
                
                # Setup mock client
                mock_client_instance = MagicMock()
                mock_client_instance.fetch_release_stats.return_value = {
                    "num_for_sale": 10,
                    "lowest_price": 5.0,
                    "community_have": 100,
                    "community_want": 50,
                    "rating_count": 20,
                    "rating_average": 4.5,
                }
                mock_client.return_value = mock_client_instance
                
                result = run_refresh_release_stats(limit=2)
                
                assert result["status"] == "completed"
                assert result["processed"] == 2
                assert result["success"] == 2
                assert result["errors"] == 0
                assert result["is_wantlist"] is False
                
                # Verify client was called for each release
                assert mock_client_instance.fetch_release_stats.call_count == 2


def test_refresh_wantlist_stats_success():
    """Test successful refresh of wantlist stats."""
    with patch("discogs_player.use_cases.release_stats_refresh.get_discogs_token", return_value="test_token"):
        with patch("discogs_player.use_cases.release_stats_refresh.DiscogsClient") as mock_client:
            with patch("discogs_player.use_cases.release_stats_refresh.get_connection") as mock_conn:
                # Setup mock data
                mock_cursor = MagicMock()
                mock_cursor.fetchall.return_value = [(789,)]
                mock_cursor.execute = MagicMock()
                
                mock_db = MagicMock()
                mock_db.execute.return_value = mock_cursor
                mock_db.close = MagicMock()
                mock_conn.return_value = mock_db
                
                # Setup mock client
                mock_client_instance = MagicMock()
                mock_client_instance.fetch_release_stats.return_value = {
                    "num_for_sale": 5,
                    "lowest_price": 10.0,
                    "community_have": 200,
                    "community_want": 150,
                    "rating_count": 30,
                    "rating_average": 4.8,
                }
                mock_client.return_value = mock_client_instance
                
                result = run_refresh_release_stats(limit=1, is_wantlist=True)
                
                assert result["status"] == "completed"
                assert result["processed"] == 1
                assert result["success"] == 1
                assert result["errors"] == 0
                assert result["is_wantlist"] is True


def test_refresh_release_stats_with_errors():
    """Test refresh when some releases fail."""
    with patch("discogs_player.use_cases.release_stats_refresh.get_discogs_token", return_value="test_token"):
        with patch("discogs_player.use_cases.release_stats_refresh.DiscogsClient") as mock_client:
            with patch("discogs_player.use_cases.release_stats_refresh.get_connection") as mock_conn:
                # Setup mock data
                mock_cursor = MagicMock()
                mock_cursor.fetchall.return_value = [(111,), (222,)]
                mock_cursor.execute = MagicMock()
                
                mock_db = MagicMock()
                mock_db.execute.return_value = mock_cursor
                mock_db.close = MagicMock()
                mock_conn.return_value = mock_db
                
                # Setup mock client to fail on second call
                mock_client_instance = MagicMock()
                mock_client_instance.fetch_release_stats.side_effect = [
                    {
                        "num_for_sale": 10,
                        "lowest_price": 5.0,
                        "community_have": 100,
                        "community_want": 50,
                        "rating_count": 20,
                        "rating_average": 4.5,
                    },
                    Exception("API Error"),
                ]
                mock_client.return_value = mock_client_instance
                
                result = run_refresh_release_stats(limit=2)
                
                assert result["status"] == "completed"
                assert result["processed"] == 2
                assert result["success"] == 1
                assert result["errors"] == 1


def test_refresh_release_stats_force_refresh():
    """Test force refresh flag."""
    with patch("discogs_player.use_cases.release_stats_refresh.get_discogs_token", return_value="test_token"):
        with patch("discogs_player.use_cases.release_stats_refresh.DiscogsClient") as mock_client:
            with patch("discogs_player.use_cases.release_stats_refresh.get_connection") as mock_conn:
                # Setup mock data
                mock_cursor = MagicMock()
                mock_cursor.fetchall.return_value = [(333,)]
                mock_cursor.execute = MagicMock()
                
                mock_db = MagicMock()
                mock_db.execute.return_value = mock_cursor
                mock_db.close = MagicMock()
                mock_conn.return_value = mock_db
                
                # Setup mock client
                mock_client_instance = MagicMock()
                mock_client_instance.fetch_release_stats.return_value = {
                    "num_for_sale": 8,
                    "lowest_price": 7.0,
                    "community_have": 150,
                    "community_want": 75,
                    "rating_count": 25,
                    "rating_average": 4.2,
                }
                mock_client.return_value = mock_client_instance
                
                result = run_refresh_release_stats(limit=1, force_refresh=True)
                
                assert result["status"] == "completed"
                assert result["processed"] == 1
                
                # Verify the query was called with force_refresh=True
                call_args = mock_db.execute.call_args_list[0]
                assert call_args[0][1][0] is True  # force_refresh parameter
