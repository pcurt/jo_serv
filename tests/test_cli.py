from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from jo_serv.cli import main


class TestCLI:
    def test_call_without_args_works(self) -> None:
        # Given
        runner = CliRunner()

        # When
        with patch("jo_serv.cli.ExampleClass", autospec=True) as mock_module:
            result = runner.invoke(main, args=None)

        # Then
        mock_module.assert_called_once()
        assert 0 == result.exit_code

    def test_call_with_args_works(self, tmp_path: str) -> None:
        # Given
        runner = CliRunner()
        log_cfg_path = str(Path(__file__).parent / "data_dir/log.cfg")

        # When
        with patch("jo_serv.cli.ExampleClass", autospec=True) as mock_module:
            result = runner.invoke(
                main, args=["--iterations", "10", "--log-config", log_cfg_path]
            )

        # Then
        assert result.exception is None
        assert 0 == result.exit_code
        mock_module.assert_called_once()
